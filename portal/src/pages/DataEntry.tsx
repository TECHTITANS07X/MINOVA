import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button, Grid, Select, MenuItem,
  FormControl, InputLabel, Chip, Stepper, Step, StepLabel, CircularProgress, Alert, Snackbar,
} from '@mui/material';
import { Save, Send } from '@mui/icons-material';
import { useMines, useCreateEntry, useSubmitEntry } from '../api/hooks';

export default function DataEntry() {
  const [shift, setShift] = useState('first');
  const [step, setStep] = useState(0);
  const [mineId, setMineId] = useState('');
  const [shiftDate, setShiftDate] = useState('');
  const [production, setProduction] = useState('');
  const [overburden, setOverburden] = useState('');
  const [operatingHours, setOperatingHours] = useState('');
  const [workersPresent, setWorkersPresent] = useState('');
  const [remarks, setRemarks] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  });

  const { data: mines = [] } = useMines();
  const createEntry = useCreateEntry();
  const submitEntry = useSubmitEntry();
  const steps = ['Production & OB', 'Equipment & Dispatch', 'Causes & Remarks', 'Review & Submit'];

  function buildPayload() {
    return {
      mine_id: mineId,
      shift_date: new Date(shiftDate).toISOString(),
      shift_number: shift,
      remarks,
      values: [
        { metric: 'production_tonnes', value: Number(production) || 0, unit: 't' },
        { metric: 'overburden_m3', value: Number(overburden) || 0, unit: 'm³' },
        { metric: 'operating_hours', value: Number(operatingHours) || 0, unit: 'hrs' },
        { metric: 'workers_present', value: Number(workersPresent) || 0, unit: 'count' },
      ],
    };
  }

  function handleSaveDraft() {
    createEntry.mutate(buildPayload(), {
      onSuccess: () => setSnackbar({ open: true, message: 'Draft saved successfully', severity: 'success' }),
      onError: () => setSnackbar({ open: true, message: 'Failed to save draft', severity: 'error' }),
    });
  }

  function handleSubmit() {
    createEntry.mutate(buildPayload(), {
      onSuccess: (entry: any) => {
        const entryId = entry?.id ?? entry?.data?.id;
        submitEntry.mutate(entryId, {
          onSuccess: () => setSnackbar({ open: true, message: 'Entry submitted for approval', severity: 'success' }),
          onError: () => setSnackbar({ open: true, message: 'Failed to submit entry', severity: 'error' }),
        });
      },
      onError: () => setSnackbar({ open: true, message: 'Failed to create entry', severity: 'error' }),
    });
  }

  const isMutating = createEntry.isPending || submitEntry.isPending;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Shift Data Entry</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Enter shift-level production data. Saved as draft until submitted.
      </Typography>

      <Stepper activeStep={step} sx={{ mb: 3 }}>
        {steps.map((label) => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
      </Stepper>

      <Card>
        <CardContent>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Shift Date" type="date" fullWidth
                value={shiftDate}
                onChange={(e) => setShiftDate(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <FormControl fullWidth>
                <InputLabel>Shift</InputLabel>
                <Select value={shift} label="Shift" onChange={(e) => setShift(e.target.value)}>
                  <MenuItem value="first">Shift 1 (6:00-14:00)</MenuItem>
                  <MenuItem value="second">Shift 2 (14:00-22:00)</MenuItem>
                  <MenuItem value="third">Shift 3 (22:00-6:00)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <FormControl fullWidth>
                <InputLabel>Mine</InputLabel>
                <Select value={mineId} label="Mine" onChange={(e) => setMineId(e.target.value)}>
                  {mines.map((m) => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>

            {step === 0 && (
              <>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    label="Production (tonnes)" type="number" fullWidth
                    value={production}
                    onChange={(e) => setProduction(e.target.value)}
                    slotProps={{ input: { endAdornment: <Chip size="small" label="t" /> } }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    label="Overburden (m³)" type="number" fullWidth
                    value={overburden}
                    onChange={(e) => setOverburden(e.target.value)}
                    slotProps={{ input: { endAdornment: <Chip size="small" label="m³" /> } }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    label="Operating Hours" type="number" fullWidth
                    value={operatingHours}
                    onChange={(e) => setOperatingHours(e.target.value)}
                    slotProps={{ htmlInput: { max: 8, step: 0.5 } }}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    label="Workers Present" type="number" fullWidth
                    value={workersPresent}
                    onChange={(e) => setWorkersPresent(e.target.value)}
                  />
                </Grid>
              </>
            )}

            {step === 2 && (
              <Grid size={{ xs: 12 }}>
                <TextField
                  label="Remarks" multiline rows={3} fullWidth
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                />
              </Grid>
            )}

            <Grid size={{ xs: 12 }}>
              <Box display="flex" gap={2} justifyContent="space-between" mt={2}>
                <Button disabled={step === 0} onClick={() => setStep(s => s - 1)}>Back</Button>
                <Box display="flex" gap={1}>
                  <Button
                    variant="outlined"
                    startIcon={isMutating ? <CircularProgress size={16} /> : <Save />}
                    onClick={handleSaveDraft}
                    disabled={isMutating}
                  >
                    Save Draft
                  </Button>
                  {step < steps.length - 1 ? (
                    <Button variant="contained" onClick={() => setStep(s => s + 1)}>Next</Button>
                  ) : (
                    <Button
                      variant="contained" color="success"
                      startIcon={isMutating ? <CircularProgress size={16} /> : <Send />}
                      onClick={handleSubmit}
                      disabled={isMutating}
                    >
                      Submit
                    </Button>
                  )}
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar(s => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar(s => ({ ...s, open: false }))}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
}
