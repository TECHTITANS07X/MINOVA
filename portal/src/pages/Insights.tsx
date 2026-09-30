import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, FormControl, InputLabel, Select, MenuItem,
  Chip, List, ListItemButton, ListItemText, Divider,
} from '@mui/material';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from '@mui/icons-material';

const MONTHLY_DATA = [
  { month: 'Apr', target: 250000, actual: 238000 },
  { month: 'May', target: 260000, actual: 272000 },
  { month: 'Jun', target: 240000, actual: 210000 },
  { month: 'Jul', target: 220000, actual: 195000 },
  { month: 'Aug', target: 250000, actual: 248000 },
  { month: 'Sep', target: 260000, actual: 225000 },
];

const DAILY_TREND = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  production: 7000 + Math.random() * 3000 - (i > 15 && i < 22 ? 2000 : 0),
  ob: 28000 + Math.random() * 8000,
}));

const TOPICS = [
  { label: 'Equipment Breakdown', docs: 42, weight: 0.85 },
  { label: 'Monsoon Disruption', docs: 28, weight: 0.72 },
  { label: 'Geological Survey Results', docs: 19, weight: 0.65 },
  { label: 'Safety Incidents', docs: 15, weight: 0.58 },
  { label: 'Blasting Operations', docs: 12, weight: 0.51 },
  { label: 'Dispatch Logistics', docs: 11, weight: 0.47 },
  { label: 'Labour & Manpower', docs: 9, weight: 0.41 },
  { label: 'Environmental Compliance', docs: 7, weight: 0.35 },
];

const WORD_CLOUD_WORDS = [
  { text: 'production', size: 48 }, { text: 'overburden', size: 40 }, { text: 'equipment', size: 36 },
  { text: 'rainfall', size: 34 }, { text: 'breakdown', size: 32 }, { text: 'dispatch', size: 30 },
  { text: 'shovel', size: 28 }, { text: 'dumper', size: 26 }, { text: 'target', size: 38 },
  { text: 'safety', size: 24 }, { text: 'blasting', size: 22 }, { text: 'coal', size: 42 },
  { text: 'stripping', size: 20 }, { text: 'geology', size: 18 }, { text: 'monsoon', size: 35 },
];

export default function Insights() {
  const [mine, setMine] = useState('all');

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Insights</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Mine</InputLabel>
          <Select value={mine} label="Mine" onChange={(e) => setMine(e.target.value)}>
            <MenuItem value="all">All Mines</MenuItem>
            <MenuItem value="mine1">DEMO Mine Alpha</MenuItem>
            <MenuItem value="mine2">DEMO Mine Beta</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Monthly Target vs Actual (tonnes)</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={MONTHLY_DATA}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(v: number) => v.toLocaleString()} />
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
                <LineChart data={DAILY_TREND}>
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
                {WORD_CLOUD_WORDS.map((w) => (
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
                {TOPICS.map((t, i) => (
                  <Box key={t.label}>
                    <ListItemButton sx={{ borderRadius: 1 }}>
                      <ListItemText
                        primary={t.label}
                        secondary={`${t.docs} documents`}
                      />
                      <Chip size="small" label={`${(t.weight * 100).toFixed(0)}%`} variant="outlined" />
                    </ListItemButton>
                    {i < TOPICS.length - 1 && <Divider />}
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
