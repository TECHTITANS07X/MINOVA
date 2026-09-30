import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead,
  TableRow, Button, TextField, Grid, Chip, IconButton, Dialog, DialogTitle, DialogContent,
  DialogActions, FormControl, InputLabel, Select, MenuItem, Alert,
} from '@mui/material';
import { Add, Edit, Delete, Settings } from '@mui/icons-material';
import { useMines } from '../api/hooks';
import { api } from '../api/client';

function TabPanel({ children, value, index }: { children: React.ReactNode; value: number; index: number }) {
  return value === index ? <Box mt={2}>{children}</Box> : null;
}

const DEMO_USERS = [
  { username: 'admin_user', name: 'Admin User', role: 'admin', mine: 'All', active: true },
  { username: 'mine_manager_1', name: 'Rajesh Kumar', role: 'mine_manager', mine: 'Mine Alpha', active: true },
  { username: 'shift_supervisor_1', name: 'Anil Singh', role: 'shift_supervisor', mine: 'Mine Alpha', active: true },
  { username: 'data_entry_op_1', name: 'Priya Sharma', role: 'data_entry_operator', mine: 'Mine Alpha', active: true },
  { username: 'geologist_1', name: 'Suresh Reddy', role: 'geologist', mine: 'Mine Beta', active: true },
  { username: 'safety_officer_1', name: 'Meena Patel', role: 'safety_officer', mine: 'Mine Alpha', active: false },
];

const APPROVAL_CHAINS = [
  { id: 'ac-1', name: 'Standard Shift Entry', levels: ['Shift Supervisor', 'Mine Manager', 'Regional Director'], mine: 'Mine Alpha' },
  { id: 'ac-2', name: 'High-Value Entry (>10,000t)', levels: ['Mine Manager', 'Regional Director', 'HQ Admin'], mine: 'All' },
];

export default function Admin() {
  const [tab, setTab] = useState(0);
  const { data: mines = [] } = useMines();
  const [mineDialog, setMineDialog] = useState(false);
  const [mineName, setMineName] = useState('');
  const [mineCode, setMineCode] = useState('');

  const handleCreateMine = async () => {
    if (!mineName.trim() || !mineCode.trim()) return;
    try {
      await api.post('/admin/mines', { name: mineName, code: mineCode });
      setMineDialog(false);
      setMineName('');
      setMineCode('');
    } catch { /* handled */ }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5"><Settings sx={{ verticalAlign: 'middle', mr: 1 }} />Administration</Typography>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Mines & Benches" />
          <Tab label="Users & Roles" />
          <Tab label="Approval Chains" />
          <Tab label="System Health" />
        </Tabs>
      </Box>

      <TabPanel value={tab} index={0}>
        <Box display="flex" justifyContent="flex-end" mb={2}>
          <Button variant="contained" startIcon={<Add />} onClick={() => setMineDialog(true)}>Add Mine</Button>
        </Box>
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Code</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Benches</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {[
                { code: 'ALPHA', name: 'DEMO Mine Alpha', benches: 4, active: true },
                { code: 'BETA', name: 'DEMO Mine Beta', benches: 3, active: true },
                { code: 'GAMMA', name: 'DEMO Mine Gamma', benches: 2, active: false },
              ].map((m) => (
                <TableRow key={m.code} hover>
                  <TableCell><Chip size="small" label={m.code} /></TableCell>
                  <TableCell>{m.name}</TableCell>
                  <TableCell>{m.benches}</TableCell>
                  <TableCell><Chip size="small" label={m.active ? 'Active' : 'Inactive'} color={m.active ? 'success' : 'default'} /></TableCell>
                  <TableCell align="right">
                    <IconButton size="small"><Edit /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>

        <Dialog open={mineDialog} onClose={() => setMineDialog(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Add Mine</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} mt={0.5}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField fullWidth label="Mine Code" value={mineCode} onChange={(e) => setMineCode(e.target.value)} />
              </Grid>
              <Grid size={{ xs: 12, sm: 8 }}>
                <TextField fullWidth label="Mine Name" value={mineName} onChange={(e) => setMineName(e.target.value)} />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMineDialog(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleCreateMine} disabled={!mineName.trim() || !mineCode.trim()}>Create</Button>
          </DialogActions>
        </Dialog>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Username</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Mine</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {DEMO_USERS.map((u) => (
                <TableRow key={u.username} hover>
                  <TableCell><Typography variant="body2" fontFamily="monospace">{u.username}</Typography></TableCell>
                  <TableCell>{u.name}</TableCell>
                  <TableCell><Chip size="small" label={u.role} variant="outlined" /></TableCell>
                  <TableCell>{u.mine}</TableCell>
                  <TableCell><Chip size="small" label={u.active ? 'Active' : 'Disabled'} color={u.active ? 'success' : 'default'} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
        <Alert severity="info" sx={{ mt: 2 }}>Users and roles are managed through Keycloak. Changes here sync via OIDC claims.</Alert>
      </TabPanel>

      <TabPanel value={tab} index={2}>
        {APPROVAL_CHAINS.map((chain) => (
          <Card key={chain.id} sx={{ mb: 2 }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="subtitle1" fontWeight={600}>{chain.name}</Typography>
                <Chip size="small" label={chain.mine} variant="outlined" />
              </Box>
              <Box display="flex" gap={1} alignItems="center">
                {chain.levels.map((level, i) => (
                  <Box key={level} display="flex" alignItems="center" gap={1}>
                    <Chip label={`${i + 1}. ${level}`} color={i === 0 ? 'primary' : 'default'} />
                    {i < chain.levels.length - 1 && <Typography color="text.secondary">→</Typography>}
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        ))}
      </TabPanel>

      <TabPanel value={tab} index={3}>
        <Grid container spacing={2}>
          {[
            { service: 'PostgreSQL', status: 'running', port: 5432, detail: 'v16.9, PostGIS + pgvector' },
            { service: 'Keycloak', status: 'running', port: 8080, detail: 'v26, MINOVA realm' },
            { service: 'MinIO', status: 'stopped', port: 9000, detail: 'S3-compatible storage' },
            { service: 'Temporal', status: 'running', port: 7233, detail: 'Workflow engine' },
            { service: 'Ollama', status: 'running', port: 11434, detail: 'Qwen3:8b loaded' },
            { service: 'FastAPI', status: 'running', port: 8000, detail: 'Backend API' },
          ].map((s) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={s.service}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle1" fontWeight={600}>{s.service}</Typography>
                    <Chip size="small" label={s.status}
                      color={s.status === 'running' ? 'success' : 'error'} />
                  </Box>
                  <Typography variant="body2" color="text.secondary">Port {s.port}</Typography>
                  <Typography variant="caption" color="text.secondary">{s.detail}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>
    </Box>
  );
}
