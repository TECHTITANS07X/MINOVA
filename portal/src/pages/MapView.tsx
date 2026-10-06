import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableRow, CircularProgress,
} from '@mui/material';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useMines } from '../api/hooks';

const MINE_ICON = new L.Icon({
  iconUrl: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="%231B5E20"><circle cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif">M</text></svg>'),
  iconSize: [24, 24],
  iconAnchor: [12, 24],
  popupAnchor: [0, -20],
});

const STATUS_COLORS: Record<string, 'success' | 'error'> = {
  active: 'success', inactive: 'error',
};

export default function MapView() {
  const [selectedMine, setSelectedMine] = useState<string>('');
  const { data: mines = [], isLoading } = useMines();

  const mappableMines = mines.filter(m => m.latitude != null && m.longitude != null);
  const filteredMines = selectedMine ? mappableMines.filter(m => m.id === selectedMine) : mappableMines;
  const filteredAll = selectedMine ? mines.filter(m => m.id === selectedMine) : mines;

  const firstMine = mappableMines[0];
  const center: [number, number] = firstMine ? [firstMine.latitude!, firstMine.longitude!] : [23.2, 84.0];

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
        <Typography variant="h5">Mine Map</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter Mine</InputLabel>
          <Select value={selectedMine} label="Filter Mine" onChange={(e) => setSelectedMine(e.target.value)}>
            <MenuItem value="">All Mines</MenuItem>
            {mines.map(m => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ height: 500 }}>
            <MapContainer center={center} zoom={7} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {filteredMines.map((mine) => (
                <Marker key={mine.id} position={[mine.latitude!, mine.longitude!]} icon={MINE_ICON}>
                  <Popup>
                    <Typography variant="subtitle2">{mine.name}</Typography>
                    <Typography variant="caption">
                      Status: <Chip size="small" label={mine.is_active ? 'active' : 'inactive'} color={STATUS_COLORS[mine.is_active ? 'active' : 'inactive']} sx={{ height: 18 }} />
                    </Typography>
                    <br />
                    <Typography variant="caption">
                      Code: {mine.code} | Shifts: {mine.shift_count}
                    </Typography>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Mine Summary</Typography>
              {filteredAll.map((mine) => {
                const status = mine.is_active ? 'active' : 'inactive';
                return (
                  <Card key={mine.id} variant="outlined" sx={{ mb: 2 }}>
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2">{mine.name}</Typography>
                        <Chip size="small" label={status} color={STATUS_COLORS[status]} />
                      </Box>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Code</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">
                              <strong>{mine.code}</strong>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Shifts</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">{mine.shift_count}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Timezone</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">{mine.timezone}</TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                );
              })}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
