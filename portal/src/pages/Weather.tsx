import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, Button, Divider,
  Table, TableBody, TableCell, TableHead, TableRow, Alert,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  FormControl, InputLabel, Select, MenuItem, CircularProgress,
} from '@mui/material';
import { WaterDrop, Thermostat, Air, CheckCircle, Cancel } from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import { useMines, useWeatherForecast, useRecoveryPlans } from '../api/hooks';

const WEATHER_CODES: Record<number, string> = {
  0: 'Clear',
  1: 'Partly cloudy',
  2: 'Cloudy',
  3: 'Overcast',
  45: 'Fog',
  51: 'Light drizzle',
  61: 'Light rain',
  63: 'Moderate rain',
  65: 'Heavy rain',
  71: 'Light snow',
  80: 'Showers',
  95: 'Thunderstorm',
};

export default function Weather() {
  const [selectedMine, setSelectedMine] = useState('');
  const [planDialog, setPlanDialog] = useState(false);
  const [decisionReason, setDecisionReason] = useState('');

  const { data: mines = [] } = useMines();
  const { data: forecasts = [], isLoading: forecastLoading } = useWeatherForecast(selectedMine || undefined);
  const { data: recoveryPlans = [], isLoading: plansLoading } = useRecoveryPlans(selectedMine || undefined);

  const plan = recoveryPlans[0];

  const forecastRows = forecasts.map((f: any) => ({
    day: new Date(f.forecast_date).toLocaleDateString(undefined, { weekday: 'short' }),
    temp: f.temperature_max,
    rain: f.precipitation_mm,
    code: WEATHER_CODES[f.weather_code] ?? `Code ${f.weather_code}`,
  }));

  const rainfallChart = forecastRows.map((f: any) => ({ day: f.day, precipitation: f.rain }));

  const todayForecast = forecasts[0];

  const handleDecision = async (action: 'accept' | 'reject') => {
    if (!decisionReason.trim() || !plan) return;
    try {
      await api.post(`/weather/recovery-plans/${plan.id}/decide`, { action, reason: decisionReason });
      setPlanDialog(false);
      setDecisionReason('');
    } catch { /* handled */ }
  };

  if (!selectedMine) {
    return (
      <Box>
        <Typography variant="h5" gutterBottom>Weather & Recovery Planning</Typography>
        <FormControl fullWidth size="small" sx={{ mb: 3, maxWidth: 400 }}>
          <InputLabel>Select Mine</InputLabel>
          <Select value="" label="Select Mine" onChange={(e) => setSelectedMine(e.target.value)}>
            {mines.map((m: any) => (
              <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Alert severity="info">Select a mine to view weather forecasts and recovery plans.</Alert>
      </Box>
    );
  }

  const isLoading = forecastLoading || plansLoading;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Weather & Recovery Planning</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Mine</InputLabel>
          <Select value={selectedMine} label="Mine" onChange={(e) => setSelectedMine(e.target.value)}>
            {mines.map((m: any) => (
              <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Grid container spacing={3} mb={3}>
            {[
              { icon: <Thermostat />, label: 'Temperature', value: todayForecast ? `${todayForecast.temperature_max}°C` : '—', sub: 'Max today', color: '#E65100' },
              { icon: <WaterDrop />, label: 'Precipitation', value: todayForecast ? `${todayForecast.precipitation_mm} mm` : '—', sub: 'Today', color: '#0277BD' },
              { icon: <Air />, label: 'Condition', value: todayForecast ? (WEATHER_CODES[todayForecast.weather_code] || '—') : '—', sub: 'Current forecast', color: '#558B2F' },
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
                      {forecastRows.map((f: any, i: number) => (
                        <TableRow key={i}>
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
                    <BarChart data={rainfallChart}>
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
              {plan ? (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Recovery Plan</Typography>
                    <Chip label={plan.status.toUpperCase()} color="warning" sx={{ mb: 2 }} />

                    <Alert severity="info" sx={{ mb: 2 }}>
                      Production gap of <strong>{plan.gap_tonnes.toLocaleString()} tonnes</strong> detected.
                    </Alert>

                    <Typography variant="subtitle2" gutterBottom>Proposed Daily Targets</Typography>
                    <Table size="small" sx={{ mb: 2 }}>
                      <TableBody>
                        {Object.entries(plan.proposed_daily_targets || {}).map(([day, target]: [string, any]) => (
                          <TableRow key={day}>
                            <TableCell>{day}</TableCell>
                            <TableCell align="right"><strong>{Number(target).toLocaleString()} t</strong></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>

                    <Typography variant="subtitle2" gutterBottom>Rationale</Typography>
                    <Typography variant="body2" color="text.secondary" mb={2}>{plan.rationale}</Typography>

                    <Divider sx={{ my: 2 }} />
                    <Box display="flex" gap={1}>
                      <Button variant="contained" color="success" startIcon={<CheckCircle />} fullWidth
                        onClick={() => setPlanDialog(true)}>Accept</Button>
                      <Button variant="outlined" color="error" startIcon={<Cancel />} fullWidth
                        onClick={() => setPlanDialog(true)}>Reject</Button>
                    </Box>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Recovery Plan</Typography>
                    <Typography color="text.secondary">No active recovery plans for this mine.</Typography>
                  </CardContent>
                </Card>
              )}
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
        </>
      )}
    </Box>
  );
}
