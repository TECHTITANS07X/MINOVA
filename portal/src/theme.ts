import { createTheme } from '@mui/material/styles';

export function createAppTheme(mode: 'light' | 'dark') {
  return createTheme({
    palette: {
      mode,
      primary: { main: '#1B5E20', light: '#4C8C4A', dark: '#003300' },
      secondary: { main: '#E65100', light: '#FF833A', dark: '#AC1900' },
      error: { main: '#D32F2F' },
      warning: { main: '#F57C00' },
      success: { main: '#2E7D32' },
      info: { main: '#0277BD' },
      background: mode === 'light'
        ? { default: '#F5F5F0', paper: '#FFFFFF' }
        : { default: '#121212', paper: '#1E1E1E' },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h4: { fontWeight: 700 },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
    },
    shape: { borderRadius: 8 },
    components: {
      MuiCard: {
        defaultProps: { elevation: 1 },
        styleOverrides: { root: { borderRadius: 12 } },
      },
      MuiButton: {
        styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } },
      },
      MuiChip: {
        styleOverrides: { root: { fontWeight: 500 } },
      },
    },
  });
}
