import { useState } from 'react';
import {
  Box, Card, Typography, Grid, Chip, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableHead, TableRow, Alert, CircularProgress,
  LinearProgress,
} from '@mui/material';
import { Add, Warning, TrendingUp } from '@mui/icons-material';
import { useMines, useSafetyIncidents, useSafetyPatterns } from '../api/hooks';
import { api } from '../api/client';

const SEVERITY_COLORS: Record<string, 'default' | 'info' | 'warning' | 'error'> = {
  near_miss: 'default',
  minor: 'info',
  moderate: 'warning',
  serious: 'error',
  fatal: 'error',
};

const CATEGORIES = [
  'roof_fall', 'slope_failure', 'equipment', 'blasting', 'electrical',
  'transport', 'fire', 'gas', 'water_inrush', 'other',
];

export default function SafetyPatterns() {
  const { data: mines = [] } = useMines();
  const [mineFilter, setMineFilter] = useState('');
  const { data: incidents = [], isLoading: loadingIncidents, refetch: refetchIncidents } = useSafetyIncidents(mineFilter || undefined);
  const { data: patterns = [], refetch: refetchPatterns } = useSafetyPatterns();
  const [dialog, setDialog] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [form, setForm] = useState({
    mine_id: '', category: 'other', severity: 'minor', description: '',
    location_description: '', workers_involved: 0, injuries: 0,
    incident_date: new Date().toISOString().slice(0, 10),
  });

  const handleReport = async () => {
    if (!form.mine_id || !form.description) return;
    await api.post('/safety/incidents', {
      ...form,
      incident_date: new Date(form.incident_date).toISOString(),
    });
    setDialog(false);
    setForm({ mine_id: '', category: 'other', severity: 'minor', description: '', location_description: '', workers_involved: 0, injuries: 0, incident_date: new Date().toISOString().slice(0, 10) });
    refetchIncidents();
  };

  const handleDetectPatterns = async () => {
    setDetecting(true);
    try {
      await api.post('/safety/detect');
      refetchPatterns();
    } finally {
      setDetecting(false);
    }
  };

  const severityCounts = {
    near_miss: incidents.filter((i: any) => i.severity === 'near_miss').length,
    minor: incidents.filter((i: any) => i.severity === 'minor').length,
    moderate: incidents.filter((i: any) => i.severity === 'moderate').length,
    serious: incidents.filter((i: any) => i.severity === 'serious' || i.severity === 'fatal').length,
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Safety Incident Pattern Detector</Typography>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Mine</InputLabel>
            <Select value={mineFilter} label="Mine" onChange={(e) => setMineFilter(e.target.value)}>
              <MenuItem value="">All Mines</MenuItem>
              {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
            </Select>
          </FormControl>
          <Button variant="outlined" startIcon={<TrendingUp />} onClick={handleDetectPatterns} disabled={detecting}>
            {detecting ? 'Detecting...' : 'Detect Patterns'}
          </Button>
          <Button variant="contained" color="error" startIcon={<Add />} onClick={() => setDialog(true)}>
            Report Incident
          </Button>
        </Box>
      </Box>

      <Grid container spacing={2} mb={3}>
        {[
          { label: 'Near Miss', count: severityCounts.near_miss, color: 'text.secondary' },
          { label: 'Minor', count: severityCounts.minor, color: 'info.main' },
          { label: 'Moderate', count: severityCounts.moderate, color: 'warning.main' },
          { label: 'Serious/Fatal', count: severityCounts.serious, color: 'error.main' },
        ].map((s) => (
          <Grid size={{ xs: 6, md: 3 }} key={s.label}>
            <Card>
              <Box p={2} textAlign="center">
                <Typography variant="h3" fontWeight={700} color={s.color}>{s.count}</Typography>
                <Typography variant="body2" color="text.secondary">{s.label}</Typography>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {patterns.length > 0 && (
        <Box mb={3}>
          <Typography variant="h6" gutterBottom>
            <Warning sx={{ verticalAlign: 'middle', mr: 0.5, color: 'warning.main' }} />
            Detected Patterns
          </Typography>
          <Grid container spacing={2}>
            {patterns.map((p: any) => (
              <Grid size={{ xs: 12, md: 6 }} key={p.id}>
                <Alert severity="warning" sx={{ '& .MuiAlert-message': { width: '100%' } }}>
                  <Typography variant="subtitle2" fontWeight={600}>{p.pattern_name}</Typography>
                  <Typography variant="body2" sx={{ my: 1 }}>{p.description}</Typography>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Chip size="small" label={`${p.incident_count} incidents`} variant="outlined" />
                    <Box display="flex" alignItems="center" gap={1} sx={{ width: 120 }}>
                      <LinearProgress variant="determinate" value={parseFloat(p.confidence || 0) * 100} sx={{ flexGrow: 1 }} />
                      <Typography variant="caption">{(parseFloat(p.confidence || 0) * 100).toFixed(0)}%</Typography>
                    </Box>
                  </Box>
                  {p.recommendations?.length > 0 && (
                    <Box mt={1}>
                      {p.recommendations.map((r: string, i: number) => (
                        <Typography key={i} variant="caption" display="block" color="text.secondary">
                          {i + 1}. {r}
                        </Typography>
                      ))}
                    </Box>
                  )}
                </Alert>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      <Typography variant="h6" gutterBottom>Recent Incidents</Typography>
      {loadingIncidents ? (
        <Box textAlign="center" py={4}><CircularProgress /></Box>
      ) : (
        <Card>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Severity</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Location</TableCell>
                <TableCell align="right">Injuries</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {incidents.map((inc: any) => (
                <TableRow key={inc.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{new Date(inc.incident_date).toLocaleDateString()}</TableCell>
                  <TableCell><Chip size="small" label={inc.category?.replace(/_/g, ' ')} variant="outlined" /></TableCell>
                  <TableCell>
                    <Chip size="small" label={inc.severity?.replace(/_/g, ' ')} color={SEVERITY_COLORS[inc.severity] || 'default'} />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 300 }}>
                    <Typography variant="body2" noWrap>{inc.description}</Typography>
                  </TableCell>
                  <TableCell>{inc.location_description || '—'}</TableCell>
                  <TableCell align="right">{inc.injuries || 0}</TableCell>
                </TableRow>
              ))}
              {incidents.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary" py={4}>No incidents recorded</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}

      <Dialog open={dialog} onClose={() => setDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Report Safety Incident</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} mt={0.5}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Mine</InputLabel>
                <Select value={form.mine_id} label="Mine" onChange={(e) => setForm(f => ({ ...f, mine_id: e.target.value }))}>
                  {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField fullWidth type="date" label="Incident Date" value={form.incident_date}
                onChange={(e) => setForm(f => ({ ...f, incident_date: e.target.value }))}
                slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select value={form.category} label="Category" onChange={(e) => setForm(f => ({ ...f, category: e.target.value }))}>
                  {CATEGORIES.map(c => (
                    <MenuItem key={c} value={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Severity</InputLabel>
                <Select value={form.severity} label="Severity" onChange={(e) => setForm(f => ({ ...f, severity: e.target.value }))}>
                  {['near_miss', 'minor', 'moderate', 'serious', 'fatal'].map(s => (
                    <MenuItem key={s} value={s}>{s.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth multiline rows={3} label="Description" value={form.description}
                onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth label="Location Description" value={form.location_description}
                onChange={(e) => setForm(f => ({ ...f, location_description: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField fullWidth type="number" label="Workers Involved" value={form.workers_involved}
                onChange={(e) => setForm(f => ({ ...f, workers_involved: parseInt(e.target.value) || 0 }))} />
            </Grid>
            <Grid size={{ xs: 6 }}>
              <TextField fullWidth type="number" label="Injuries" value={form.injuries}
                onChange={(e) => setForm(f => ({ ...f, injuries: parseInt(e.target.value) || 0 }))} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleReport}
            disabled={!form.mine_id || !form.description}>Report</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
