import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, Button, Divider,
  Table, TableBody, TableCell, TableHead, TableRow, Alert,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
} from '@mui/material';
import { WaterDrop, Thermostat, Air, CheckCircle, Cancel } from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import type { RecoveryPlan } from '../types';

const FORECAST = [
  { day: 'Today', temp: 32, rain: 0, code: 'Clear' },
  { day: 'Tomorrow', temp: 30, rain: 5, code: 'Light rain' },
  { day: 'Wed', temp: 28, rain: 25, code: 'Moderate rain' },
  { day: 'Thu', temp: 27, rain: 40, code: 'Heavy rain' },
  { day: 'Fri', temp: 29, rain: 10, code: 'Light rain' },
  { day: 'Sat', temp: 31, rain: 2, code: 'Partly cloudy' },
  { day: 'Sun', temp: 33, rain: 0, code: 'Clear' },
];

const RAINFALL_CHART = FORECAST.map(f => ({ day: f.day, precipitation: f.rain }));

const MOCK_PLAN: RecoveryPlan = {
  id: 'plan-1', mine_id: 'mine1', gap_tonnes: 15000, status: 'proposed',
  proposed_daily_targets: { 'Oct 1': 9500, 'Oct 2': 9500, 'Oct 3': 8500, 'Oct 4': 9000, 'Oct 5': 9500 },
  rationale: 'Based on historical P95 output of 9,800t/day and forecasted clear weather for the next 5 days, redistributing the 15,000t shortfall across 5 working days is feasible. Historical evidence shows 3 similar recovery periods achieved targets within 5% margin.',
  created_at: new Date().toISOString(),
};

export default function Weather() {
  const [planDialog, setPlanDialog] = useState(false);
  const [decisionReason, setDecisionReason] = useState('');

  const handleDecision = async (action: 'accept' | 'reject') => {
    if (!decisionReason.trim()) return;
    try {
      await api.post(`/weather/recovery-plans/${MOCK_PLAN.id}/decide`, { action, reason: decisionReason });
      setPlanDialog(false);
      setDecisionReason('');
    } catch { /* handled */ }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Weather & Recovery Planning</Typography>

      <Grid container spacing={3} mb={3}>
        {[
          { icon: <Thermostat />, label: 'Temperature', value: '32°C', sub: 'Max today', color: '#E65100' },
          { icon: <WaterDrop />, label: 'Precipitation', value: '0 mm', sub: 'Today', color: '#0277BD' },
          { icon: <Air />, label: 'Wind Speed', value: '12 km/h', sub: 'Light breeze', color: '#558B2F' },
        ].map((card) => (
          <Grid size={{ xs: 12, sm: 4 }} key={card.label}>
            <Card>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: `${card.color}15`, color: card.color }}>
                  {card.icon}
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">{card.label}</Typography>
                  <Typography variant="h5" fontWeight={700}>{card.value}</Typography>
                  <Typography variant="caption" color="text.secondary">{card.sub}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>7-Day Forecast</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Day</TableCell>
                    <TableCell>Condition</TableCell>
                    <TableCell align="right">Temp (°C)</TableCell>
                    <TableCell align="right">Rain (mm)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {FORECAST.map((f) => (
                    <TableRow key={f.day}>
                      <TableCell>{f.day}</TableCell>
                      <TableCell><Chip size="small" label={f.code} variant="outlined" /></TableCell>
                      <TableCell align="right">{f.temp}</TableCell>
                      <TableCell align="right">
                        <Typography color={f.rain > 20 ? 'error' : f.rain > 0 ? 'warning.main' : 'text.primary'} fontWeight={f.rain > 20 ? 700 : 400}>
                          {f.rain}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Precipitation Forecast</Typography>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={RAINFALL_CHART}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="precipitation" fill="#0277BD" name="Rain (mm)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recovery Plan</Typography>
              <Chip label={MOCK_PLAN.status.toUpperCase()} color="warning" sx={{ mb: 2 }} />

              <Alert severity="info" sx={{ mb: 2 }}>
                Production gap of <strong>{MOCK_PLAN.gap_tonnes.toLocaleString()} tonnes</strong> detected.
              </Alert>

              <Typography variant="subtitle2" gutterBottom>Proposed Daily Targets</Typography>
              <Table size="small" sx={{ mb: 2 }}>
                <TableBody>
                  {Object.entries(MOCK_PLAN.proposed_daily_targets).map(([day, target]) => (
                    <TableRow key={day}>
                      <TableCell>{day}</TableCell>
                      <TableCell align="right"><strong>{target.toLocaleString()} t</strong></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <Typography variant="subtitle2" gutterBottom>Rationale</Typography>
              <Typography variant="body2" color="text.secondary" mb={2}>{MOCK_PLAN.rationale}</Typography>

              <Divider sx={{ my: 2 }} />
              <Box display="flex" gap={1}>
                <Button variant="contained" color="success" startIcon={<CheckCircle />} fullWidth
                  onClick={() => setPlanDialog(true)}>Accept</Button>
                <Button variant="outlined" color="error" startIcon={<Cancel />} fullWidth
                  onClick={() => setPlanDialog(true)}>Reject</Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={planDialog} onClose={() => setPlanDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Recovery Plan Decision</DialogTitle>
        <DialogContent>
          <TextField label="Decision Reason (mandatory)" multiline rows={3} fullWidth sx={{ mt: 1 }}
            value={decisionReason} onChange={(e) => setDecisionReason(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPlanDialog(false)}>Cancel</Button>
          <Button variant="contained" color="success" disabled={!decisionReason.trim()}
            onClick={() => handleDecision('accept')}>Accept Plan</Button>
          <Button variant="outlined" color="error" disabled={!decisionReason.trim()}
            onClick={() => handleDecision('reject')}>Reject Plan</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
