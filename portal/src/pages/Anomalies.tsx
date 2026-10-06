import { useState } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, IconButton, Tooltip, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, LinearProgress, Grid,
} from '@mui/material';
import { CheckCircle, Close, Visibility, AutoAwesome } from '@mui/icons-material';
import { useAnomalies, useAnomalyNarrative } from '../api/hooks';
import { api } from '../api/client';
import type { AnomalyFlag } from '../types';

export default function Anomalies() {
  const { data: anomalies = [] } = useAnomalies();
  const [selected, setSelected] = useState<AnomalyFlag | null>(null);
  const [action, setAction] = useState<'acknowledge' | 'dismiss'>('acknowledge');
  const [reason, setReason] = useState('');

  const handleAction = async () => {
    if (!selected || !reason.trim()) return;
    try {
      await api.post(`/anomalies/${selected.id}/${action}`, { reason });
      setSelected(null);
      setReason('');
    } catch { /* handled */ }
  };

  const flaggedCount = anomalies.filter(a => a.status === 'flagged').length;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5">Anomaly Detection</Typography>
          <Typography variant="body2" color="text.secondary">
            {flaggedCount} active flag{flaggedCount !== 1 ? 's' : ''} requiring review
          </Typography>
        </Box>
      </Box>

      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Metric</TableCell>
              <TableCell align="right">Expected</TableCell>
              <TableCell align="right">Actual</TableCell>
              <TableCell>Score</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {anomalies.map((a) => {
              const deviation = a.actual_value - a.expected_value;
              const pct = a.expected_value !== 0 ? (deviation / a.expected_value) * 100 : 0;
              return (
                <TableRow key={a.id} hover sx={{ bgcolor: a.status === 'flagged' ? 'warning.50' : undefined }}>
                  <TableCell>{new Date(a.flag_date).toLocaleDateString()}</TableCell>
                  <TableCell>{a.metric}</TableCell>
                  <TableCell align="right">{a.expected_value.toLocaleString()}</TableCell>
                  <TableCell align="right">
                    <Typography color={deviation < 0 ? 'error' : 'success.main'} fontWeight={600}>
                      {a.actual_value.toLocaleString()} ({pct >= 0 ? '+' : ''}{pct.toFixed(1)}%)
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <LinearProgress variant="determinate" value={a.anomaly_score * 100}
                        color={a.anomaly_score > 0.8 ? 'error' : a.anomaly_score > 0.5 ? 'warning' : 'info'}
                        sx={{ width: 60, height: 6, borderRadius: 3 }} />
                      <Typography variant="caption">{(a.anomaly_score * 100).toFixed(0)}%</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={a.status}
                      color={a.status === 'flagged' ? 'warning' : a.status === 'acknowledged' ? 'info' : 'default'} />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Details">
                      <IconButton size="small" onClick={() => { setSelected(a); setAction('acknowledge'); }}><Visibility /></IconButton>
                    </Tooltip>
                    {a.status === 'flagged' && (
                      <>
                        <Tooltip title="Acknowledge">
                          <IconButton size="small" color="success"
                            onClick={() => { setSelected(a); setAction('acknowledge'); }}>
                            <CheckCircle />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Dismiss">
                          <IconButton size="small" color="default"
                            onClick={() => { setSelected(a); setAction('dismiss'); }}>
                            <Close />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
            {anomalies.length === 0 && (
              <TableRow><TableCell colSpan={7} align="center">
                <Typography color="text.secondary" py={4}>No anomalies detected</Typography>
              </TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{action === 'acknowledge' ? 'Acknowledge' : 'Dismiss'} Anomaly</DialogTitle>
        <DialogContent>
          {selected && (
            <Box>
              <NarrativeSection anomalyId={selected.id} />
              <Typography variant="subtitle2" gutterBottom>Explanation</Typography>
              <Typography variant="body2" mb={2}>{selected.explanation || 'No explanation generated.'}</Typography>

              <Typography variant="subtitle2" gutterBottom>Contributing Features</Typography>
              <Grid container spacing={1} mb={2}>
                {Object.entries(selected.contributing_features).map(([k, v]) => (
                  <Grid size={{ xs: 6 }} key={k}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="caption">{k}</Typography>
                      <Typography variant="caption" fontWeight={600}>{(v as number).toFixed(2)}</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={Math.abs(v as number) * 100} sx={{ height: 4, borderRadius: 2 }} />
                  </Grid>
                ))}
              </Grid>

              <TextField label="Reason (mandatory)" multiline rows={3} fullWidth required
                value={reason} onChange={(e) => setReason(e.target.value)}
                helperText="Why are you acknowledging / dismissing this anomaly?" />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleAction} disabled={!reason.trim()}
            color={action === 'acknowledge' ? 'success' : 'inherit'}>
            {action === 'acknowledge' ? 'Acknowledge' : 'Dismiss'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function NarrativeSection({ anomalyId }: { anomalyId: string }) {
  const { data: narrative, isLoading } = useAnomalyNarrative(anomalyId);

  if (isLoading) return <LinearProgress sx={{ mb: 2 }} />;
  if (!narrative) return null;

  return (
    <Box mb={3} p={2} sx={{ bgcolor: 'info.50', borderRadius: 1, border: 1, borderColor: 'info.main' }}>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <AutoAwesome fontSize="small" color="info" />
        <Typography variant="subtitle2">Smart Narrative — probable explanation with evidence</Typography>
      </Box>
      <Typography variant="body2" mb={1.5}>{narrative.summary}</Typography>
      {narrative.probable_causes?.length > 0 && (
        <>
          <Typography variant="caption" fontWeight={700}>Probable causes:</Typography>
          {narrative.probable_causes.map((c: any, i: number) => (
            <Typography key={i} variant="caption" display="block" ml={1}>
              • [{c.confidence} confidence] {c.description}
            </Typography>
          ))}
        </>
      )}
      {narrative.evidence?.length > 0 && (
        <>
          <Typography variant="caption" fontWeight={700} display="block" mt={1}>Evidence trail:</Typography>
          {narrative.evidence.map((e: any, i: number) => (
            <Typography key={i} variant="caption" display="block" ml={1} color="text.secondary">
              • {e.detail} <Typography component="span" variant="caption" fontWeight={600}>({e.source_type})</Typography>
            </Typography>
          ))}
        </>
      )}
    </Box>
  );
}
