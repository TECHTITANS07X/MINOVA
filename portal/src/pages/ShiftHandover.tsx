import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Grid, Button, Alert, List, ListItem,
  ListItemIcon, ListItemText, MenuItem, Select, FormControl, InputLabel,
} from '@mui/material';
import { Bolt, Warning, CheckCircle, Sync } from '@mui/icons-material';
import { useHandovers, useGenerateHandover, useMines } from '../api/hooks';

export default function ShiftHandover() {
  const { data: handovers = [] } = useHandovers();
  const { data: mines = [] } = useMines();
  const generate = useGenerateHandover();
  const [mineId, setMineId] = useState('');
  const [shiftNumber, setShiftNumber] = useState('first');
  const [selected, setSelected] = useState<any>(null);

  const current = selected ?? handovers[0];
  const brief = current?.brief ?? {};

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5">Shift Handover Intelligence</Typography>
          <Typography variant="body2" color="text.secondary">
            Auto-generated structured brief — the incoming shift sees everything, nothing lost between shifts
          </Typography>
        </Box>
        <Box display="flex" gap={1}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Mine</InputLabel>
            <Select value={mineId} label="Mine" onChange={(e) => setMineId(e.target.value)}>
              {(mines as any[]).map((m) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Shift</InputLabel>
            <Select value={shiftNumber} label="Shift" onChange={(e) => setShiftNumber(e.target.value)}>
              <MenuItem value="first">First</MenuItem>
              <MenuItem value="second">Second</MenuItem>
              <MenuItem value="third">Third</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" startIcon={<Sync />} loading={generate.isPending}
            disabled={!mineId} onClick={() => generate.mutate({ mineId, shiftNumber })}>
            Generate
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Handover Log</Typography>
              {handovers.map((h: any) => (
                <Card key={h.id} variant="outlined" sx={{ p: 1.5, mb: 1, cursor: 'pointer', bgcolor: current?.id === h.id ? 'action.selected' : undefined }}
                  onClick={() => setSelected(h)}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" fontWeight={600}>
                      {h.brief?.mine?.name ?? 'Mine'} — {h.outgoing_shift} shift
                    </Typography>
                    {h.acknowledged_at
                      ? <CheckCircle fontSize="small" color="success" />
                      : <Chip size="small" label="pending" color="warning" />}
                  </Box>
                  <Typography variant="caption" color="text.secondary">{h.shift_date?.slice(0, 10)}</Typography>
                </Card>
              ))}
              {handovers.length === 0 && <Alert severity="info">No handovers generated yet</Alert>}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          {current ? (
            <>
              {current.critical_items?.length > 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Critical items for the incoming shift</Typography>
                  <List dense disablePadding>
                    {current.critical_items.map((item: string, i: number) => (
                      <ListItem key={i} disableGutters>
                        <ListItemIcon sx={{ minWidth: 32 }}><Warning fontSize="small" color="warning" /></ListItemIcon>
                        <ListItemText primary={item} primaryTypographyProps={{ variant: 'body2' }} />
                      </ListItem>
                    ))}
                  </List>
                </Alert>
              )}
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Card><CardContent>
                    <Typography variant="subtitle2" gutterBottom>Production (this shift)</Typography>
                    <Typography variant="h4" fontWeight={700}>
                      {(brief.production?.production_tonnes ?? 0).toLocaleString()} <Typography component="span" variant="caption">t</Typography>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {brief.production?.achievement_pct != null
                        ? `${brief.production.achievement_pct}% of prorated target`
                        : 'target n/a'} · OB {(brief.production?.overburden_m3 ?? 0).toLocaleString()} m³
                    </Typography>
                  </CardContent></Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Card><CardContent>
                    <Typography variant="subtitle2" gutterBottom>Equipment</Typography>
                    <Typography variant="h4" fontWeight={700} color={brief.equipment?.hours_lost > 0 ? 'warning.main' : 'success.main'}>
                      {brief.equipment?.hours_lost ?? 0} h
                    </Typography>
                    <Typography variant="caption" color="text.secondary">stoppage hours this shift</Typography>
                    {(brief.equipment?.stoppages ?? []).map((s: any, i: number) => (
                      <Typography key={i} variant="caption" display="block">• {s.description}</Typography>
                    ))}
                  </CardContent></Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card><CardContent>
                    <Typography variant="subtitle2" gutterBottom>Weather</Typography>
                    {brief.weather ? (
                      <Typography variant="body2">
                        {brief.weather.precipitation_mm} mm rain · {brief.weather.temp_max}°C max
                      </Typography>
                    ) : <Typography variant="caption" color="text.secondary">No observation</Typography>}
                  </CardContent></Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card><CardContent>
                    <Typography variant="subtitle2" gutterBottom>Safety</Typography>
                    <Typography variant="body2">
                      {(brief.safety?.observations ?? []).length === 0
                        ? 'No safety observations this shift'
                        : `${brief.safety.observations.length} observation(s)`}
                    </Typography>
                  </CardContent></Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card><CardContent>
                    <Typography variant="subtitle2" gutterBottom>Pending</Typography>
                    <Typography variant="body2">
                      {brief.pending?.count ?? 0} unapproved entr{(brief.pending?.count ?? 0) === 1 ? 'y' : 'ies'}
                    </Typography>
                  </CardContent></Card>
                </Grid>
              </Grid>
              <Box mt={2} display="flex" alignItems="center" gap={1}>
                <Bolt fontSize="small" color="primary" />
                <Typography variant="caption" color="text.secondary">
                  Generated deterministically from approved shift data at {new Date(current.generated_at).toLocaleString()}
                </Typography>
              </Box>
            </>
          ) : (
            <Card><CardContent sx={{ py: 8, textAlign: 'center' }}>
              <Typography color="text.secondary">Select or generate a handover brief</Typography>
            </CardContent></Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
