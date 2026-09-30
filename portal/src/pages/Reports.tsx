import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button, Select, MenuItem,
  FormControl, InputLabel, Grid, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions,
  Menu, ListItemIcon, ListItemText,
} from '@mui/material';
import { Download, Visibility, PictureAsPdf, TableChart, Article } from '@mui/icons-material';
import { useReports } from '../api/hooks';
import { api } from '../api/client';
import type { Report } from '../types';

const PERIOD_COLORS: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'info' | 'warning'> = {
  daily: 'primary',
  weekly: 'info',
  monthly: 'secondary',
  quarterly: 'warning',
  annual: 'success',
};

export default function Reports() {
  const [mineFilter, setMineFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');
  const { data: reports = [] } = useReports(mineFilter || undefined);
  const [previewReport, setPreviewReport] = useState<Report | null>(null);
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);
  const [exportReportId, setExportReportId] = useState<string>('');

  const handleExport = (format: string) => {
    window.open(`${api.defaults.baseURL}/reports/export/${exportReportId}?format=${format}`, '_blank');
    setExportAnchor(null);
  };

  const filtered = reports.filter((r) => {
    if (periodFilter && r.period !== periodFilter) return false;
    return true;
  });

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Reports</Typography>

      <Grid container spacing={2} mb={3}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Mine</InputLabel>
            <Select value={mineFilter} label="Mine" onChange={(e) => setMineFilter(e.target.value)}>
              <MenuItem value="">All Mines</MenuItem>
              <MenuItem value="mine1">DEMO Mine Alpha</MenuItem>
              <MenuItem value="mine2">DEMO Mine Beta</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Period</InputLabel>
            <Select value={periodFilter} label="Period" onChange={(e) => setPeriodFilter(e.target.value)}>
              <MenuItem value="">All Periods</MenuItem>
              <MenuItem value="daily">Daily</MenuItem>
              <MenuItem value="weekly">Weekly</MenuItem>
              <MenuItem value="monthly">Monthly</MenuItem>
              <MenuItem value="quarterly">Quarterly</MenuItem>
              <MenuItem value="annual">Annual</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Button variant="contained" fullWidth>Generate Report</Button>
        </Grid>
      </Grid>

      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Period</TableCell>
              <TableCell>Date Range</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Generated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((r) => (
              <TableRow key={r.id} hover>
                <TableCell>
                  <Chip size="small" label={r.period} color={PERIOD_COLORS[r.period] || 'default'} />
                </TableCell>
                <TableCell>
                  {new Date(r.period_start).toLocaleDateString()} — {new Date(r.period_end).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Chip size="small" label={r.status} variant="outlined"
                    color={r.status === 'approved' ? 'success' : r.status === 'draft' ? 'default' : 'warning'} />
                </TableCell>
                <TableCell>{new Date(r.created_at).toLocaleString()}</TableCell>
                <TableCell align="right">
                  <Tooltip title="Preview">
                    <IconButton size="small" onClick={() => setPreviewReport(r)}><Visibility /></IconButton>
                  </Tooltip>
                  <Tooltip title="Export">
                    <IconButton size="small" onClick={(e) => { setExportReportId(r.id); setExportAnchor(e.currentTarget); }}>
                      <Download />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary" py={4}>No reports found</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Menu anchorEl={exportAnchor} open={!!exportAnchor} onClose={() => setExportAnchor(null)}>
        <MenuItem onClick={() => handleExport('xlsx')}>
          <ListItemIcon><TableChart fontSize="small" /></ListItemIcon>
          <ListItemText>Excel (.xlsx)</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('pdf')}>
          <ListItemIcon><PictureAsPdf fontSize="small" /></ListItemIcon>
          <ListItemText>PDF</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('docx')}>
          <ListItemIcon><Article fontSize="small" /></ListItemIcon>
          <ListItemText>Word (.docx)</ListItemText>
        </MenuItem>
      </Menu>

      <Dialog open={!!previewReport} onClose={() => setPreviewReport(null)} maxWidth="md" fullWidth>
        <DialogTitle>Report Preview — {previewReport?.period}</DialogTitle>
        <DialogContent>
          {previewReport && (
            <Box>
              <Typography variant="body2" color="text.secondary" mb={2}>
                {new Date(previewReport.period_start).toLocaleDateString()} — {new Date(previewReport.period_end).toLocaleDateString()}
              </Typography>
              <Typography variant="subtitle2" gutterBottom>Description</Typography>
              <Typography variant="body2" mb={2}>{previewReport.generated_description || 'No description generated yet.'}</Typography>
              <Typography variant="subtitle2" gutterBottom>Values</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Section</TableCell>
                    <TableCell>Metric</TableCell>
                    <TableCell align="right">Value</TableCell>
                    <TableCell>Unit</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {previewReport.values?.map((v, i) => (
                    <TableRow key={i}>
                      <TableCell>{v.section}</TableCell>
                      <TableCell>{v.metric}</TableCell>
                      <TableCell align="right">{v.value.toLocaleString()}</TableCell>
                      <TableCell>{v.unit}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewReport(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
