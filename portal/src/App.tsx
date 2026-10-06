import { useState, useMemo } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { Box, CircularProgress, CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SnackbarProvider } from 'notistack';

import { createAppTheme } from './theme';
import { AuthProvider, useAuth } from './auth/KeycloakProvider';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DataEntry from './pages/DataEntry';
import ApprovalConsole from './pages/ApprovalConsole';
import Reports from './pages/Reports';
import ReplayTheNumber from './pages/ReplayTheNumber';
import Conflicts from './pages/Conflicts';
import Documents from './pages/Documents';
import AIChat from './pages/AIChat';
import Insights from './pages/Insights';
import Anomalies from './pages/Anomalies';
import Weather from './pages/Weather';
import AuditExplorer from './pages/AuditExplorer';
import MapView from './pages/MapView';
import Admin from './pages/Admin';
import Notifications from './pages/Notifications';
import Login from './pages/Login';
import ParliamentaryEngine from './pages/ParliamentaryEngine';
import QualityCorrelation from './pages/QualityCorrelation';
import LossLedger from './pages/LossLedger';
import ShiftHandover from './pages/ShiftHandover';
import Compliance from './pages/Compliance';
import Intelligence from './pages/Intelligence';
import MeetingTracker from './pages/MeetingTracker';
import KnowledgeBase from './pages/KnowledgeBase';
import SafetyPatterns from './pages/SafetyPatterns';
import PhotoVerification from './pages/PhotoVerification';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

/** Blocks rendering until Keycloak init settles; redirects unauthenticated users to /login. */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { loading, authenticated } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  if (!authenticated && location.pathname !== '/login')
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (authenticated && location.pathname === '/login') return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('minova_dark_mode') === 'true';
  });

  const theme = useMemo(() => createAppTheme(darkMode ? 'dark' : 'light'), [darkMode]);

  const toggleDark = () => {
    setDarkMode((prev) => {
      localStorage.setItem('minova_dark_mode', String(!prev));
      return !prev;
    });
  };

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
          <AuthProvider>
            <BrowserRouter>
              <AuthGate>
              <Routes>
                <Route element={<Layout darkMode={darkMode} onToggleDark={toggleDark} />}>
                  <Route index element={<Dashboard />} />
                  <Route path="entry" element={<DataEntry />} />
                  <Route path="approval" element={<ApprovalConsole />} />
                  <Route path="reports" element={<Reports />} />
                  <Route path="replay" element={<ReplayTheNumber />} />
                  <Route path="conflicts" element={<Conflicts />} />
                  <Route path="documents" element={<Documents />} />
                  <Route path="chat" element={<AIChat />} />
                  <Route path="insights" element={<Insights />} />
                  <Route path="anomalies" element={<Anomalies />} />
                  <Route path="weather" element={<Weather />} />
                  <Route path="audit" element={<AuditExplorer />} />
                  <Route path="map" element={<MapView />} />
                  <Route path="admin" element={<Admin />} />
                  <Route path="notifications" element={<Notifications />} />
                  <Route path="login" element={<Login />} />
                  <Route path="parliament" element={<ParliamentaryEngine />} />
                  <Route path="quality" element={<QualityCorrelation />} />
                  <Route path="loss-ledger" element={<LossLedger />} />
                  <Route path="handover" element={<ShiftHandover />} />
                  <Route path="compliance" element={<Compliance />} />
                  <Route path="intelligence" element={<Intelligence />} />
                  <Route path="meetings" element={<MeetingTracker />} />
                  <Route path="knowledge" element={<KnowledgeBase />} />
                  <Route path="safety-patterns" element={<SafetyPatterns />} />
                  <Route path="photo-verify" element={<PhotoVerification />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
              </AuthGate>
            </BrowserRouter>
          </AuthProvider>
        </SnackbarProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
