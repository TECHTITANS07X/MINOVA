import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Box, CssBaseline, Divider, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Toolbar, Typography, Avatar, Menu, MenuItem, Badge, Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard, Edit, CheckCircle, Description, AccountTree,
  CompareArrows, Folder, SmartToy, Insights, Warning, Cloud, Security,
  Map, AdminPanelSettings, Notifications, DarkMode, LightMode,
} from '@mui/icons-material';
import { useAuth } from '../auth/KeycloakProvider';

const DRAWER_WIDTH = 260;

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: <Dashboard /> },
  { label: 'Data Entry', path: '/entry', icon: <Edit /> },
  { label: 'Approval', path: '/approval', icon: <CheckCircle /> },
  { label: 'Reports', path: '/reports', icon: <Description /> },
  { label: 'Replay the Number', path: '/replay', icon: <AccountTree /> },
  { label: 'Conflicts', path: '/conflicts', icon: <CompareArrows /> },
  { label: 'Documents', path: '/documents', icon: <Folder /> },
  { label: 'AI Assistant', path: '/chat', icon: <SmartToy /> },
  { label: 'Insights', path: '/insights', icon: <Insights /> },
  { label: 'Anomalies', path: '/anomalies', icon: <Warning /> },
  { label: 'Weather', path: '/weather', icon: <Cloud /> },
  { label: 'Audit Explorer', path: '/audit', icon: <Security /> },
  { label: 'Map View', path: '/map', icon: <Map /> },
  { label: 'Admin', path: '/admin', icon: <AdminPanelSettings /> },
];

interface LayoutProps {
  darkMode: boolean;
  onToggleDark: () => void;
}

export default function Layout({ darkMode, onToggleDark }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" fontWeight={700} color="primary">MINOVA</Typography>
      </Toolbar>
      <Divider />
      <List>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => { navigate(item.path); setMobileOpen(false); }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 14 }} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }} color="default" elevation={1}>
        <Toolbar>
          <IconButton edge="start" onClick={() => setMobileOpen(!mobileOpen)} sx={{ mr: 2, display: { md: 'none' } }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1, fontWeight: 700 }}>
            MINOVA
          </Typography>
          <Tooltip title={darkMode ? 'Light mode' : 'Dark mode'}>
            <IconButton onClick={onToggleDark} sx={{ mr: 1 }}>
              {darkMode ? <LightMode /> : <DarkMode />}
            </IconButton>
          </Tooltip>
          <IconButton sx={{ mr: 1 }}>
            <Badge badgeContent={3} color="error"><Notifications /></Badge>
          </IconButton>
          <IconButton onClick={(e) => setAnchorEl(e.currentTarget)}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchorEl} open={!!anchorEl} onClose={() => setAnchorEl(null)}>
            <MenuItem disabled><Typography variant="body2">{user?.name} ({user?.roles?.[0]})</Typography></MenuItem>
            <Divider />
            <MenuItem onClick={() => { setAnchorEl(null); logout(); }}>Sign Out</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)}
          sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: DRAWER_WIDTH } }}>
          {drawer}
        </Drawer>
        <Drawer variant="permanent"
          sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }} open>
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: 3, width: { md: `calc(100% - ${DRAWER_WIDTH}px)` } }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
