import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type {
  AuthUser,
  LoginInput,
  Permission,
  Session,
  SignupInput,
  WalletInput,
} from "../contracts/auth";
import { hasPermission } from "../contracts/auth";
import { isApiError } from "../contracts/errors";
import * as authService from "../services/authService";

type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthCtx = {
  status: AuthStatus;
  session: Session | null;
  user: AuthUser | null;
  authMode: "firebase" | "firebase-emulator" | "mock";
  error: string | null;
  fieldErrors: Record<string, string>;
  clearError: () => void;
  can: (permission: Permission) => boolean;
  signIn: (input: LoginInput) => Promise<boolean>;
  signUp: (input: SignupInput) => Promise<boolean>;
  connectWallet: (input: WalletInput) => Promise<boolean>;
  enterDemoConsole: () => Promise<boolean>;
  signOut: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    let alive = true;
    void authService.hydrateSession().then((existing) => {
      if (!alive) return;
      setSession(existing);
      setStatus(existing ? "authenticated" : "anonymous");
    });
    const unsub = authService.onAuthStateChanged((s) => {
      if (!alive) return;
      setSession(s);
      setStatus(s ? "authenticated" : "anonymous");
    });
    return () => {
      alive = false;
      unsub();
    };
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setFieldErrors({});
  }, []);

  const handleAuthError = useCallback((e: unknown) => {
    if (isApiError(e)) {
      setError(e.message);
      setFieldErrors(e.fields ?? {});
      return false;
    }
    setError("Something went wrong. Try again.");
    setFieldErrors({});
    return false;
  }, []);

  const signIn = useCallback(
    async (input: LoginInput) => {
      clearError();
      try {
        const s = await authService.signIn(input);
        setSession(s);
        setStatus("authenticated");
        return true;
      } catch (e) {
        return handleAuthError(e);
      }
    },
    [clearError, handleAuthError],
  );

  const signUp = useCallback(
    async (input: SignupInput) => {
      clearError();
      try {
        const s = await authService.signUp(input);
        setSession(s);
        setStatus("authenticated");
        return true;
      } catch (e) {
        return handleAuthError(e);
      }
    },
    [clearError, handleAuthError],
  );

  const connectWallet = useCallback(
    async (input: WalletInput) => {
      clearError();
      try {
        const s = await authService.connectWallet(input);
        setSession(s);
        setStatus("authenticated");
        return true;
      } catch (e) {
        return handleAuthError(e);
      }
    },
    [clearError, handleAuthError],
  );

  const enterDemoConsole = useCallback(async () => {
    clearError();
    try {
      const s = await authService.enterDemoConsole();
      setSession(s);
      setStatus("authenticated");
      return true;
    } catch (e) {
      return handleAuthError(e);
    }
  }, [clearError, handleAuthError]);

  const signOut = useCallback(async () => {
    await authService.signOut();
    setSession(null);
    setStatus("anonymous");
    clearError();
  }, [clearError]);

  const can = useCallback(
    (permission: Permission) => {
      if (!session) return false;
      return hasPermission(session.user.role, permission);
    },
    [session],
  );

  const value = useMemo<AuthCtx>(
    () => ({
      status,
      session,
      user: session?.user ?? null,
      authMode: authService.authMode(),
      error,
      fieldErrors,
      clearError,
      can,
      signIn,
      signUp,
      connectWallet,
      enterDemoConsole,
      signOut,
    }),
    [
      status,
      session,
      error,
      fieldErrors,
      clearError,
      can,
      signIn,
      signUp,
      connectWallet,
      enterDemoConsole,
      signOut,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
