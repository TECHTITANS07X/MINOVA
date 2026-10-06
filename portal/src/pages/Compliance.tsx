import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Grid, Button, Table, TableBody, TableCell,
  TableHead, TableRow, Alert, LinearProgress, Tooltip,
} from '@mui/material';
import { Sync, Gavel, Error as ErrorIcon, Timelapse, CheckCircle } from '@mui/icons-material';
import { useComplianceFilings, useComplianceSync } from '../api/hooks';

const STATUS_META: Record<string, { color: any; icon: any; label: string }> = {
  late: { color: 'error', icon: <ErrorIcon />, label: 'LATE' },
  incomplete: { color: 'warning', icon: <Timelapse />, label: 'Incomplete' },
  ready: { color: 'success', icon: <CheckCircle />, label: 'Ready' },
  submitted: { color: 'success', icon: <CheckCircle />, label: 'Submitted' },
  not_started: { color: 'default', icon: <Timelapse />, label: 'Not started' },
};

export default function Compliance() {
  const { data: filings = [] } = useComplianceFilings();
  const sync = useComplianceSync();
  const [syncedAt, setSyncedAt] = useState<string | null>(null);

  const counts = filings.reduce((acc: Record<string, number>, f: any) => {
    acc[f.status] = (acc[f.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5">Statutory Compliance Sentinel</Typography>
          <Typography variant="body2" color="text.secondary">
            Every DGMS / MoEF / PCB deadline across all mines, with data-completeness tracking — missing one can shut a mine
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Sync />} loading={sync.isPending}
          onClick={() => sync.mutate(undefined, { onSuccess: (d: any) => setSyncedAt(d.synced_at) })}>
          Sync Deadlines
        </Button>
      </Box>

      <Grid container spacing={2} mb={3}>
        {['late', 'incomplete', 'ready', 'submitted'].map((s) => (
          <Grid size={{ xs: 6, sm: 3 }} key={s}>
            <Card><CardContent sx={{ textAlign: 'center', py: 2 }}>
              <Box display="flex" justifyContent="center" alignItems="center" gap={1}>
                {STATUS_META[s].icon}
                <Typography variant="h4" fontWeight={700} color={s === 'late' ? 'error.main' : s === 'incomplete' ? 'warning.main' : 'success.main'}>
                  {counts[s] ?? 0}
                </Typography>
              </Box>
              <Typography variant="caption">{STATUS_META[s].label}</Typography>
            </CardContent></Card>
          </Grid>
        ))}
      </Grid>

      {syncedAt && <Alert severity="success" sx={{ mb: 2 }}>Deadlines re-synced at {new Date(syncedAt).toLocaleTimeString()}</Alert>}

      <Card>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Obligation</TableCell>
              <TableCell>Authority</TableCell>
              <TableCell>Mine</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Due</TableCell>
              <TableCell>Data completeness</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filings.map((f: any) => (
              <TableRow key={f.filing_id} hover sx={{ bgcolor: f.status === 'late' ? 'error.50' : undefined }}>
                <TableCell>{f.obligation_title}</TableCell>
                <TableCell><Chip size="small" label={f.authority?.toUpperCase()} /></TableCell>
                <TableCell>{f.mine_name}</TableCell>
                <TableCell>
                  <Typography variant="caption">{f.period_start} → {f.period_end}</Typography>
                </TableCell>
                <TableCell>
                  <Tooltip title={f.due_in_days >= 0 ? `${f.due_in_days} days remaining` : `${-f.due_in_days} days overdue`}>
                    <Typography variant="body2" fontWeight={f.status === 'late' ? 700 : 400} color={f.status === 'late' ? 'error' : 'inherit'}>
                      {f.due_date}
                    </Typography>
                  </Tooltip>
                </TableCell>
                <TableCell sx={{ minWidth: 140 }}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <LinearProgress variant="determinate" value={f.completion_pct}
                      color={f.completion_pct >= 100 ? 'success' : f.completion_pct > 0 ? 'warning' : 'inherit'}
                      sx={{ flex: 1, height: 6, borderRadius: 3 }} />
                    <Typography variant="caption">{f.completion_pct.toFixed(0)}%</Typography>
                  </Box>
                  {f.missing_metrics?.length > 0 && (
                    <Typography variant="caption" color="text.secondary">
                      missing: {f.missing_metrics.join(', ')}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip size="small" icon={STATUS_META[f.status]?.icon} label={STATUS_META[f.status]?.label ?? f.status}
                    color={STATUS_META[f.status]?.color ?? 'default'} />
                </TableCell>
              </TableRow>
            ))}
            {filings.length === 0 && (
              <TableRow><TableCell colSpan={7} align="center">
                <Typography color="text.secondary" py={4}>
                  <Gavel sx={{ verticalAlign: 'middle', mr: 1 }} />
                  No filings yet — click "Sync Deadlines" to compute obligations × mines
                </Typography>
              </TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Box>
  );
}
