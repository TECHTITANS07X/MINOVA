import { useState, useMemo } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SnackbarProvider } from 'notistack';

import { createAppTheme } from './theme';
import { AuthProvider } from './auth/KeycloakProvider';
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

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
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </SnackbarProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
