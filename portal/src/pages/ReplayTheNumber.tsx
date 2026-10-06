import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, TextField, Button, Chip, Collapse,
  List, ListItemButton, ListItemText, ListItemIcon, Alert, CircularProgress,
} from '@mui/material';
import { ExpandMore, ExpandLess, Verified, Error, Description, CalendarMonth, Person, PictureAsPdf } from '@mui/icons-material';
import { api } from '../api/client';
import type { LineageNode } from '../types';

function LineageTreeNode({ node, depth = 0 }: { node: LineageNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);

  return (
    <Box ml={depth * 2}>
      <ListItemButton onClick={() => setOpen(!open)} sx={{ borderRadius: 1, mb: 0.5 }}>
        <ListItemIcon sx={{ minWidth: 36 }}>
          {node.source_type === 'report' || node.source_type === 'report_value' ? <Description color="primary" /> :
           node.source_type === 'shift_entry' ? <Person color="secondary" /> :
           node.source_type === 'document' || node.source_type === 'document_page' ? <PictureAsPdf color="warning" /> :
           <CalendarMonth color="action" />}
        </ListItemIcon>
        <ListItemText
          primary={
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="body2" fontWeight={600}>{node.label}</Typography>
              {node.value !== null && node.value !== undefined && (
                <Chip size="small" label={`${node.value.toLocaleString()}${node.unit ? ' ' + node.unit : ''}`} variant="outlined" />
              )}
            </Box>
          }
          secondary={node.timestamp ? new Date(node.timestamp).toLocaleString() : undefined}
        />
        {node.children.length > 0 && (open ? <ExpandLess /> : <ExpandMore />)}
      </ListItemButton>
      <Collapse in={open}>
        {node.children.map((child, i) => (
          <LineageTreeNode key={`${child.source_id}-${i}`} node={child} depth={depth + 1} />
        ))}
      </Collapse>
    </Box>
  );
}

export default function ReplayTheNumber() {
  const [searchParams] = useSearchParams();
  const [valueId, setValueId] = useState(searchParams.get('valueId') || '');
  const [lineage, setLineage] = useState<LineageNode | null>(null);
  const [verifyResult, setVerifyResult] = useState<'MATCH' | 'MISMATCH' | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLookup = async (id?: string) => {
    const target = (id ?? valueId).trim();
    if (!target) return;
    setLoading(true);
    setVerifyResult(null);
    try {
      const res = await api.get(`/lineage/${target}`);
      setLineage(res.data);
    } catch {
      setLineage(null);
    }
    setLoading(false);
  };

  // Deep link from Reports (document-to-report pipeline): /replay?valueId=...
  useEffect(() => {
    const fromUrl = searchParams.get('valueId');
    if (fromUrl) handleLookup(fromUrl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleVerify = async () => {
    if (!valueId.trim()) return;
    setLoading(true);
    try {
      const res = await api.post(`/lineage/${valueId}/verify`);
      setVerifyResult(res.data.match ? 'MATCH' : 'MISMATCH');
    } catch {
      setVerifyResult(null);
    }
    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Replay the Number</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Trace any report value back to its source data. Every number has a lineage.
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" gap={2} alignItems="flex-start">
            <TextField label="Report Value ID" value={valueId} onChange={(e) => setValueId(e.target.value)}
              placeholder="Enter or click a value ID from any report" fullWidth size="small" />
            <Button variant="contained" onClick={() => handleLookup()} disabled={loading}>
              Trace
            </Button>
            <Button variant="outlined" color="success" onClick={handleVerify} disabled={loading || !lineage}>
              {loading ? <CircularProgress size={20} /> : <Verified sx={{ mr: 0.5 }} />}
              Verify
            </Button>
          </Box>

          {verifyResult && (
            <Alert severity={verifyResult === 'MATCH' ? 'success' : 'error'} sx={{ mt: 2 }} icon={verifyResult === 'MATCH' ? <Verified /> : <Error />}>
              <Typography fontWeight={700}>
                {verifyResult === 'MATCH'
                  ? 'MATCH — Recomputed value matches the stored value exactly.'
                  : 'MISMATCH — Recomputed value differs from the stored value. Investigation required.'}
              </Typography>
            </Alert>
          )}
        </CardContent>
      </Card>

      {lineage && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Lineage Tree</Typography>
            <Typography variant="caption" color="text.secondary" mb={2} display="block">
              Annual → Monthly → Weekly → Daily → Shift → Foreman Entry
            </Typography>
            <List>
              <LineageTreeNode node={lineage} />
            </List>
          </CardContent>
        </Card>
      )}

      {!lineage && !loading && (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography color="text.secondary">
              Enter a Report Value ID to trace its lineage, or click any number in a report to navigate here.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
