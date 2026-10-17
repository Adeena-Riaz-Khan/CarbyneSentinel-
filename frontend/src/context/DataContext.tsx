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
  Agent,
  BenchmarkDoc,
  GlobalStats,
  InterceptAlert,
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
  agents: Agent[];
  intercept: InterceptAlert | null;
  settings: SettingsDoc | null;
  benchmarks: BenchmarkDoc | null;
  refresh: () => Promise<void>;
  saveSettings: (patch: Partial<SettingsDoc>) => Promise<boolean>;
  toggleFreeze: (agentId: string) => Promise<boolean>;
};

const Ctx = createContext<DataCtx | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const { status, user: authUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [intercept, setIntercept] = useState<InterceptAlert | null>(null);
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
      const [s, txs, ag, al, st, bm] = await Promise.all([
        api.getStats(),
        api.getTransactions(),
        api.getAgents(),
        api.getIntercept(),
        api.getSettings().catch((e) => {
          if (isApiError(e) && e.code === "FORBIDDEN") return null;
          throw e;
        }),
        api.getBenchmarks(),
      ]);
      setStats(s);
      setTransactions(txs);
      setAgents(ag);
      setIntercept(al);
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
      setAgents([]);
      setIntercept(null);
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
        const [s, txs, ag, al, st, bm] = await Promise.all([
          api.getStats(controller.signal),
          api.getTransactions(controller.signal),
          api.getAgents(controller.signal),
          api.getIntercept(controller.signal),
          api.getSettings(controller.signal).catch((e) => {
            if (isApiError(e) && e.code === "FORBIDDEN") return null;
            throw e;
          }),
          api.getBenchmarks(controller.signal),
        ]);
        if (cancelled) return;
        setStats(s);
        setTransactions(txs);
        setAgents(ag);
        setIntercept(al);
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

  const toggleFreeze = useCallback(
    async (agentId: string) => {
      const current = agents.find((a) => a.id === agentId);
      if (!current) return false;
      try {
        const next = await api.freezeAgent(agentId, current.status !== "FROZEN");
        setAgents(next);
        setError(null);
        return true;
      } catch (e) {
        if (isApiError(e)) setError(e.message);
        else setError("Could not update agent.");
        return false;
      }
    },
    [agents],
  );

  const value = useMemo(
    () => ({
      loading,
      error,
      clearError,
      user: profileUser,
      stats,
      transactions,
      agents,
      intercept,
      settings,
      benchmarks,
      refresh,
      saveSettings,
      toggleFreeze,
    }),
    [
      loading,
      error,
      clearError,
      profileUser,
      stats,
      transactions,
      agents,
      intercept,
      settings,
      benchmarks,
      refresh,
      saveSettings,
      toggleFreeze,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useData() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useData must be used inside DataProvider");
  return ctx;
}
