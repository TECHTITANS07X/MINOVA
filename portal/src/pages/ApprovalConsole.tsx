import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, Table, TableBody, TableCell, TableHead, TableRow,
  IconButton, Tooltip, Tab, Tabs, Alert,
} from '@mui/material';
import { CheckCircle, Undo, ArrowUpward, Visibility } from '@mui/icons-material';
import { useApprovalInbox, useApproveAction } from '../api/hooks';
import type { ApprovalTask } from '../types';

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'error' | 'success' | 'info'> = {
  pending: 'warning',
  overdue: 'error',
  approved: 'success',
  returned: 'info',
};

export default function ApprovalConsole() {
  const { data: tasks = [], isLoading } = useApprovalInbox();
  const approveAction = useApproveAction();
  const [selectedTask, setSelectedTask] = useState<ApprovalTask | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'return' | 'escalate'>('approve');
  const [comment, setComment] = useState('');
  const [tab, setTab] = useState(0);

  const handleAction = () => {
    if (!selectedTask) return;
    approveAction.mutate(
      { taskId: selectedTask.id, action: actionType, comment },
      { onSuccess: () => { setSelectedTask(null); setComment(''); } }
    );
  };

  const filteredTasks = tab === 0 ? tasks : tasks.filter(t => !t.action);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Approval Console</Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={`All (${tasks.length})`} />
        <Tab label={`Pending (${tasks.filter(t => !t.action).length})`} />
      </Tabs>

      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Level</TableCell>
              <TableCell>SLA</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredTasks.map((task) => {
              const isOverdue = task.sla_deadline && new Date(task.sla_deadline) < new Date();
              return (
                <TableRow key={task.id} hover>
                  <TableCell>{task.entity_type}</TableCell>
                  <TableCell>Level {task.current_level}</TableCell>
                  <TableCell>
                    <Chip size="small" label={isOverdue ? 'OVERDUE' : 'On time'}
                      color={isOverdue ? 'error' : 'success'} variant="outlined" />
                  </TableCell>
                  <TableCell>{new Date(task.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Chip size="small" label={task.action || 'Pending'}
                      color={STATUS_COLORS[task.action || 'pending'] || 'default'} />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="View"><IconButton size="small"><Visibility /></IconButton></Tooltip>
                    <Tooltip title="Approve">
                      <IconButton size="small" color="success"
                        onClick={() => { setSelectedTask(task); setActionType('approve'); }}>
                        <CheckCircle />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Return">
                      <IconButton size="small" color="warning"
                        onClick={() => { setSelectedTask(task); setActionType('return'); }}>
                        <Undo />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Escalate">
                      <IconButton size="small" color="info"
                        onClick={() => { setSelectedTask(task); setActionType('escalate'); }}>
                        <ArrowUpward />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              );
            })}
            {filteredTasks.length === 0 && (
              <TableRow><TableCell colSpan={6} align="center">
                <Typography color="text.secondary" py={4}>No approval tasks</Typography>
              </TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={!!selectedTask} onClose={() => setSelectedTask(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {actionType === 'approve' ? 'Approve' : actionType === 'return' ? 'Return' : 'Escalate'} Entry
        </DialogTitle>
        <DialogContent>
          {actionType === 'return' && (
            <Alert severity="info" sx={{ mb: 2 }}>The entry will be returned to the submitter for corrections.</Alert>
          )}
          <TextField label="Comment" multiline rows={3} fullWidth value={comment}
            onChange={(e) => setComment(e.target.value)}
            required={actionType === 'return'}
            helperText={actionType === 'return' ? 'Comment required for returns' : 'Optional'} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedTask(null)}>Cancel</Button>
          <Button variant="contained"
            color={actionType === 'approve' ? 'success' : actionType === 'return' ? 'warning' : 'info'}
            onClick={handleAction}
            disabled={actionType === 'return' && !comment.trim()}>
            {actionType.charAt(0).toUpperCase() + actionType.slice(1)}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
