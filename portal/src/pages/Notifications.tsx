import { useState } from 'react';
import {
  Box, Typography, Card, List, ListItemButton, ListItemIcon, ListItemText, Chip,
  IconButton, Tooltip, Divider, Tabs, Tab, Button,
} from '@mui/material';
import {
  Approval, Warning, Description, Calculate, Gavel, NotificationsActive,
  DoneAll, MarkEmailRead,
} from '@mui/icons-material';

interface Notification {
  id: string;
  type: 'approval' | 'anomaly' | 'conflict' | 'report' | 'calculation' | 'system';
  title: string;
  body: string;
  time: string;
  read: boolean;
}

const MOCK_NOTIFICATIONS: Notification[] = [
  { id: 'n1', type: 'approval', title: 'Approval Required', body: 'Shift entry SE-101 from Bench A1 is pending your approval.', time: '10 min ago', read: false },
  { id: 'n2', type: 'anomaly', title: 'Anomaly Detected', body: 'OB removal at Bench B3 is 45% below expected value.', time: '25 min ago', read: false },
  { id: 'n3', type: 'conflict', title: 'Conflict Flagged', body: 'Conflicting values for production tonnage on 2026-09-30.', time: '1 hr ago', read: false },
  { id: 'n4', type: 'report', title: 'Weekly Report Ready', body: 'Weekly report for Sep 23-29 has been generated and is ready for review.', time: '2 hrs ago', read: true },
  { id: 'n5', type: 'calculation', title: 'Calc Run Complete', body: 'Daily rollup for 2026-09-30 completed successfully.', time: '3 hrs ago', read: true },
  { id: 'n6', type: 'system', title: 'Service Alert', body: 'MinIO storage service is currently unavailable.', time: '5 hrs ago', read: true },
];

const TYPE_ICONS: Record<string, React.ReactElement> = {
  approval: <Approval color="success" />,
  anomaly: <Warning color="error" />,
  conflict: <Gavel color="warning" />,
  report: <Description color="info" />,
  calculation: <Calculate />,
  system: <NotificationsActive color="secondary" />,
};

export default function Notifications() {
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);
  const [tab, setTab] = useState(0);

  const unread = notifications.filter(n => !n.read);
  const filtered = tab === 0 ? notifications : tab === 1 ? unread : notifications.filter(n => n.read);

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const markRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h5">Notifications</Typography>
          <Typography variant="body2" color="text.secondary">
            {unread.length} unread notification{unread.length !== 1 ? 's' : ''}
          </Typography>
        </Box>
        <Button variant="text" startIcon={<DoneAll />} onClick={markAllRead} disabled={unread.length === 0}>
          Mark all read
        </Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={`All (${notifications.length})`} />
        <Tab label={`Unread (${unread.length})`} />
        <Tab label="Read" />
      </Tabs>

      <Card>
        <List disablePadding>
          {filtered.map((n, i) => (
            <Box key={n.id}>
              <ListItemButton
                sx={{ bgcolor: n.read ? 'transparent' : 'action.hover', py: 1.5 }}
                onClick={() => markRead(n.id)}
              >
                <ListItemIcon>{TYPE_ICONS[n.type]}</ListItemIcon>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle2" fontWeight={n.read ? 400 : 700}>{n.title}</Typography>
                      {!n.read && <Chip size="small" label="NEW" color="primary" sx={{ height: 18, fontSize: 10 }} />}
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.secondary">{n.body}</Typography>
                      <Typography variant="caption" color="text.disabled">{n.time}</Typography>
                    </>
                  }
                />
                {!n.read && (
                  <Tooltip title="Mark as read">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); markRead(n.id); }}>
                      <MarkEmailRead fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </ListItemButton>
              {i < filtered.length - 1 && <Divider />}
            </Box>
          ))}
          {filtered.length === 0 && (
            <Box py={6} textAlign="center">
              <Typography color="text.secondary">No notifications</Typography>
            </Box>
          )}
        </List>
      </Card>
    </Box>
  );
}
