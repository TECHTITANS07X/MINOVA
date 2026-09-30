import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button, Grid, Select, MenuItem,
  FormControl, InputLabel, Chip, Stepper, Step, StepLabel, Alert,
} from '@mui/material';
import { Save, Send } from '@mui/icons-material';

export default function DataEntry() {
  const [shift, setShift] = useState('first');
  const [step, setStep] = useState(0);
  const steps = ['Production & OB', 'Equipment & Dispatch', 'Causes & Remarks', 'Review & Submit'];

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
              <TextField label="Shift Date" type="date" fullWidth slotProps={{ inputLabel: { shrink: true } }} />
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
                <Select defaultValue="" label="Mine">
                  <MenuItem value="mine1">DEMO Mine Alpha</MenuItem>
                  <MenuItem value="mine2">DEMO Mine Beta</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {step === 0 && (
              <>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField label="Production (tonnes)" type="number" fullWidth
                    slotProps={{ input: { endAdornment: <Chip size="small" label="t" /> } }} />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField label="Overburden (m³)" type="number" fullWidth
                    slotProps={{ input: { endAdornment: <Chip size="small" label="m³" /> } }} />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField label="Operating Hours" type="number" fullWidth slotProps={{ htmlInput: { max: 8, step: 0.5 } }} />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField label="Workers Present" type="number" fullWidth />
                </Grid>
              </>
            )}

            <Grid size={{ xs: 12 }}>
              <Box display="flex" gap={2} justifyContent="space-between" mt={2}>
                <Button disabled={step === 0} onClick={() => setStep(s => s - 1)}>Back</Button>
                <Box display="flex" gap={1}>
                  <Button variant="outlined" startIcon={<Save />}>Save Draft</Button>
                  {step < steps.length - 1 ? (
                    <Button variant="contained" onClick={() => setStep(s => s + 1)}>Next</Button>
                  ) : (
                    <Button variant="contained" color="success" startIcon={<Send />}>Submit</Button>
                  )}
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}
