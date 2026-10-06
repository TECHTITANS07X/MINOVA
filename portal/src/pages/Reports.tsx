import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, Button, Select, MenuItem,
  FormControl, InputLabel, Grid, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions,
  Menu, ListItemIcon, ListItemText, TextField, CircularProgress, Alert, Divider,
} from '@mui/material';
import { Download, Visibility, PictureAsPdf, TableChart, Article, AutoAwesome, CloudUpload, TravelExplore } from '@mui/icons-material';
import { useReports, useMines, useGenerateReport } from '../api/hooks';
import { api } from '../api/client';
import type { Report } from '../types';

interface ExtractedFigure {
  metric: string;
  value: number;
  unit: string;
  source_page: number;
  source_snippet: string;
}

interface DocumentReportResult {
  document_id: string;
  document_filename: string;
  pages_parsed: number;
  extracted: ExtractedFigure[];
  report_id: string;
  report_status: string;
  period_start: string;
  period_end: string;
  report_values: { id: string; metric: string; value: number; unit: string; section: string; row_key: string }[];
  primary_value_id: string | null;
}

const PERIOD_COLORS: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'info' | 'warning'> = {
  daily: 'primary',
  weekly: 'info',
  monthly: 'secondary',
  quarterly: 'warning',
  annual: 'success',
};

