/**
 * Firebase-shaped data layer.
 * Uses in-memory fake seeds by default so the UI runs without a Firebase project.
 * Swap `USE_LIVE_FIREBASE` + env vars when a real project is ready.
 */
import {
  seedAgents,
  seedBenchmark,
  seedIntercept,
  seedSettings,
  seedStats,
  seedTransactions,
  seedUser,
  type Agent,
  type BenchmarkDoc,
  type GlobalStats,
  type InterceptAlert,
  type SettingsDoc,
  type Transaction,
} from "../data/seeds";

const USE_LIVE_FIREBASE = false;

type Collections = {
  user: typeof seedUser;
  stats: GlobalStats;
  transactions: Transaction[];
  agents: Agent[];
  interceptAlert: InterceptAlert;
  settings: SettingsDoc;
  benchmarks: BenchmarkDoc;
};

const memoryDb: Collections = {
  user: { ...seedUser },
  stats: { ...seedStats },
  transactions: seedTransactions.map((t) => ({ ...t })),
  agents: seedAgents.map((a) => ({
    ...a,
    recentTxs: a.recentTxs.map((t) => ({ ...t })),
  })),
  interceptAlert: { ...seedIntercept },
  settings: { ...seedSettings },
  benchmarks: {
    ...seedBenchmark,
    latencyStages: seedBenchmark.latencyStages.map((s) => ({ ...s })),
    matrix: seedBenchmark.matrix.map((row) => [...row]),
  },
};

export async function getDoc<K extends keyof Collections>(
  collection: K,
): Promise<Collections[K]> {
  if (USE_LIVE_FIREBASE) {
    throw new Error("Live Firebase not configured — set USE_LIVE_FIREBASE and env vars.");
  }
  await delay(40);
  return structuredClone(memoryDb[collection]);
}

export async function updateSettings(
  patch: Partial<SettingsDoc>,
): Promise<SettingsDoc> {
  memoryDb.settings = { ...memoryDb.settings, ...patch };
  await delay(40);
  return structuredClone(memoryDb.settings);
}

export async function freezeAgent(agentId: string, frozen: boolean): Promise<Agent[]> {
  memoryDb.agents = memoryDb.agents.map((a) =>
    a.id === agentId ? { ...a, status: frozen ? "FROZEN" : "ACTIVE" } : a,
  );
  await delay(40);
  return structuredClone(memoryDb.agents);
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export const collections = {
  user: "user",
  stats: "stats",
  transactions: "transactions",
  agents: "agents",
  interceptAlert: "interceptAlert",
  settings: "settings",
  benchmarks: "benchmarks",
} as const;
