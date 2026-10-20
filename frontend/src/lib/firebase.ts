/**
 * Firebase-shaped data layer.
 * Uses in-memory fake seeds by default so the UI runs without a Firebase project.
 * Swap `USE_LIVE_FIREBASE` + env vars when a real project is ready.
 */
import {
  seedBenchmark,
  seedSettings,
  seedStats,
  seedTransactions,
  seedUser,
  type BenchmarkDoc,
  type GlobalStats,
  type SettingsDoc,
  type Transaction,
} from "../data/seeds";

const USE_LIVE_FIREBASE = false;

type Collections = {
  user: typeof seedUser;
  stats: GlobalStats;
  transactions: Transaction[];
  settings: SettingsDoc;
  benchmarks: BenchmarkDoc;
};

const memoryDb: Collections = {
  user: { ...seedUser },
  stats: { ...seedStats },
  transactions: seedTransactions.map((t) => ({ ...t })),
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

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export const collections = {
  user: "user",
  stats: "stats",
  transactions: "transactions",
  settings: "settings",
  benchmarks: "benchmarks",
} as const;
