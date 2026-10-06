import { useState } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Grid, FormControl, InputLabel, Select, MenuItem, IconButton, Tooltip,
  CircularProgress,
} from '@mui/material';
import { Add, CheckCircle, Schedule, Flag } from '@mui/icons-material';
import { useMines, useMeetingActions, useCreateMeetingAction } from '../api/hooks';
import { api } from '../api/client';

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success' | 'error' | 'info'> = {
  open: 'info',
  in_progress: 'warning',
  completed: 'success',
  overdue: 'error',
};

export default function MeetingTracker() {
  const { data: mines = [] } = useMines();
  const [mineFilter, setMineFilter] = useState('');
  const { data: actions = [], isLoading } = useMeetingActions(mineFilter || undefined);
  const createAction = useCreateMeetingAction();
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState({
    mine_id: '', meeting_type: 'production', title: '', description: '',
    assigned_to: '', due_date: '',
  });

  const handleCreate = () => {
    if (!form.mine_id || !form.title || !form.assigned_to || !form.due_date) return;
    createAction.mutate({
      ...form,
      meeting_date: new Date().toISOString(),
      due_date: new Date(form.due_date).toISOString(),
    }, {
      onSuccess: () => {
        setDialog(false);
        setForm({ mine_id: '', meeting_type: 'production', title: '', description: '', assigned_to: '', due_date: '' });
      },
    });
  };

  const handleStatusUpdate = async (id: string, status: string) => {
    await api.patch(`/meetings/actions/${id}`, { status });
  };

  const summary = {
    open: actions.filter((a: any) => a.status === 'open').length,
    in_progress: actions.filter((a: any) => a.status === 'in_progress').length,
    overdue: actions.filter((a: any) => a.status === 'overdue').length,
    completed: actions.filter((a: any) => a.status === 'completed').length,
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Meeting Action Tracker</Typography>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Mine</InputLabel>
            <Select value={mineFilter} label="Mine" onChange={(e) => setMineFilter(e.target.value)}>
              <MenuItem value="">All Mines</MenuItem>
              {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
            </Select>
          </FormControl>
          <Button variant="contained" startIcon={<Add />} onClick={() => setDialog(true)}>New Action</Button>
        </Box>
      </Box>

      <Grid container spacing={2} mb={3}>
        {[
          { label: 'Open', count: summary.open, color: 'info.main', icon: <Flag /> },
          { label: 'In Progress', count: summary.in_progress, color: 'warning.main', icon: <Schedule /> },
          { label: 'Overdue', count: summary.overdue, color: 'error.main', icon: <Schedule /> },
          { label: 'Completed', count: summary.completed, color: 'success.main', icon: <CheckCircle /> },
        ].map((s) => (
          <Grid size={{ xs: 6, md: 3 }} key={s.label}>
            <Card>
              <Box p={2} display="flex" alignItems="center" gap={2}>
                <Box sx={{ color: s.color }}>{s.icon}</Box>
                <Box>
                  <Typography variant="h4" fontWeight={700} color={s.color}>{s.count}</Typography>
                  <Typography variant="body2" color="text.secondary">{s.label}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {isLoading ? (
        <Box textAlign="center" py={4}><CircularProgress /></Box>
      ) : (
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Assigned To</TableCell>
                <TableCell>Due Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {actions.map((a: any) => (
                <TableRow key={a.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>{a.title}</Typography>
                    <Typography variant="caption" color="text.secondary">{a.description?.slice(0, 80)}</Typography>
                  </TableCell>
                  <TableCell><Chip size="small" label={a.meeting_type} variant="outlined" /></TableCell>
                  <TableCell>{a.assigned_to}</TableCell>
                  <TableCell>{new Date(a.due_date).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Chip size="small" label={a.status} color={STATUS_COLORS[a.status] || 'default'} />
                  </TableCell>
                  <TableCell align="right">
                    {a.status !== 'completed' && (
                      <>
                        <Tooltip title="Mark In Progress">
                          <IconButton size="small" onClick={() => handleStatusUpdate(a.id, 'in_progress')}>
                            <Schedule fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Mark Complete">
                          <IconButton size="small" color="success" onClick={() => handleStatusUpdate(a.id, 'completed')}>
                            <CheckCircle fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {actions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary" py={4}>No action items</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}

      <Dialog open={dialog} onClose={() => setDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Meeting Action</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} mt={0.5}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Mine</InputLabel>
                <Select value={form.mine_id} label="Mine" onChange={(e) => setForm(f => ({ ...f, mine_id: e.target.value }))}>
                  {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Meeting Type</InputLabel>
                <Select value={form.meeting_type} label="Meeting Type" onChange={(e) => setForm(f => ({ ...f, meeting_type: e.target.value }))}>
                  <MenuItem value="safety">Safety</MenuItem>
                  <MenuItem value="production">Production</MenuItem>
                  <MenuItem value="planning">Planning</MenuItem>
                  <MenuItem value="review">Review</MenuItem>
                  <MenuItem value="emergency">Emergency</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth label="Action Title" value={form.title} onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth multiline rows={2} label="Description" value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField fullWidth label="Assigned To" value={form.assigned_to} onChange={(e) => setForm(f => ({ ...f, assigned_to: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField fullWidth type="date" label="Due Date" value={form.due_date} onChange={(e) => setForm(f => ({ ...f, due_date: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={createAction.isPending || !form.title || !form.mine_id}>
            {createAction.isPending ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
