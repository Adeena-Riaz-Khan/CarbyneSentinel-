import type {
  BenchmarkDoc,
  GlobalStats,
  SettingsDoc,
  Transaction,
} from "../contracts/domain";
import { ApiError } from "../contracts/errors";
import { PENDING_FEED_TOTAL } from "../contracts/grids";
import { isFirestoreDataEnabled } from "../lib/firebaseApp";
import { validateSettingsPatch } from "../validation/forms";
import { can, getCurrentSession, requirePermission } from "./authService";
import {
  seedBenchmark,
  seedSettings,
  seedStats,
  seedTransactions,
} from "../data/seeds";
import * as fs from "./firestoreRepo";

type Memory = {
  stats: GlobalStats;
  transactions: Transaction[];
  settings: SettingsDoc;
  benchmarks: BenchmarkDoc;
};

const memory: Memory = {
  stats: { ...seedStats, pendingTotal: PENDING_FEED_TOTAL },
  transactions: seedTransactions.map((t) => ({ ...t })),
  settings: { ...seedSettings },
  benchmarks: {
    ...seedBenchmark,
    latencyStages: seedBenchmark.latencyStages.map((s) => ({ ...s })),
    matrix: seedBenchmark.matrix.map((r) => [...r]),
  },
};

let networkDown = false;

export function __setNetworkDown(down: boolean) {
  networkDown = down;
}

export function __resetApiForTests() {
  networkDown = false;
  memory.stats = { ...seedStats, pendingTotal: PENDING_FEED_TOTAL };
  memory.transactions = seedTransactions.map((t) => ({ ...t }));
  memory.settings = { ...seedSettings };
  memory.benchmarks = {
    ...seedBenchmark,
    latencyStages: seedBenchmark.latencyStages.map((s) => ({ ...s })),
    matrix: seedBenchmark.matrix.map((r) => [...r]),
  };
}

function assertAuth() {
  if (!getCurrentSession()) {
    throw new ApiError("UNAUTHORIZED", "Sign in required.", 401);
  }
}

async function gate(signal?: AbortSignal) {
  if (signal?.aborted) throw new ApiError("NETWORK", "Request aborted.", 499);
  if (networkDown) throw new ApiError("UNAVAILABLE", "Service temporarily unavailable.", 503);
  if (!isFirestoreDataEnabled()) await delay(20);
  if (signal?.aborted) throw new ApiError("NETWORK", "Request aborted.", 499);
}

export async function getStats(signal?: AbortSignal): Promise<GlobalStats> {
  await gate(signal);
  assertAuth();
  requirePermission("mempool:read");
  if (isFirestoreDataEnabled()) return fs.fsGetStats();
  return structuredClone(memory.stats);
}

export async function getTransactions(signal?: AbortSignal): Promise<Transaction[]> {
  await gate(signal);
  assertAuth();
  requirePermission("mempool:read");
  if (isFirestoreDataEnabled()) return fs.fsGetTransactions();
  return structuredClone(memory.transactions);
}

export async function getBenchmarks(signal?: AbortSignal): Promise<BenchmarkDoc> {
  await gate(signal);
  assertAuth();
  requirePermission("analytics:read");
  if (isFirestoreDataEnabled()) return fs.fsGetBenchmarks();
  return structuredClone(memory.benchmarks);
}

export async function getSettings(signal?: AbortSignal): Promise<SettingsDoc> {
  await gate(signal);
  assertAuth();
  requirePermission("settings:read");
  if (isFirestoreDataEnabled()) return fs.fsGetSettings();
  return structuredClone(memory.settings);
}

export async function patchSettings(
  patch: Partial<SettingsDoc>,
  signal?: AbortSignal,
): Promise<SettingsDoc> {
  await gate(signal);
  assertAuth();
  requirePermission("settings:write");
  if (isFirestoreDataEnabled()) return fs.fsPatchSettings(patch);
  const parsed = validateSettingsPatch(patch, memory.settings);
  if (!parsed.ok) {
    throw new ApiError("VALIDATION", parsed.message, 400, parsed.errors);
  }
  memory.settings = { ...memory.settings, ...parsed.data };
  return structuredClone(memory.settings);
}

export function canExportAnalytics(): boolean {
  return can("analytics:export");
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
