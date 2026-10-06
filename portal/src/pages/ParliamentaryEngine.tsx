import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Chip, Button, LinearProgress, Grid, Dialog,
  DialogTitle, DialogContent, DialogActions, Alert, Divider, Accordion, AccordionSummary, AccordionDetails,
} from '@mui/material';
import { Refresh, ExpandMore, Campaign, CheckCircle, Warning } from '@mui/icons-material';
import { usePQPatterns, usePQPacks, useGeneratePQPacks } from '../api/hooks';

export default function ParliamentaryEngine() {
  const { data: patterns = [] } = usePQPatterns();
  const { data: packs = [] } = usePQPacks();
  const generate = useGeneratePQPacks();
  const [selected, setSelected] = useState<any>(null);

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h5">Predictive Parliamentary Engine</Typography>
          <Typography variant="body2" color="text.secondary">
            Evidence packs pre-generated BEFORE parliament asks — response time drops from days to hours
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Refresh />} loading={generate.isPending}
          onClick={() => generate.mutate(5)}>
          Generate Top 5 Packs
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Question Patterns — Likelihood Ranking</Typography>
              <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                Scored from 10-year history + seasonality + live operational triggers (deterministic)
              </Typography>
              {patterns.map((p) => (
                <Box key={p.id} mb={2}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                    <Typography variant="body2" fontWeight={600}>{p.title}</Typography>
                    <Chip size="small" label={`${Math.round((p.likelihood_score ?? 0) * 100)}%`}
                      color={(p.likelihood_score ?? 0) > 0.6 ? 'error' : (p.likelihood_score ?? 0) > 0.35 ? 'warning' : 'default'} />
                  </Box>
                  <LinearProgress variant="determinate" value={(p.likelihood_score ?? 0) * 100}
                    sx={{ height: 6, borderRadius: 3, mb: 0.5 }} />
                  <Typography variant="caption" color="text.secondary">
                    {p.category} · {p.trigger_type} · {p.historical_frequency_10y}× in 10y · {(p.likelihood_reasons ?? []).join('; ')}
                  </Typography>
                </Box>
              ))}
              {patterns.length === 0 && <Typography color="text.secondary">No patterns seeded</Typography>}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Evidence Packs</Typography>
              {packs.map((pack) => (
                <Card key={pack.id} variant="outlined" sx={{ mb: 1.5, p: 1.5, cursor: 'pointer' }} onClick={() => setSelected(pack)}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box display="flex" alignItems="center" gap={1}>
                      {pack.status === 'ready' ? <CheckCircle color="success" /> : <Warning color="warning" />}
                      <Typography variant="body2" fontWeight={600}>{pack.title}</Typography>
                    </Box>
                    <Chip size="small" label={`${Math.round(pack.likelihood_score * 100)}% likely`} />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {pack.status} · data as of {new Date(pack.data_as_of).toLocaleString()}
                  </Typography>
                </Card>
              ))}
              {packs.length === 0 && (
                <Alert severity="info">No packs generated yet — click "Generate Top 5 Packs".</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="md" fullWidth>
        <DialogTitle display="flex" alignItems="center" gap={1}>
          <Campaign /> {selected?.title}
        </DialogTitle>
        <DialogContent>
          {selected && (
            <>
              <Alert severity={selected.status === 'ready' ? 'success' : 'warning'} sx={{ mb: 2 }}>
                {selected.summary}
              </Alert>
              {Object.entries(selected.sections ?? {}).map(([key, section]: [string, any]) => (
                <Accordion key={key} defaultExpanded={key === 'production'}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle2">{section.title} ({section.figures.length} figures)</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {section.figures.map((f: any, i: number) => (
                      <Box key={i} mb={1.5}>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2">{f.label}</Typography>
                          <Typography variant="body2" fontWeight={700}>{f.value} {f.unit}</Typography>
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          source: {f.source_type}{f.source_ids.length > 0 ? ` (${f.source_ids.length} record(s))` : ''} — {f.note}
                        </Typography>
                        <Divider sx={{ mt: 0.5 }} />
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              ))}
              <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                Every figure carries source references for Replay-the-Number drill-down. Figures from unresolved
                conflicts are marked by the Truth Gate — the pack stays in DRAFT until a human resolves them.
              </Typography>
            </>
          )}
        </DialogContent>
        <DialogActions><Button onClick={() => setSelected(null)}>Close</Button></DialogActions>
      </Dialog>
    </Box>
  );
}
