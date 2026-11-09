import type {
  BenchmarkDoc,
  BytecodeAnalysisReport,
  DemoExample,
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

const INFERENCE_API_BASE = "http://127.0.0.1:8000";

const FALLBACK_DEMOS: DemoExample[] = [
  {
    id: "SMARTBUGS_reentrancy_reentrancy_insecure",
    title: "Known Vulnerable — Reentrancy (Exact Compiler)",
    description: "Labelled dataset contract from SmartBugs (reentrancy, test split, solc 0.4.26).",
    ground_truth_label: "reentrancy",
    dataset_source: "smartbugs",
    split: "test",
    compiler_version: "0.4.26",
    recovery_status: "original_dataset_bytecode",
    used_fallback: false,
    bytecode: "608060405260043610610041576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff1680632e1a7d4d14610046575b600080fd5b00",
  },
  {
    id: "SMARTBUGS_reentrancy_spank_chain_payment",
    title: "Unlinked Library Placeholder (Excluded Contract)",
    description: "Compiled artifact from SmartBugs containing unresolved __Library__ placeholders in runtime bytecode.",
    ground_truth_label: "reentrancy",
    dataset_source: "smartbugs",
    split: "test",
    compiler_version: "0.4.23",
    recovery_status: "failed",
    used_fallback: false,
    bytecode: "6080604052__ECTools_______________________________00",
  },
  {
    id: "SYNTHETIC_MALFORMED_ODD_HEX",
    title: "Malformed Bytecode — Odd Hex / Invalid Input",
    description: "Synthetic malformed runtime hex string to demonstrate input validation failure handling.",
    ground_truth_label: null,
    dataset_source: "synthetic_validation_case",
    split: null,
    compiler_version: null,
    recovery_status: "synthetic_invalid",
    used_fallback: false,
    bytecode: "0x6080604052348015610010576",
  },
];

export async function getDemoExamples(signal?: AbortSignal): Promise<DemoExample[]> {
  await gate(signal);
  assertAuth();
  requirePermission("mempool:read");
  try {
    const res = await fetch(`${INFERENCE_API_BASE}/api/demos`, { signal });
    if (res.ok) {
      const data = (await res.json()) as { demos?: DemoExample[] };
      if (Array.isArray(data.demos) && data.demos.length > 0) {
        return data.demos;
      }
    }
  } catch {
    return FALLBACK_DEMOS.map((d) => ({ ...d }));
  }
  return FALLBACK_DEMOS.map((d) => ({ ...d }));
}

export async function analyzeBytecode(
  bytecode: string,
  contractId?: string | null,
  signal?: AbortSignal,
): Promise<BytecodeAnalysisReport> {
  await gate(signal);
  assertAuth();
  requirePermission("mempool:read");
  try {
    const res = await fetch(`${INFERENCE_API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bytecode, contract_id: contractId ?? null }),
      signal,
    });
    if (res.ok) {
      return (await res.json()) as BytecodeAnalysisReport;
    }
  } catch {
    const text = (bytecode || "").trim();
    if (!text || text === "0x" || text === "0X") {
      return {
        contract_id: contractId,
        validation: { ok: false, errors: ["bytecode is empty"] },
        limitations: [
          "Local Python inference server (http://127.0.0.1:8000) is offline; validated input format locally.",
        ],
      };
    }
    if (text.includes("__")) {
      return {
        contract_id: contractId,
        validation: {
          ok: false,
          errors: ["unlinked library placeholder in runtime bytecode"],
        },
        limitations: [
          "Contracts containing unlinked Solidity library placeholders (__$...$__ or __Lib__) cannot be executed or featurized until linked.",
        ],
      };
    }
    const clean = text.startsWith("0x") || text.startsWith("0X") ? text.slice(2) : text;
    if (clean.length % 2 !== 0 || !/^[0-9a-fA-F]+$/.test(clean)) {
      return {
        contract_id: contractId,
        validation: {
          ok: false,
          errors: [clean.length % 2 !== 0 ? "bytecode hex length is odd" : "bytecode is not valid hex"],
        },
        limitations: [
          "Input failed static EVM runtime bytecode validation; disassembly, CFG, and ML inference were not executed.",
        ],
      };
    }
    return {
      contract_id: contractId,
      validation: {
        ok: false,
        errors: [
          "Python inference backend (http://127.0.0.1:8000) is not running. Start: py -3.13 scripts/phase5_smoke_baseline.py --serve",
        ],
      },
      limitations: [
        "Start the unified Python inference backend to run full disassembly, CFG extraction, 159-d featurization, and model prediction.",
      ],
    };
  }
  throw new ApiError("UNAVAILABLE", "Inference request failed.", 503);
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
