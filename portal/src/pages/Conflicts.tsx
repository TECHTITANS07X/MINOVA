import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, Select, MenuItem, FormControl, InputLabel, Alert, Divider,
  Table, TableBody, TableCell, TableHead, TableRow, IconButton,
} from '@mui/material';
import { CompareArrows, CheckCircle } from '@mui/icons-material';
import { useConflicts, useResolveConflict } from '../api/hooks';
import type { ConflictFlag } from '../types';

export default function Conflicts() {
  const { data: conflicts = [] } = useConflicts();
  const resolveConflict = useResolveConflict();
  const [selected, setSelected] = useState<ConflictFlag | null>(null);
  const [resolution, setResolution] = useState('accept_primary');
  const [reason, setReason] = useState('');
  const [correctedValue, setCorrectedValue] = useState('');

  const handleResolve = () => {
    if (!selected || !reason.trim()) return;
    resolveConflict.mutate({
      conflictId: selected.id,
      resolution,
      reason,
      value: resolution === 'corrected' ? parseFloat(correctedValue) : undefined,
    }, { onSuccess: () => { setSelected(null); setReason(''); setCorrectedValue(''); } });
  };

  const unresolvedCount = conflicts.filter(c => c.resolution === 'unresolved').length;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5">Conflicts</Typography>
          <Typography variant="body2" color="text.secondary">
            {unresolvedCount} unresolved conflict{unresolvedCount !== 1 ? 's' : ''} requiring human verification
          </Typography>
        </Box>
      </Box>

      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Entity</TableCell>
              <TableCell>Metric</TableCell>
              <TableCell align="right">Value A</TableCell>
              <TableCell>Source A</TableCell>
              <TableCell align="right">Value B</TableCell>
              <TableCell>Source B</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {conflicts.map((c) => (
              <TableRow key={c.id} hover sx={{ bgcolor: c.resolution === 'unresolved' ? 'error.50' : undefined }}>
                <TableCell>{c.entity_type}</TableCell>
                <TableCell>{c.metric}</TableCell>
                <TableCell align="right"><Typography fontWeight={700}>{c.value_a.toLocaleString()}</Typography></TableCell>
                <TableCell><Chip size="small" label={c.source_a} /></TableCell>
                <TableCell align="right"><Typography fontWeight={700}>{c.value_b.toLocaleString()}</Typography></TableCell>
                <TableCell><Chip size="small" label={c.source_b} /></TableCell>
                <TableCell>
                  <Chip size="small" label={c.resolution}
                    color={c.resolution === 'unresolved' ? 'error' : 'success'} />
                </TableCell>
                <TableCell align="right">
                  {c.resolution === 'unresolved' && (
                    <Button size="small" variant="outlined" onClick={() => setSelected(c)}>Resolve</Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {conflicts.length === 0 && (
              <TableRow><TableCell colSpan={8} align="center">
                <Typography color="text.secondary" py={4}>No conflicts</Typography>
              </TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="md" fullWidth>
        <DialogTitle>Resolve Conflict</DialogTitle>
        <DialogContent>
          {selected && (
            <>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Two sources disagree on <strong>{selected.metric}</strong>. You must choose which value to accept or provide a corrected value with evidence.
              </Alert>
              <Grid container spacing={3} mb={3}>
                <Grid size={{ xs: 5 }}>
                  <Card variant="outlined" sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="caption" color="text.secondary">Source A: {selected.source_a}</Typography>
                    <Typography variant="h4" fontWeight={700} color="primary">{selected.value_a.toLocaleString()}</Typography>
                  </Card>
                </Grid>
                <Grid size={{ xs: 2 }} display="flex" alignItems="center" justifyContent="center">
                  <CompareArrows color="error" fontSize="large" />
                </Grid>
                <Grid size={{ xs: 5 }}>
                  <Card variant="outlined" sx={{ textAlign: 'center', p: 2 }}>
                    <Typography variant="caption" color="text.secondary">Source B: {selected.source_b}</Typography>
                    <Typography variant="h4" fontWeight={700} color="secondary">{selected.value_b.toLocaleString()}</Typography>
                  </Card>
                </Grid>
              </Grid>
              <Divider sx={{ mb: 2 }} />
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Resolution</InputLabel>
                <Select value={resolution} label="Resolution" onChange={(e) => setResolution(e.target.value)}>
                  <MenuItem value="accept_primary">Accept Value A ({selected.value_a})</MenuItem>
                  <MenuItem value="accept_secondary">Accept Value B ({selected.value_b})</MenuItem>
                  <MenuItem value="corrected">Provide Corrected Value</MenuItem>
                </Select>
              </FormControl>
              {resolution === 'corrected' && (
                <TextField label="Corrected Value" type="number" fullWidth sx={{ mb: 2 }}
                  value={correctedValue} onChange={(e) => setCorrectedValue(e.target.value)} />
              )}
              <TextField label="Reason (mandatory)" multiline rows={3} fullWidth required
                value={reason} onChange={(e) => setReason(e.target.value)}
                helperText="Explain why this resolution was chosen" />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleResolve} disabled={!reason.trim()}>
            <CheckCircle sx={{ mr: 0.5 }} /> Resolve
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
