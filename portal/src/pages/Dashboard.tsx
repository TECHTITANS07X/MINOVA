import { useState } from 'react';
import {
  Box, Card, CardContent, Grid, Typography, CircularProgress,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, TrendingDown, Warning, CheckCircle } from '@mui/icons-material';
import { useAuth } from '../auth/KeycloakProvider';
import { useDashboard, useMines } from '../api/hooks';

function StatCard({ title, value, unit, trend, color }: {
  title: string; value: string; unit: string; trend?: 'up' | 'down'; color: string;
}) {
  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>{title}</Typography>
        <Box display="flex" alignItems="baseline" gap={0.5}>
          <Typography variant="h4" fontWeight={700} color={color}>{value}</Typography>
          <Typography variant="body2" color="text.secondary">{unit}</Typography>
        </Box>
        {trend && (
          <Box display="flex" alignItems="center" mt={1}>
            {trend === 'up' ? <TrendingUp color="success" fontSize="small" /> : <TrendingDown color="error" fontSize="small" />}
            <Typography variant="caption" color={trend === 'up' ? 'success.main' : 'error.main'} ml={0.5}>
              {trend === 'up' ? '+5.2%' : '-3.1%'} vs last week
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [selectedMine, setSelectedMine] = useState<string>('');
  const { data: mines = [] } = useMines();
  const { data: dashboard, isLoading } = useDashboard(selectedMine || undefined);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  const mineName = mines.find(m => m.id === selectedMine)?.name || 'All Mines';

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="h5">
          Welcome, {user?.name || 'User'}
        </Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Mine</InputLabel>
          <Select value={selectedMine} label="Mine" onChange={(e) => setSelectedMine(e.target.value)}>
            <MenuItem value="">All Mines</MenuItem>
            {mines.map((m) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Production overview for {mineName}
      </Typography>

      <Grid container spacing={3} mb={3}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Today's Production" value={dashboard?.today_production?.toLocaleString() ?? '—'} unit="tonnes" trend="up" color="primary.main" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Target Achievement" value={dashboard?.target_achievement_pct?.toFixed(1) ?? '—'} unit="%" trend="up" color="success.main" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Pending Approvals" value={dashboard?.pending_approvals?.toLocaleString() ?? '—'} unit="entries" color="warning.main" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Active Anomalies" value={dashboard?.active_anomalies?.toLocaleString() ?? '—'} unit="flags" trend="down" color="error.main" />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Weekly Production vs Target</Typography>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={dashboard?.weekly_production ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="target" fill="#1B5E20" opacity={0.3} name="Target (t)" />
                  <Bar dataKey="actual" fill="#1B5E20" name="Actual (t)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recent Activity</Typography>
              {(dashboard?.recent_activity ?? []).map((item: any) => (
                <Box key={item.id} display="flex" alignItems="center" gap={1} py={1} borderBottom={1} borderColor="divider">
                  {item.action === 'approve' ? <CheckCircle color="success" fontSize="small" /> : <Warning color="warning" fontSize="small" />}
                  <Box flex={1}>
                    <Typography variant="body2">
                      {item.action.charAt(0).toUpperCase() + item.action.slice(1)}: {item.entity_type}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">{formatTime(item.time)}</Typography>
                  </Box>
                </Box>
              ))}
              {(dashboard?.recent_activity ?? []).length === 0 && (
                <Typography variant="body2" color="text.secondary">No recent activity</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
