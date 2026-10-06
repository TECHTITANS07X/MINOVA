import {
  Box, Card, CardContent, Typography, Chip, Grid, Table, TableBody, TableCell,
  TableHead, TableRow, Alert,
} from '@mui/material';
import { Science, TrendingDown, TrendingUp, CheckCircle } from '@mui/icons-material';
import { useQualityPredictions, useQualitySummary } from '../api/hooks';

export default function QualityCorrelation() {
  const { data: predictions = [] } = useQualityPredictions();
  const { data: summary } = useQualitySummary();

  const riskColor = (risk: string) => (risk === 'high' ? 'error' : risk === 'medium' ? 'warning' : 'success');

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Quality-Dispatch Correlation</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Predicts grade (GCV) slippage from production patterns BEFORE the UTTAM lab result arrives (~1-week lag closed)
      </Typography>

      {summary && (
        <Grid container spacing={2} mb={3}>
          <Grid size={{ xs: 6, md: 3 }}>
            <Card><CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" fontWeight={700} color="error">{summary.flagged}</Typography>
              <Typography variant="caption">High/Medium risk flags</Typography>
            </CardContent></Card>
          </Grid>
          <Grid size={{ xs: 6, md: 3 }}>
            <Card><CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" fontWeight={700}>{summary.pending_lab}</Typography>
              <Typography variant="caption">Awaiting lab confirmation</Typography>
            </CardContent></Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Alert severity="info" sx={{ height: '100%' }}>
              <Typography variant="body2">
                Flags are raised at dispatch time. When the lab result lands, confirmations either clear the flag or
                raise a Truth Gate conflict for human resolution.
              </Typography>
            </Alert>
          </Grid>
        </Grid>
      )}

      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell align="right">Pattern GCV</TableCell>
              <TableCell align="right">Declared</TableCell>
              <TableCell align="right">Deviation</TableCell>
              <TableCell>Risk</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Lab Result</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {predictions.map((p) => (
              <TableRow key={p.id} hover>
                <TableCell>{new Date(p.prediction_date).toLocaleDateString()}</TableCell>
                <TableCell align="right">{Number(p.predicted_gcv).toLocaleString()}</TableCell>
                <TableCell align="right"><Typography fontWeight={700}>{Number(p.declared_gcv).toLocaleString()}</Typography></TableCell>
                <TableCell align="right">
                  <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5}>
                    {Number(p.deviation_pct) >= 0 ? <TrendingUp fontSize="small" color="error" /> : <TrendingDown fontSize="small" color="success" />}
                    {Number(p.deviation_pct).toFixed(1)}%
                  </Box>
                </TableCell>
                <TableCell><Chip size="small" label={p.risk} color={riskColor(p.risk)} /></TableCell>
                <TableCell><Chip size="small" label={p.status.replace('_', ' ')} variant="outlined" /></TableCell>
                <TableCell>
                  {p.lab_gcv ? (
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <CheckCircle fontSize="small" color={Math.abs(Number(p.lab_gcv) - Number(p.declared_gcv)) > 50 ? 'error' : 'success'} />
                      {Number(p.lab_gcv).toLocaleString()}
                    </Box>
                  ) : <Typography variant="caption" color="text.secondary">pending (~1 week)</Typography>}
                </TableCell>
              </TableRow>
            ))}
            {predictions.length === 0 && (
              <TableRow><TableCell colSpan={7} align="center">
                <Typography color="text.secondary" py={4}>
                  <Science sx={{ verticalAlign: 'middle', mr: 1 }} />No predictions — POST /quality/predict with a declared GCV
                </Typography>
              </TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Box>
  );
}
