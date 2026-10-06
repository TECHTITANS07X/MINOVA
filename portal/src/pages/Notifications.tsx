import { useState } from 'react';
import {
  Box, Typography, Card, List, ListItemButton, ListItemIcon, ListItemText, Chip,
  IconButton, Tooltip, Divider, Tabs, Tab, Button, CircularProgress,
} from '@mui/material';
import {
  Approval, Warning, Description, Calculate, Gavel, NotificationsActive,
  DoneAll, MarkEmailRead,
} from '@mui/icons-material';
import { useNotifications } from '../api/hooks';

const TYPE_ICONS: Record<string, React.ReactElement> = {
  approval: <Approval color="success" />,
  anomaly: <Warning color="error" />,
  conflict: <Gavel color="warning" />,
  report: <Description color="info" />,
  calculation: <Calculate />,
  system: <NotificationsActive color="secondary" />,
};

const SEVERITY_COLORS: Record<string, 'error' | 'warning' | 'info'> = {
  high: 'error',
  medium: 'warning',
  low: 'info',
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs > 1 ? 's' : ''} ago`;
  const days = Math.floor(hrs / 24);
  return `${days} day${days > 1 ? 's' : ''} ago`;
}

export default function Notifications() {
  const { data: notifications = [], isLoading } = useNotifications();
  const [readIds, setReadIds] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState(0);

  const withReadState = notifications.map((n: any) => ({
    ...n,
    read: n.read || readIds.has(n.id),
  }));

  const unread = withReadState.filter((n: any) => !n.read);
  const filtered = tab === 0 ? withReadState : tab === 1 ? unread : withReadState.filter((n: any) => n.read);

  const markAllRead = () => {
    setReadIds(new Set(notifications.map((n: any) => n.id)));
  };

  const markRead = (id: string) => {
    setReadIds(prev => new Set(prev).add(id));
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" py={6}>
        <CircularProgress />
      </Box>
    );
  }

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
        <Tab label={`All (${withReadState.length})`} />
        <Tab label={`Unread (${unread.length})`} />
        <Tab label="Read" />
      </Tabs>

      <Card>
        <List disablePadding>
          {filtered.map((n: any, i: number) => (
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
                      {n.severity && (
                        <Chip size="small" label={n.severity} color={SEVERITY_COLORS[n.severity] || 'info'} sx={{ height: 18, fontSize: 10 }} />
                      )}
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.secondary">{n.body}</Typography>
                      <Typography variant="caption" color="text.disabled">
                        {new Date(n.time).toLocaleString()} ({relativeTime(n.time)})
                      </Typography>
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
