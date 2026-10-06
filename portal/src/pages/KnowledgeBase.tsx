import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Chip, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, FormControl, InputLabel, Select, MenuItem,
  IconButton, Tooltip, CircularProgress, Divider,
} from '@mui/material';
import { Add, Verified, Person, Search } from '@mui/icons-material';
import { useMines, useKnowledgeEntries, useCreateKnowledgeEntry } from '../api/hooks';
import { api } from '../api/client';

const CATEGORY_COLORS: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'> = {
  geological: 'primary',
  operational: 'secondary',
  safety: 'error',
  equipment: 'warning',
  environmental: 'success',
  regulatory: 'info',
};

export default function KnowledgeBase() {
  const { data: mines = [] } = useMines();
  const [mineFilter, setMineFilter] = useState('');
  const { data: entries = [], isLoading, refetch } = useKnowledgeEntries(mineFilter || undefined);
  const createEntry = useCreateKnowledgeEntry();
  const [dialog, setDialog] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [form, setForm] = useState({
    mine_id: '', category: 'operational', title: '', content: '',
    author_name: '', author_designation: '', years_experience: 0, tags: '',
  });

  const handleCreate = () => {
    if (!form.title || !form.content || !form.author_name) return;
    createEntry.mutate({
      ...form,
      mine_id: form.mine_id || null,
      tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
    }, {
      onSuccess: () => {
        setDialog(false);
        setForm({ mine_id: '', category: 'operational', title: '', content: '', author_name: '', author_designation: '', years_experience: 0, tags: '' });
      },
    });
  };

  const handleVerify = async (id: string) => {
    await api.post(`/knowledge/entries/${id}/verify`);
    refetch();
  };

  const filtered = entries.filter((e: any) =>
    !searchTerm || e.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.content?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Institutional Knowledge Base</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setDialog(true)}>Add Knowledge</Button>
      </Box>

      <Grid container spacing={2} mb={3}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Mine</InputLabel>
            <Select value={mineFilter} label="Mine" onChange={(e) => setMineFilter(e.target.value)}>
              <MenuItem value="">All Mines</MenuItem>
              {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
            </Select>
          </FormControl>
        </Grid>
        <Grid size={{ xs: 12, sm: 8 }}>
          <TextField fullWidth size="small" placeholder="Search knowledge base..."
            value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            slotProps={{ input: { startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} /> } }} />
        </Grid>
      </Grid>

      {isLoading ? (
        <Box textAlign="center" py={4}><CircularProgress /></Box>
      ) : (
        <Grid container spacing={2}>
          {filtered.map((entry: any) => (
            <Grid size={{ xs: 12, md: 6 }} key={entry.id}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600}>{entry.title}</Typography>
                      <Chip size="small" label={entry.category}
                        color={CATEGORY_COLORS[entry.category] || 'default'} sx={{ mt: 0.5 }} />
                    </Box>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      {entry.is_verified ? (
                        <Chip size="small" icon={<Verified />} label="Verified" color="success" variant="outlined" />
                      ) : (
                        <Tooltip title="Mark as Verified">
                          <IconButton size="small" color="success" onClick={() => handleVerify(entry.id)}>
                            <Verified />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxHeight: 80, overflow: 'hidden' }}>
                    {entry.content}
                  </Typography>

                  <Divider sx={{ my: 1 }} />

                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <Person fontSize="small" color="action" />
                      <Typography variant="caption">
                        {entry.author_name}{entry.author_designation ? ` — ${entry.author_designation}` : ''}
                        {entry.years_experience > 0 ? ` (${entry.years_experience}y exp)` : ''}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(entry.created_at).toLocaleDateString()}
                    </Typography>
                  </Box>

                  {entry.tags?.length > 0 && (
                    <Box display="flex" gap={0.5} mt={1} flexWrap="wrap">
                      {entry.tags.map((tag: string) => (
                        <Chip key={tag} size="small" label={tag} variant="outlined" sx={{ height: 20, fontSize: 11 }} />
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
          {filtered.length === 0 && (
            <Grid size={{ xs: 12 }}>
              <Box textAlign="center" py={6}>
                <Typography color="text.secondary">No knowledge entries found</Typography>
              </Box>
            </Grid>
          )}
        </Grid>
      )}

      <Dialog open={dialog} onClose={() => setDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add Knowledge Entry</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} mt={0.5}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <FormControl fullWidth>
                <InputLabel>Mine</InputLabel>
                <Select value={form.mine_id} label="Mine" onChange={(e) => setForm(f => ({ ...f, mine_id: e.target.value }))}>
                  <MenuItem value="">Global (All Mines)</MenuItem>
                  {mines.map((m: any) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select value={form.category} label="Category" onChange={(e) => setForm(f => ({ ...f, category: e.target.value }))}>
                  {['geological', 'operational', 'safety', 'equipment', 'environmental', 'regulatory'].map(c => (
                    <MenuItem key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField fullWidth label="Tags (comma-separated)" value={form.tags}
                onChange={(e) => setForm(f => ({ ...f, tags: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth label="Title" value={form.title}
                onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth multiline rows={4} label="Knowledge Content"
                value={form.content} onChange={(e) => setForm(f => ({ ...f, content: e.target.value }))}
                helperText="Document insights, best practices, or lessons learned" />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField fullWidth label="Author Name" value={form.author_name}
                onChange={(e) => setForm(f => ({ ...f, author_name: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField fullWidth label="Designation" value={form.author_designation}
                onChange={(e) => setForm(f => ({ ...f, author_designation: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField fullWidth type="number" label="Years Experience" value={form.years_experience}
                onChange={(e) => setForm(f => ({ ...f, years_experience: parseInt(e.target.value) || 0 }))} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={createEntry.isPending || !form.title || !form.content}>
            {createEntry.isPending ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
