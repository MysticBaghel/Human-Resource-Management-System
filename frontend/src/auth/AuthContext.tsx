/** Session context: who is signed in, and the actions that change it. */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  login as loginRequest,
  logout as logoutRequest,
  meQueryKey,
  useMe,
  type Role,
  type User,
} from "@/api/queries";

type AuthContextValue = {
  user: User | null;
  role: Role | null;
  /** True only while the session is being resolved for the first time. */
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  /** Role check for the UI. The API enforces the real rule. */
  hasRole: (...roles: Role[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useMe();
  const user = data ?? null;

  const login = useCallback(
    async (email: string, password: string) => {
      const loggedIn = await loginRequest(email, password);
      // Seed the cache so the route guards see the user immediately, without
      // a second round trip back to /auth/me/.
      queryClient.setQueryData(meQueryKey, loggedIn);
      return loggedIn;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      queryClient.setQueryData(meQueryKey, null);
      queryClient.clear();
    }
  }, [queryClient]);

  const hasRole = useCallback(
    (...roles: Role[]) => (user ? roles.includes(user.role) : false),
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      role: user?.role ?? null,
      isLoading,
      isAuthenticated: user !== null,
      login,
      logout,
      hasRole,
    }),
    [user, isLoading, login, logout, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside an AuthProvider.");
  }
  return context;
}
