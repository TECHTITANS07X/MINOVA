import { useState } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, TextField, Grid, FormControl, InputLabel, Select, MenuItem, Alert, Button,
  Tooltip, IconButton, CircularProgress,
} from '@mui/material';
import { VerifiedUser, Warning, ContentCopy } from '@mui/icons-material';
import { api } from '../api/client';
import { useAuditEvents } from '../api/hooks';

const ACTION_COLORS: Record<string, 'success' | 'info' | 'warning' | 'error' | 'default'> = {
  'shift_entry.submit': 'info',
  'approval.approve': 'success',
  'approval.return': 'warning',
  'calc_run.execute': 'default',
  'anomaly.flag': 'error',
  'conflict.resolve': 'warning',
};

export default function AuditExplorer() {
  const [actionFilter, setActionFilter] = useState('');
  const [searchActor, setSearchActor] = useState('');
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [verifying, setVerifying] = useState(false);

  const { data: auditData, isLoading } = useAuditEvents({
    action: actionFilter || undefined,
    actor: searchActor || undefined,
  });

  const verifyChain = async () => {
    setVerifying(true);
    try {
      const res = await api.get('/admin/audit/verify');
      setChainValid(res.data.valid);
    } catch {
      setChainValid(false);
    }
    setVerifying(false);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Audit Trail Explorer</Typography>
        <Button variant="outlined" startIcon={<VerifiedUser />} onClick={verifyChain} disabled={verifying}>
          Verify Chain Integrity
        </Button>
      </Box>

      {chainValid === true && <Alert severity="success" sx={{ mb: 2 }}>Hash chain verified — no tampering detected.</Alert>}
      {chainValid === false && <Alert severity="error" sx={{ mb: 2 }} icon={<Warning />}>Chain integrity check FAILED — possible tampering detected.</Alert>}

      <Grid container spacing={2} mb={3}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <TextField fullWidth size="small" label="Search by actor" value={searchActor}
            onChange={(e) => setSearchActor(e.target.value)} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Action</InputLabel>
            <Select value={actionFilter} label="Action" onChange={(e) => setActionFilter(e.target.value)}>
              <MenuItem value="">All Actions</MenuItem>
              <MenuItem value="shift_entry.submit">Submit Entry</MenuItem>
              <MenuItem value="approval.approve">Approve</MenuItem>
              <MenuItem value="approval.return">Return</MenuItem>
              <MenuItem value="calc_run.execute">Calculation Run</MenuItem>
              <MenuItem value="anomaly.flag">Anomaly Flag</MenuItem>
              <MenuItem value="conflict.resolve">Conflict Resolution</MenuItem>
            </Select>
          </FormControl>
        </Grid>
      </Grid>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : (
        <Card>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Actor</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>Details</TableCell>
                <TableCell>Hash</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {auditData?.items?.map((e: any) => (
                <TableRow key={e.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {new Date(e.ts).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={e.actor} variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={e.action} color={ACTION_COLORS[e.action] || 'default'} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{e.entity_type}</Typography>
                    <br />
                    <Typography variant="caption" color="text.secondary">{e.entity_id}</Typography>
                  </TableCell>
                  <TableCell>
                    {typeof e.details === 'object' ? JSON.stringify(e.details) : e.details}
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <Typography variant="caption" fontFamily="monospace">{e.event_hash}</Typography>
                      <Tooltip title="Copy hash">
                        <IconButton size="small" onClick={() => navigator.clipboard.writeText(e.event_hash)}>
                          <ContentCopy sx={{ fontSize: 14 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </Box>
  );
}
