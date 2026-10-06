import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead,
  TableRow, Button, TextField, Grid, Chip, IconButton, Dialog, DialogTitle, DialogContent,
  DialogActions, Alert, CircularProgress,
} from '@mui/material';
import { Add, Edit, Settings } from '@mui/icons-material';
import { api } from '../api/client';
import { useMines, useUsers, useApprovalChains, useSystemHealth } from '../api/hooks';

function TabPanel({ children, value, index }: { children: React.ReactNode; value: number; index: number }) {
  return value === index ? <Box mt={2}>{children}</Box> : null;
}

export default function Admin() {
  const [tab, setTab] = useState(0);
  const [mineDialog, setMineDialog] = useState(false);
  const [mineName, setMineName] = useState('');
  const [mineCode, setMineCode] = useState('');

  const { data: mines = [], isLoading: minesLoading } = useMines();
  const { data: users = [], isLoading: usersLoading } = useUsers();
  const { data: approvalChains = [], isLoading: chainsLoading } = useApprovalChains();
  const { data: health, isLoading: healthLoading } = useSystemHealth();

  const getMineNameById = (mineId: string) => {
    const mine = mines.find((m: any) => m.id === mineId);
    return mine?.name || mineId;
  };

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
        {minesLoading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : (
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
                {mines.map((m: any) => (
                  <TableRow key={m.id} hover>
                    <TableCell><Chip size="small" label={m.code} /></TableCell>
                    <TableCell>{m.name}</TableCell>
                    <TableCell>{'—'}</TableCell>
                    <TableCell><Chip size="small" label={m.is_active ? 'Active' : 'Inactive'} color={m.is_active ? 'success' : 'default'} /></TableCell>
                    <TableCell align="right">
                      <IconButton size="small"><Edit /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}

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
        {usersLoading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : (
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
                {users.map((u: any) => (
                  <TableRow key={u.id} hover>
                    <TableCell><Typography variant="body2" fontFamily="monospace">{u.username}</Typography></TableCell>
                    <TableCell>{u.full_name}</TableCell>
                    <TableCell>
                      <Box display="flex" gap={0.5} flexWrap="wrap">
                        {u.roles?.map((role: string) => (
                          <Chip key={role} size="small" label={role} variant="outlined" />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell>{getMineNameById(u.mine_id)}</TableCell>
                    <TableCell><Chip size="small" label={u.is_active ? 'Active' : 'Disabled'} color={u.is_active ? 'success' : 'default'} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
        <Alert severity="info" sx={{ mt: 2 }}>Users and roles are managed through Keycloak. Changes here sync via OIDC claims.</Alert>
      </TabPanel>

      <TabPanel value={tab} index={2}>
        {chainsLoading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : (
          approvalChains.map((chain: any) => (
            <Card key={chain.id} sx={{ mb: 2 }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="subtitle1" fontWeight={600}>{chain.name}</Typography>
                  <Box display="flex" gap={1}>
                    <Chip size="small" label={chain.report_type} variant="outlined" />
                    <Chip size="small" label={getMineNameById(chain.mine_id)} variant="outlined" />
                  </Box>
                </Box>
                <Chip size="small" label={chain.is_active ? 'Active' : 'Inactive'} color={chain.is_active ? 'success' : 'default'} />
              </CardContent>
            </Card>
          ))
        )}
      </TabPanel>

      <TabPanel value={tab} index={3}>
        {healthLoading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : (
          <Grid container spacing={2}>
            {health?.checks && Object.entries(health.checks).map(([name, status]: [string, any]) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={name}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="subtitle1" fontWeight={600}>{name}</Typography>
                      <Chip size="small" label={status ? 'running' : 'stopped'} color={status ? 'success' : 'error'} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            {health?.status && (
              <Grid size={{ xs: 12 }}>
                <Alert severity={health.status === 'ok' ? 'success' : 'warning'}>
                  Overall system status: {health.status}
                </Alert>
              </Grid>
            )}
          </Grid>
        )}
      </TabPanel>
    </Box>
  );
}
