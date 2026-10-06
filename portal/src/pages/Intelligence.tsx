import {
  Box, Card, CardContent, Typography, Chip, Grid,
  Alert, Accordion, AccordionSummary, AccordionDetails,
} from '@mui/material';
import { ExpandMore, WarningAmber, Science } from '@mui/icons-material';
import { useExplosivesAnalysis, useGeologyDeviations } from '../api/hooks';

export default function Intelligence() {
  const { data: exp } = useExplosivesAnalysis();
  const { data: geo } = useGeologyDeviations();

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Correlation Intelligence</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Cross-domain correlations that no siloed CIL system performs: explosives-to-output and geology prediction accuracy
      </Typography>

      <Grid container spacing={3}>
        {/* ── Explosive-to-Output Correlation ── */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Explosive-to-Output Correlation</Typography>
              <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                kg explosive per m³ overburden vs mine baseline — anomalies indicate waste, theft, or unexpected geology (PESO-regulated)
              </Typography>
              {exp && (
                <>
                  <Grid container spacing={2} mb={2}>
                    <Grid size={{ xs: 4 }}><Card variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={700}>{exp.logs_analyzed}</Typography>
                      <Typography variant="caption">logs analyzed</Typography>
                    </Card></Grid>
                    <Grid size={{ xs: 4 }}><Card variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={700} color={exp.flagged.length > 0 ? 'error.main' : 'success.main'}>
                        {exp.flagged.length}
                      </Typography>
                      <Typography variant="caption">flagged</Typography>
                    </Card></Grid>
                    <Grid size={{ xs: 4 }}><Card variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={700} color="warning.main">
                        {exp.estimated_excess_kg.toLocaleString()}
                      </Typography>
                      <Typography variant="caption">excess kg est.</Typography>
                    </Card></Grid>
                  </Grid>
                  {exp.flagged.map((f: any) => (
                    <Alert key={f.log_id} severity={f.flag === 'over_consumption' ? 'error' : 'warning'} sx={{ mb: 1 }}>
                      <Typography variant="body2" fontWeight={600}>
                        {f.mine} — {f.date}: {f.kg_per_m3} kg/m³ vs baseline {f.baseline} ({f.deviation_pct > 0 ? '+' : ''}{f.deviation_pct.toFixed(1)}%)
                      </Typography>
                      <Typography variant="caption">
                        Possible: {f.possible_explanations.join(' · ')} — {f.explosives_kg.toLocaleString()} kg used on {f.ob_m3.toLocaleString()} m³
                      </Typography>
                    </Alert>
                  ))}
                  {exp.flagged.length === 0 && <Alert severity="success">All consumption within baseline thresholds (±15%)</Alert>}
                  <Typography variant="caption" color="text.secondary" display="block" mt={1}>{exp.note}</Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* ── Geological Deviation Learning Loop ── */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Geological Deviation Learning Loop</Typography>
              <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                CMPDI predictions vs actual geology encountered — accuracy stats feed back into future prediction confidence
              </Typography>
              {geo && (
                <>
                  {geo.alert && <Alert severity="warning" sx={{ mb: 2 }}><WarningAmber fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />{geo.alert}</Alert>}
                  <Grid container spacing={2} mb={2}>
                    <Grid size={{ xs: 4 }}><Card variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={700}>{geo.thickness_accuracy.n}</Typography>
                      <Typography variant="caption">thickness observations</Typography>
                    </Card></Grid>
                    <Grid size={{ xs: 4 }}><Card variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={700}>{geo.thickness_accuracy.bias_pct ?? '—'}</Typography>
                      <Typography variant="caption">thickness bias %</Typography>
                    </Card></Grid>
                    <Grid size={{ xs: 4 }}><Card variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={700} color="primary">
                        {geo.recommended_tolerance.thickness_pct ?? '—'}%
                      </Typography>
                      <Typography variant="caption">recommended tolerance</Typography>
                    </Card></Grid>
                  </Grid>
                  {geo.predictions.map((p: any) => (
                    <Accordion key={p.prediction_id} elevation={0} sx={{ border: 1, borderColor: 'divider', mb: 1 }}>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Box display="flex" justifyContent="space-between" width="100%" alignItems="center">
                          <Typography variant="body2" fontWeight={600}>
                            <Science fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                            {p.mine} — seam {p.seam} <Typography component="span" variant="caption">({p.source})</Typography>
                          </Typography>
                          {p.severe_deviations > 0
                            ? <Chip size="small" color="error" label={`${p.severe_deviations} severe`} />
                            : <Chip size="small" color="success" label="in tolerance" />}
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="caption" display="block">
                          Predicted: {p.predicted_thickness_m} m thickness, {p.predicted_gcv} kcal GCV (tolerance ±{p.tolerance_pct}%)
                        </Typography>
                        {p.latest && (
                          <Typography variant="caption" display="block" color={p.latest.severity === 'severe' ? 'error' : 'inherit'}>
                            Latest ({p.latest.date}): {p.latest.actual_thickness_m} m ({p.latest.thickness_dev_pct > 0 ? '+' : ''}{p.latest.thickness_dev_pct.toFixed(1)}%),
                            {p.latest.actual_gcv} kcal ({p.latest.gcv_dev_pct > 0 ? '+' : ''}{p.latest.gcv_dev_pct.toFixed(1)}%) — {p.latest.severity.replace(/_/g, ' ')}
                          </Typography>
                        )}
                        <Typography variant="caption" display="block" color="text.secondary">
                          {p.observations} observation(s) · mean thickness deviation {p.mean_thickness_dev_pct ?? '—'}%
                        </Typography>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                  <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                    {geo.recommended_tolerance.note}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