export default function Reports() {
  const navigate = useNavigate();
  const [mineFilter, setMineFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');
  const { data: reports = [], refetch: refetchReports } = useReports(mineFilter || undefined);
  const { data: mines = [] } = useMines();
  const generateReport = useGenerateReport();
  const [previewReport, setPreviewReport] = useState<Report | null>(null);
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);
  const [exportReportId, setExportReportId] = useState<string>('');
  const [genDialog, setGenDialog] = useState(false);
  const [genMineId, setGenMineId] = useState('');
  const [genPeriod, setGenPeriod] = useState('daily');
  const [genStart, setGenStart] = useState('');
  const [genEnd, setGenEnd] = useState('');

  // ── Document-to-report pipeline: upload → extract → finalized report ──
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentMine, setDocumentMine] = useState('');
  const [documentRunning, setDocumentRunning] = useState(false);
  const [documentResult, setDocumentResult] = useState<DocumentReportResult | null>(null);
  const [documentError, setDocumentError] = useState('');

  const runDocumentPipeline = async () => {
    if (!documentFile || !documentMine) return;
    setDocumentRunning(true);
    setDocumentError('');
    setDocumentResult(null);
    try {
      const fd = new FormData();
      fd.append('file', documentFile);
      fd.append('mine_id', documentMine);
      const res = await api.post('/reports/generate-from-document', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setDocumentResult(res.data);
      refetchReports();
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      const msg = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: any) => `${(x.loc || []).join('.')}: ${x.msg}`).join('; ') : d ? JSON.stringify(d) : 'Could not process the document. Please try again.';
      setDocumentError(msg);
    }
    setDocumentRunning(false);
  };

  const previewDocumentReport = (r: DocumentReportResult): Report => ({
    id: r.report_id,
    mine_id: '',
    template_id: '',
    period: 'monthly',
    period_start: r.period_start,
    period_end: r.period_end,
    status: r.report_status as Report['status'],
    generated_description: `AI-extracted from "${r.document_filename}" (${r.pages_parsed} page${r.pages_parsed === 1 ? '' : 's'} parsed). Every figure is traceable to the source document page via Replay the Number.`,
    edited_description: null,
    created_at: new Date().toISOString(),
    finalized_at: new Date().toISOString(),
    values: r.report_values.map(v => ({ id: v.id, metric: v.metric, value: Number(v.value), unit: v.unit, section: v.section, row_key: v.row_key })),
  } as unknown as Report);

  const handleExport = (format: string) => {
    window.open(`${api.defaults.baseURL}/reports/${exportReportId}/export?format=${format}`, '_blank');
    setExportAnchor(null);
  };

  const handleGenerate = () => {
    if (!genMineId || !genStart || !genEnd) return;
    generateReport.mutate(
      { mine_id: genMineId, period: genPeriod, period_start: genStart, period_end: genEnd },
      {
        onSuccess: () => {
          setGenDialog(false);
          setGenMineId('');
          setGenPeriod('daily');
          setGenStart('');
          setGenEnd('');
        },
      }
    );
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
              {mines.map((m: any) => (
                <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
              ))}
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
          <Button variant="contained" fullWidth onClick={() => setGenDialog(true)}>Generate Report</Button>
        </Grid>
      </Grid>

      {/* ── Document-to-report pipeline: upload → extract → finalized report ── */}
      <Card sx={{ mb: 3, border: '1px solid', borderColor: 'primary.light' }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={1}>
            <AutoAwesome color="primary" />
            <Typography variant="h6">Generate Report from Document</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Upload a mine document — the AI reads it, extracts the key figures, and generates a
            finalized, compliant report. Every number is traceable back to the exact document page
            via <strong>Replay the Number</strong>.
          </Typography>
          <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
            <Button
              variant="outlined"
              component="label"
              startIcon={<CloudUpload />}
            >
              {documentFile ? documentFile.name : 'Choose PDF document'}
              <input
                type="file"
                accept="application/pdf"
                hidden
                onChange={(e) => { setDocumentFile(e.target.files?.[0] || null); setDocumentResult(null); setDocumentError(''); }}
              />
            </Button>
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel>Mine</InputLabel>
              <Select value={documentMine} label="Mine" onChange={(e) => setDocumentMine(e.target.value)}>
                {mines.map((m: any) => (
                  <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="contained"
              color="secondary"
              startIcon={documentRunning ? <CircularProgress size={18} color="inherit" /> : <AutoAwesome />}
              disabled={!documentFile || !documentMine || documentRunning}
              onClick={runDocumentPipeline}
            >
              {documentRunning ? 'Extracting figures…' : 'Generate Report'}
            </Button>
          </Box>

          {documentError && <Alert severity="error" sx={{ mt: 2 }}>{documentError}</Alert>}

          {documentResult && (
            <Box mt={2}>
              <Divider sx={{ mb: 2 }} />
              <Alert severity="success" sx={{ mb: 2 }}>
                <Typography fontWeight={700}>
                  Report generated from “{documentResult.document_filename}” — status: {documentResult.report_status.toUpperCase()}
                </Typography>
              </Alert>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Extracted figure</TableCell>
                    <TableCell align="right">Value</TableCell>
                    <TableCell>Source (document)</TableCell>
                    <TableCell align="right">Trace</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {documentResult.extracted.map((x, i) => (
                    <TableRow key={i}>
                      <TableCell>{x.metric}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>{x.value.toLocaleString()} {x.unit}</TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          p.{x.source_page}: “{x.source_snippet}”
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {documentResult.report_values[i] && (
                          <Tooltip title="Replay the Number — trace to source">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => navigate(`/replay?valueId=${documentResult.report_values[i].id}`)}
                            >
                              <TravelExplore />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Box display="flex" gap={1} mt={2}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Visibility />}
                  onClick={() => setPreviewReport(previewDocumentReport(documentResult))}
                >
                  Open finalized report
                </Button>
                {documentResult.primary_value_id && (
                  <Button
                    variant="contained"
                    size="small"
                    color="success"
                    startIcon={<TravelExplore />}
                    onClick={() => navigate(`/replay?valueId=${documentResult.primary_value_id}`)}
                  >
                    Replay the Number
                  </Button>
                )}
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

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

      <Dialog open={genDialog} onClose={() => setGenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Generate Report</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} mt={0.5}>
            <Grid size={{ xs: 12 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Mine</InputLabel>
                <Select value={genMineId} label="Mine" onChange={(e) => setGenMineId(e.target.value)}>
                  {mines.map((m: any) => (
                    <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Period</InputLabel>
                <Select value={genPeriod} label="Period" onChange={(e) => setGenPeriod(e.target.value)}>
                  <MenuItem value="daily">Daily</MenuItem>
                  <MenuItem value="weekly">Weekly</MenuItem>
                  <MenuItem value="monthly">Monthly</MenuItem>
                  <MenuItem value="quarterly">Quarterly</MenuItem>
                  <MenuItem value="annual">Annual</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField fullWidth size="small" label="Start Date" type="date" value={genStart}
                onChange={(e) => setGenStart(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField fullWidth size="small" label="End Date" type="date" value={genEnd}
                onChange={(e) => setGenEnd(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGenDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleGenerate}
            disabled={!genMineId || !genStart || !genEnd || generateReport.isPending}>
            {generateReport.isPending ? <CircularProgress size={20} /> : 'Generate'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
