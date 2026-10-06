import { useState, useCallback } from 'react';
import {
  Box, Card, Typography, TextField, Button, Grid, Chip, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, Tooltip, LinearProgress, Paper,
} from '@mui/material';
import { Search, Visibility, CloudUpload } from '@mui/icons-material';
import { useDocuments } from '../api/hooks';
import { api } from '../api/client';

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'info' | 'success' | 'error'> = {
  uploaded: 'default',
  processing: 'warning',
  ocr_complete: 'info',
  embedded: 'info',
  indexed: 'success',
  review_pending: 'warning',
  reviewed: 'success',
  failed: 'error',
};

export default function Documents() {
  const { data: documents = [] } = useDocuments();
  const [searchQuery, setSearchQuery] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) handleUpload(files);
  }, []);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        await api.post('/documents/upload/file', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } catch {
        // Error handled by interceptor
      }
    }
    setUploading(false);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      await api.get('/documents/search', { params: { q: searchQuery } });
    } catch {
      // handled
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Documents</Typography>

      <Paper
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        sx={{
          p: 4, mb: 3, textAlign: 'center', border: '2px dashed',
          borderColor: dragOver ? 'primary.main' : 'divider',
          bgcolor: dragOver ? 'action.hover' : 'background.paper',
          cursor: 'pointer', transition: 'all 0.2s',
        }}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input id="file-input" type="file" hidden multiple accept=".pdf,.xlsx,.csv,.doc,.docx,.ppt,.pptx,.png,.jpg,.jpeg"
          onChange={(e) => e.target.files && handleUpload(Array.from(e.target.files))} />
        <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
        <Typography variant="body1">Drag & drop files here or click to upload</Typography>
        <Typography variant="caption" color="text.secondary">
          PDF, Excel, CSV, Word, PowerPoint, Images (Hindi & English supported)
        </Typography>
        {uploading && <LinearProgress sx={{ mt: 2 }} />}
      </Paper>

      <Grid container spacing={2} mb={3}>
        <Grid size={{ xs: 12, sm: 9 }}>
          <TextField fullWidth size="small" placeholder="Search documents (keyword + semantic)..."
            value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            slotProps={{ input: { startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} /> } }} />
        </Grid>
        <Grid size={{ xs: 12, sm: 3 }}>
          <Button variant="contained" fullWidth onClick={handleSearch} startIcon={<Search />}>Search</Button>
        </Grid>
      </Grid>

      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Filename</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Uploaded</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {documents.map((doc) => (
              <TableRow key={doc.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight={500}>{doc.filename}</Typography>
                </TableCell>
                <TableCell><Chip size="small" label={doc.doc_type} variant="outlined" /></TableCell>
                <TableCell>{doc.category}</TableCell>
                <TableCell>
                  <Chip size="small" label={doc.ingestion_status}
                    color={STATUS_COLORS[doc.ingestion_status] || 'default'} />
                </TableCell>
                <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                <TableCell align="right">
                  <Tooltip title="View"><IconButton size="small"><Visibility /></IconButton></Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {documents.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary" py={4}>No documents uploaded yet</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Box>
  );
}
