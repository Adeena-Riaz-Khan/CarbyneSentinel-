import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "../auth/AuthContext";
import type {
  BenchmarkDoc,
  GlobalStats,
  SettingsDoc,
  Transaction,
} from "../contracts/domain";
import { isApiError } from "../contracts/errors";
import { seedUser } from "../data/seeds";
import * as api from "../services/apiClient";

type DataCtx = {
  loading: boolean;
  error: string | null;
  clearError: () => void;
  user: typeof seedUser;
  stats: GlobalStats | null;
  transactions: Transaction[];
  settings: SettingsDoc | null;
  benchmarks: BenchmarkDoc | null;
  refresh: () => Promise<void>;
  saveSettings: (patch: Partial<SettingsDoc>) => Promise<boolean>;
};

const Ctx = createContext<DataCtx | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const { status, user: authUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [settings, setSettings] = useState<SettingsDoc | null>(null);
  const [benchmarks, setBenchmarks] = useState<BenchmarkDoc | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const profileUser = useMemo(() => {
    if (!authUser) return seedUser;
    return {
      initials: authUser.initials,
      wallet: authUser.wallet,
      role:
        authUser.role === "security_admin"
          ? "Security Admin"
          : authUser.role === "analyst"
            ? "Analyst"
            : "Viewer",
      network: authUser.network,
    };
  }, [authUser]);

  const refresh = useCallback(async () => {
    if (status !== "authenticated") return;
    setLoading(true);
    setError(null);
    try {
      const [s, txs, st, bm] = await Promise.all([
        api.getStats(),
        api.getTransactions(),
        api.getSettings().catch((e) => {
          if (isApiError(e) && e.code === "FORBIDDEN") return null;
          throw e;
        }),
        api.getBenchmarks(),
      ]);
      setStats(s);
      setTransactions(txs);
      setSettings(st);
      setBenchmarks(bm);
    } catch (e) {
      if (isApiError(e)) setError(e.message);
      else setError("Failed to load console data.");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    if (status !== "authenticated") {
      setStats(null);
      setTransactions([]);
      setSettings(null);
      setBenchmarks(null);
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const [s, txs, st, bm] = await Promise.all([
          api.getStats(controller.signal),
          api.getTransactions(controller.signal),
          api.getSettings(controller.signal).catch((e) => {
            if (isApiError(e) && e.code === "FORBIDDEN") return null;
            throw e;
          }),
          api.getBenchmarks(controller.signal),
        ]);
        if (cancelled) return;
        setStats(s);
        setTransactions(txs);
        setSettings(st);
        setBenchmarks(bm);
      } catch (e) {
        if (cancelled) return;
        if (isApiError(e)) setError(e.message);
        else setError("Failed to load console data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [status]);

  const saveSettings = useCallback(async (patch: Partial<SettingsDoc>) => {
    try {
      const next = await api.patchSettings(patch);
      setSettings(next);
      setError(null);
      return true;
    } catch (e) {
      if (isApiError(e)) setError(e.message);
      else setError("Could not save settings.");
      return false;
    }
  }, []);

  const value = useMemo(
    () => ({
      loading,
      error,
      clearError,
      user: profileUser,
      stats,
      transactions,
      settings,
      benchmarks,
      refresh,
      saveSettings,
    }),
    [
      loading,
      error,
      clearError,
      profileUser,
      stats,
      transactions,
      settings,
      benchmarks,
      refresh,
      saveSettings,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useData() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useData must be used inside DataProvider");
  return ctx;
}
