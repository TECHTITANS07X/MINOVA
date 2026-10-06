import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, FormControl, InputLabel, Select, MenuItem,
  Chip, List, ListItemButton, ListItemText, Divider, CircularProgress,
} from '@mui/material';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from '@mui/icons-material';
import { useInsights, useMines } from '../api/hooks';

export default function Insights() {
  const [mine, setMine] = useState('');
  const { data: mines = [] } = useMines();
  const { data: insights, isLoading } = useInsights(mine || undefined);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Insights</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Mine</InputLabel>
          <Select value={mine} label="Mine" onChange={(e) => setMine(e.target.value)}>
            <MenuItem value="">All Mines</MenuItem>
            {mines.map((m) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Monthly Target vs Actual (tonnes)</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={insights?.monthly_data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(v) => Number(v).toLocaleString()} />
                  <Legend />
                  <Bar dataKey="target" fill="#1B5E20" opacity={0.3} name="Target" />
                  <Bar dataKey="actual" fill="#1B5E20" name="Actual" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Daily Production & OB Trend</Typography>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={insights?.daily_trend ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="production" stroke="#1B5E20" name="Production (t)" dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="ob" stroke="#E65100" name="OB (m³)" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Word Cloud</Typography>
              <Box display="flex" flexWrap="wrap" gap={0.5} justifyContent="center" py={2}>
                {(insights?.word_cloud ?? []).map((w: any) => (
                  <Typography key={w.text} sx={{ fontSize: w.size * 0.45, fontWeight: w.size > 30 ? 700 : 400, color: w.size > 35 ? 'primary.main' : 'text.secondary', cursor: 'pointer', '&:hover': { color: 'secondary.main' } }}>
                    {w.text}
                  </Typography>
                ))}
              </Box>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <TrendingUp sx={{ verticalAlign: 'middle', mr: 0.5 }} />Topics
              </Typography>
              <List disablePadding>
                {(insights?.topics ?? []).map((t: any, i: number) => (
                  <Box key={t.id}>
                    <ListItemButton sx={{ borderRadius: 1 }}>
                      <ListItemText
                        primary={t.label}
                        secondary={`${t.doc_count?.toLocaleString()} documents`}
                      />
                      <Chip size="small" label={`${(t.weight * 100).toFixed(0)}%`} variant="outlined" />
                    </ListItemButton>
                    {i < (insights?.topics ?? []).length - 1 && <Divider />}
                  </Box>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
