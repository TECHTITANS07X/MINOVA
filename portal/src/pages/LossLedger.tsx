import {
  Box, Card, CardContent, Typography, Chip, Grid,
  Alert, Accordion, AccordionSummary, AccordionDetails, LinearProgress,
} from '@mui/material';
import { ExpandMore, AccountBalanceWallet } from '@mui/icons-material';
import { useLossLedgerSummary } from '../api/hooks';

export default function LossLedger() {
  const { data: summary } = useLossLedgerSummary();
  const mines = summary?.mines ?? [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Production Loss Ledger — Recovery Debt</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Every verified loss event is carried forward as debt into future planning — no more rediscovering gaps in each review meeting
      </Typography>

      {summary && (
        <Alert severity={summary.total_open_debt > 0 ? 'warning' : 'success'} sx={{ mb: 3 }}>
          <Typography variant="subtitle2">
            Total open recovery debt: {summary.total_open_debt.toLocaleString()} tonnes across {mines.length} mine(s)
          </Typography>
          <Typography variant="caption">
            Open debt = verified losses (equipment, weather, power, blasting) not yet recovered. Feeds weather-aware recovery planning.
          </Typography>
        </Alert>
      )}

      <Grid container spacing={3}>
        {mines.map((m: any) => (
          <Grid size={{ xs: 12, md: 6 }} key={m.mine_id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="h6">{m.mine_name}</Typography>
                  <Chip size="small" label={`${m.open_debt.toLocaleString()} t open`} color="warning" />
                </Box>
                <Box display="flex" gap={3} mb={2}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Total lost</Typography>
                    <Typography variant="body1" fontWeight={700}>{m.total_lost.toLocaleString()} t</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Recovered</Typography>
                    <Typography variant="body1" fontWeight={700} color="success.main">{m.recovered.toLocaleString()} t</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Recovery rate</Typography>
                    <Typography variant="body1" fontWeight={700}>{m.recovery_rate_pct}%</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Events</Typography>
                    <Typography variant="body1" fontWeight={700}>{m.events}</Typography>
                  </Box>
                </Box>
                <LinearProgress variant="determinate" value={m.recovery_rate_pct}
                  sx={{ height: 8, borderRadius: 4, mb: 2 }} color={m.recovery_rate_pct > 60 ? 'success' : 'warning'} />
                <Accordion elevation={0} sx={{ border: 1, borderColor: 'divider' }}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="body2">Loss breakdown by cause ({Object.keys(m.by_cause).length})</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {Object.entries(m.by_cause).sort((a: any, b: any) => b[1] - a[1]).map(([cause, tonnes]: [string, any]) => (
                      <Box key={cause} display="flex" justifyContent="space-between" mb={0.5}>
                        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                          {cause.replace(/_/g, ' ')}
                        </Typography>
                        <Typography variant="body2" fontWeight={700}>{Number(tonnes).toLocaleString()} t</Typography>
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {mines.length === 0 && (
        <Card><CardContent sx={{ textAlign: 'center', py: 6 }}>
          <AccountBalanceWallet sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          <Typography color="text.secondary">No losses ledgered yet — POST /loss-ledger/derive to build from approved cause records</Typography>
        </CardContent></Card>
      )}
    </Box>
  );
}
