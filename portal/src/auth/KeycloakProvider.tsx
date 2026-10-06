import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import Keycloak from 'keycloak-js';
import type { User } from '../types';

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8081',
  realm: 'minova',
  clientId: 'minova-portal',
});

interface AuthContextType {
  user: User | null;
  authenticated: boolean;
  loading: boolean;
  token: string | null;
  login: () => void;
  logout: () => void;
  hasRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  authenticated: false,
  loading: true,
  token: null,
  login: () => {},
  logout: () => {},
  hasRole: () => false,
});

// Module-scope init promise: React StrictMode double-invokes effects in dev,
// which would call keycloak.init twice — one run consumes the PKCE ?code= from
// the redirect while the other resolves unauthenticated, bouncing the user
// back to /login even with a valid session. Init once, consume everywhere.
// onLoad 'login-required' (not check-sso): without a silent-check-sso iframe on
// the Keycloak origin, check-sso falls back to a full-page redirect that drops
// the deep-linked path. login-required redirects with the current URL as target.
const keycloakInit = keycloak.init({
  onLoad: 'login-required',
  pkceMethod: 'S256',
  checkLoginIframe: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    keycloakInit
      .then((auth) => {
        setAuthenticated(auth);
        if (auth && keycloak.tokenParsed) {
          const parsed = keycloak.tokenParsed;
          const roles = parsed.realm_access?.roles || parsed.realm_roles || [];
          setUser({
            sub: parsed.sub || '',
            email: parsed.email || '',
            name: parsed.preferred_username || parsed.name || '',
            roles,
            mine_id: parsed.mine || null,
            department: parsed.department || null,
          });
          setToken(keycloak.token || null);
          sessionStorage.setItem('minova_token', keycloak.token || '');
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));

    keycloak.onTokenExpired = () => {
      keycloak.updateToken(30).then(() => {
        setToken(keycloak.token || null);
        sessionStorage.setItem('minova_token', keycloak.token || '');
      });
    };
  }, []);

  const login = () => keycloak.login();
  const logout = () => {
    sessionStorage.removeItem('minova_token');
    keycloak.logout();
  };
  const hasRole = (role: string) => user?.roles.includes(role) ?? false;

  return (
    <AuthContext.Provider value={{ user, authenticated, loading, token, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
