import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableRow,
} from '@mui/material';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

const MINE_ICON = new L.Icon({
  iconUrl: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="%231B5E20"><circle cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif">M</text></svg>'),
  iconSize: [24, 24],
  iconAnchor: [12, 24],
  popupAnchor: [0, -20],
});

interface MineLocation {
  id: string;
  name: string;
  lat: number;
  lng: number;
  status: 'active' | 'idle' | 'maintenance';
  todayProduction: number;
  targetProduction: number;
  benches: number;
}

const MINES: MineLocation[] = [
  { id: 'mine1', name: 'DEMO Mine Alpha', lat: 23.6345, lng: 85.3803, status: 'active', todayProduction: 8200, targetProduction: 8500, benches: 4 },
  { id: 'mine2', name: 'DEMO Mine Beta', lat: 23.7957, lng: 86.4304, status: 'active', todayProduction: 6100, targetProduction: 7000, benches: 3 },
  { id: 'mine3', name: 'DEMO Mine Gamma', lat: 22.0797, lng: 82.1409, status: 'maintenance', todayProduction: 0, targetProduction: 5000, benches: 2 },
];

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'error'> = {
  active: 'success', idle: 'warning', maintenance: 'error',
};

export default function MapView() {
  const [selectedMine, setSelectedMine] = useState<string>('');

  const center: [number, number] = [23.2, 84.0];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Mine Map</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter Mine</InputLabel>
          <Select value={selectedMine} label="Filter Mine" onChange={(e) => setSelectedMine(e.target.value)}>
            <MenuItem value="">All Mines</MenuItem>
            {MINES.map(m => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
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
              {MINES.filter(m => !selectedMine || m.id === selectedMine).map((mine) => (
                <Marker key={mine.id} position={[mine.lat, mine.lng]} icon={MINE_ICON}>
                  <Popup>
                    <Typography variant="subtitle2">{mine.name}</Typography>
                    <Typography variant="caption">
                      Status: <Chip size="small" label={mine.status} color={STATUS_COLORS[mine.status]} sx={{ height: 18 }} />
                    </Typography>
                    <br />
                    <Typography variant="caption">
                      Today: {mine.todayProduction.toLocaleString()} / {mine.targetProduction.toLocaleString()} t
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
              {MINES.filter(m => !selectedMine || m.id === selectedMine).map((mine) => {
                const pct = mine.targetProduction > 0 ? (mine.todayProduction / mine.targetProduction * 100) : 0;
                return (
                  <Card key={mine.id} variant="outlined" sx={{ mb: 2 }}>
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2">{mine.name}</Typography>
                        <Chip size="small" label={mine.status} color={STATUS_COLORS[mine.status]} />
                      </Box>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Production</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">
                              <strong>{mine.todayProduction.toLocaleString()} t</strong>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Target</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">{mine.targetProduction.toLocaleString()} t</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Achievement</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">
                              <Typography color={pct >= 95 ? 'success.main' : pct >= 80 ? 'warning.main' : 'error'} fontWeight={600}>
                                {pct.toFixed(1)}%
                              </Typography>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell sx={{ border: 0, py: 0.25, pl: 0 }}>Benches</TableCell>
                            <TableCell sx={{ border: 0, py: 0.25 }} align="right">{mine.benches}</TableCell>
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
