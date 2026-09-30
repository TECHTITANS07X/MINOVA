import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, TextField, Grid, FormControl, InputLabel, Select, MenuItem, Alert, Button,
  Tooltip, IconButton,
} from '@mui/material';
import { VerifiedUser, Warning, ContentCopy } from '@mui/icons-material';
import { api } from '../api/client';

interface AuditEntry {
  id: string;
  ts: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  prev_hash: string;
  event_hash: string;
  details: string;
}

const MOCK_AUDIT: AuditEntry[] = [
  { id: 'ae-1', ts: '2026-09-30T08:00:12Z', actor: 'shift_supervisor_1', action: 'shift_entry.submit', entity_type: 'ShiftEntry', entity_id: 'se-101', prev_hash: '0000000000', event_hash: 'a3f8c2d1e5', details: 'Submitted shift 1 entry for Bench A1' },
  { id: 'ae-2', ts: '2026-09-30T08:15:33Z', actor: 'mine_manager_1', action: 'approval.approve', entity_type: 'ApprovalTask', entity_id: 'at-201', prev_hash: 'a3f8c2d1e5', event_hash: 'b7e4a9f6c3', details: 'Approved shift entry se-101' },
  { id: 'ae-3', ts: '2026-09-30T09:00:01Z', actor: 'system', action: 'calc_run.execute', entity_type: 'CalcRun', entity_id: 'cr-301', prev_hash: 'b7e4a9f6c3', event_hash: 'c1d5b8e2a7', details: 'Daily rollup for 2026-09-30' },
  { id: 'ae-4', ts: '2026-09-30T10:30:45Z', actor: 'data_entry_op_2', action: 'shift_entry.submit', entity_type: 'ShiftEntry', entity_id: 'se-102', prev_hash: 'c1d5b8e2a7', event_hash: 'd9c3f7a1b5', details: 'Submitted shift 2 entry for Bench B3' },
  { id: 'ae-5', ts: '2026-09-30T11:00:00Z', actor: 'system', action: 'anomaly.flag', entity_type: 'AnomalyFlag', entity_id: 'af-401', prev_hash: 'd9c3f7a1b5', event_hash: 'e2a6d8c4f1', details: 'Flagged anomaly: OB removal 45% below expected' },
];

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

  const filtered = MOCK_AUDIT.filter((e) => {
    if (actionFilter && e.action !== actionFilter) return false;
    if (searchActor && !e.actor.toLowerCase().includes(searchActor.toLowerCase())) return false;
    return true;
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
            {filtered.map((e) => (
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
                <TableCell>{e.details}</TableCell>
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
    </Box>
  );
}
