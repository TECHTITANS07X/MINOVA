import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, Button, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, Tooltip, CircularProgress,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, FormControl,
  InputLabel, Select, MenuItem, LinearProgress, Alert,
} from '@mui/material';
import { CloudUpload, CheckCircle, Cancel, LocationOn, Photo } from '@mui/icons-material';
import { useMines, usePhotoVerifications, useUploadPhotoEvidence } from '../api/hooks';
import { api } from '../api/client';

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  pending: 'warning',
  verified: 'success',
  rejected: 'error',
  suspicious: 'error',
};

export default function PhotoVerification() {
  const { data: mines = [] } = useMines();
  const [mineFilter, setMineFilter] = useState('');
  const { data: verifications = [], isLoading, refetch } = usePhotoVerifications(mineFilter || undefined);
  const uploadMutation = useUploadPhotoEvidence();
  const [uploading, setUploading] = useState(false);
  const [uploadMine, setUploadMine] = useState('');
  const [uploadContext, setUploadContext] = useState('');
  const [verifyDialog, setVerifyDialog] = useState<any>(null);
  const [verifyNotes, setVerifyNotes] = useState('');

  const handleUpload = async (files: FileList | null) => {
    if (!files || !uploadMine) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('mine_id', uploadMine);
      formData.append('context', uploadContext);
      uploadMutation.mutate(formData);
    }
    setUploading(false);
    setUploadContext('');
  };

  const handleVerify = async (id: string, status: 'verified' | 'rejected') => {
    await api.post(`/photos/verifications/${id}/verify`, {
      status,
      notes: verifyNotes,
    });
    setVerifyDialog(null);
    setVerifyNotes('');
    refetch();
  };

  const summary = {
    total: verifications.length,
    verified: verifications.filter((v: any) => v.verification_status === 'verified').length,
    pending: verifications.filter((v: any) => v.verification_status === 'pending').length,
    suspicious: verifications.filter((v: any) => v.verification_status === 'suspicious' || v.verification_status === 'rejected').length,
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">
          <Photo sx={{ verticalAlign: 'middle', mr: 1 }} />
          Photo-Evidence Geo-Verification
        </Typography>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Mine</InputLabel>
          <Select value={mineFilter} label="Mine" onChange={(e) => setMineFilter(e.target.value)}>
            <MenuItem value="">All Mines</MenuItem>
            {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={2} mb={3}>
        {[
          { label: 'Total Photos', count: summary.total, color: 'primary.main' },
          { label: 'Verified', count: summary.verified, color: 'success.main' },
          { label: 'Pending', count: summary.pending, color: 'warning.main' },
          { label: 'Suspicious/Rejected', count: summary.suspicious, color: 'error.main' },
        ].map((s) => (
          <Grid size={{ xs: 6, md: 3 }} key={s.label}>
            <Card>
              <Box p={2} textAlign="center">
                <Typography variant="h4" fontWeight={700} color={s.color}>{s.count}</Typography>
                <Typography variant="body2" color="text.secondary">{s.label}</Typography>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Upload Photo Evidence</Typography>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 4 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Mine</InputLabel>
                <Select value={uploadMine} label="Mine" onChange={(e) => setUploadMine(e.target.value)}>
                  {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField fullWidth size="small" label="Context (e.g., Bench A1 progress)"
                value={uploadContext} onChange={(e) => setUploadContext(e.target.value)} />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Button variant="contained" fullWidth startIcon={<CloudUpload />} component="label"
                disabled={!uploadMine || uploading}>
                {uploading ? 'Uploading...' : 'Upload Photos'}
                <input type="file" hidden multiple accept="image/*"
                  onChange={(e) => handleUpload(e.target.files)} />
              </Button>
            </Grid>
          </Grid>
          {uploading && <LinearProgress sx={{ mt: 1 }} />}
          <Alert severity="info" sx={{ mt: 2 }}>
            Photos are checked for EXIF GPS data and compared against the mine's registered coordinates.
            Distance discrepancies are flagged for review.
          </Alert>
        </CardContent>
      </Card>

      {isLoading ? (
        <Box textAlign="center" py={4}><CircularProgress /></Box>
      ) : (
        <Card>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Filename</TableCell>
                <TableCell>Mine</TableCell>
                <TableCell>Context</TableCell>
                <TableCell>GPS Location</TableCell>
                <TableCell>Distance</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Uploaded</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {verifications.map((v: any) => {
                const hasGps = v.photo_latitude && v.photo_longitude;
                const distance = v.distance_m ? parseFloat(v.distance_m) : null;
                return (
                  <TableRow key={v.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>{v.filename}</Typography>
                    </TableCell>
                    <TableCell>{mines.find((m: any) => m.id === v.mine_id)?.name || v.mine_id?.slice(0, 8)}</TableCell>
                    <TableCell>{v.context || '—'}</TableCell>
                    <TableCell>
                      {hasGps ? (
                        <Tooltip title={`${v.photo_latitude}, ${v.photo_longitude}`}>
                          <Chip size="small" icon={<LocationOn />} label="GPS Found" color="success" variant="outlined" />
                        </Tooltip>
                      ) : (
                        <Chip size="small" label="No GPS" color="warning" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>
                      {distance !== null ? (
                        <Typography color={distance > 500 ? 'error' : distance > 100 ? 'warning.main' : 'success.main'} fontWeight={600}>
                          {distance > 1000 ? `${(distance / 1000).toFixed(1)} km` : `${distance.toFixed(0)} m`}
                        </Typography>
                      ) : '—'}
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={v.verification_status}
                        color={STATUS_COLORS[v.verification_status] || 'default'} />
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{new Date(v.created_at).toLocaleDateString()}</TableCell>
                    <TableCell align="right">
                      {v.verification_status === 'pending' && (
                        <>
                          <Tooltip title="Verify">
                            <IconButton size="small" color="success"
                              onClick={() => { setVerifyDialog(v); }}>
                              <CheckCircle fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Reject">
                            <IconButton size="small" color="error"
                              onClick={() => { setVerifyDialog({ ...v, _reject: true }); }}>
                              <Cancel fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
              {verifications.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary" py={4}>No photo evidence uploaded</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}

      <Dialog open={!!verifyDialog} onClose={() => setVerifyDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {verifyDialog?._reject ? 'Reject' : 'Verify'} Photo Evidence
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" mb={2}>
            {verifyDialog?.filename}
            {verifyDialog?.distance_m && ` — Distance: ${parseFloat(verifyDialog.distance_m).toFixed(0)}m from expected location`}
          </Typography>
          <TextField fullWidth multiline rows={2} label="Verification Notes" value={verifyNotes}
            onChange={(e) => setVerifyNotes(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVerifyDialog(null)}>Cancel</Button>
          <Button variant="contained"
            color={verifyDialog?._reject ? 'error' : 'success'}
            onClick={() => handleVerify(verifyDialog?.id, verifyDialog?._reject ? 'rejected' : 'verified')}>
            {verifyDialog?._reject ? 'Reject' : 'Verify'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
