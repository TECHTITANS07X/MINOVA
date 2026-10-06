import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import { keycloak } from '../auth/KeycloakProvider';

export default function Login() {
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || '/';
  const back = window.location.origin + from;

  useEffect(() => {
    // Redirect straight to Keycloak after a beat; the button is a manual fallback.
    // `from` preserves the originally requested path so deep links survive the round-trip.
    const t = setTimeout(() => {
      if (!keycloak.authenticated) keycloak.login({ redirectUri: back });
    }, 300);
    return () => clearTimeout(t);
  }, [back]);

  const signIn = () => keycloak.login({ redirectUri: back });

  return (
    <Box
      sx={{
        minHeight: '80vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 2,
      }}
    >
      <Typography variant="h5" fontWeight={700}>MINOVA</Typography>
      <CircularProgress size={28} />
      <Button variant="contained" onClick={signIn}>
        Sign in with Keycloak
      </Button>
    </Box>
  );
}
