import { Box, Card, CardContent, Grid, Typography, Chip, Skeleton } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, TrendingDown, Warning, CheckCircle } from '@mui/icons-material';
import { useAuth } from '../auth/KeycloakProvider';

const MOCK_PRODUCTION = [
  { day: 'Mon', target: 8000, actual: 7500 },
  { day: 'Tue', target: 8000, actual: 8200 },
  { day: 'Wed', target: 8000, actual: 6800 },
  { day: 'Thu', target: 8000, actual: 7900 },
  { day: 'Fri', target: 8000, actual: 8100 },
  { day: 'Sat', target: 6000, actual: 5500 },
  { day: 'Sun', target: 4000, actual: 3200 },
];

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

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Welcome, {user?.name || 'User'}
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Production overview for DEMO Mine Alpha
      </Typography>

      <Grid container spacing={3} mb={3}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Today's Production" value="7,900" unit="tonnes" trend="up" color="primary.main" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Monthly Target" value="87.2" unit="%" trend="up" color="success.main" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Pending Approvals" value="12" unit="entries" color="warning.main" />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard title="Active Anomalies" value="3" unit="flags" trend="down" color="error.main" />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Weekly Production vs Target</Typography>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={MOCK_PRODUCTION}>
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
              {[
                { text: 'Shift 1 entry approved', icon: <CheckCircle color="success" fontSize="small" />, time: '10m ago' },
                { text: 'Anomaly flagged: low OB', icon: <Warning color="warning" fontSize="small" />, time: '1h ago' },
                { text: 'Daily report generated', icon: <CheckCircle color="info" fontSize="small" />, time: '2h ago' },
                { text: 'Conflict detected: 8000 vs 7850', icon: <Warning color="error" fontSize="small" />, time: '3h ago' },
              ].map((item, i) => (
                <Box key={i} display="flex" alignItems="center" gap={1} py={1} borderBottom={1} borderColor="divider">
                  {item.icon}
                  <Box flex={1}>
                    <Typography variant="body2">{item.text}</Typography>
                    <Typography variant="caption" color="text.secondary">{item.time}</Typography>
                  </Box>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
