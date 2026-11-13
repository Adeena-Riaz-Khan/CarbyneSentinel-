import type {
  AnalysisRun,
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
  analysisRuns: AnalysisRun[];
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
  analysisRuns: [],
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
  memory.analysisRuns = [];
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
  let report: BytecodeAnalysisReport | null = null;
  try {
    const res = await fetch(`${INFERENCE_API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bytecode, contract_id: contractId ?? null }),
      signal,
    });
    if (res.ok) {
      report = (await res.json()) as BytecodeAnalysisReport;
    }
  } catch {
    const text = (bytecode || "").trim();
    if (!text || text === "0x" || text === "0X") {
      report = {
        contract_id: contractId,
        validation: { ok: false, errors: ["bytecode is empty"] },
        limitations: [
          "Local Python inference server (http://127.0.0.1:8000) is offline; validated input format locally.",
        ],
      };
    } else if (text.includes("__")) {
      report = {
        contract_id: contractId,
        validation: {
          ok: false,
          errors: ["unlinked library placeholder in runtime bytecode"],
        },
        limitations: [
          "Contracts containing unlinked Solidity library placeholders (__$...$__ or __Lib__) cannot be executed or featurized until linked.",
        ],
      };
    } else {
      const clean = text.startsWith("0x") || text.startsWith("0X") ? text.slice(2) : text;
      if (clean.length % 2 !== 0 || !/^[0-9a-fA-F]+$/.test(clean)) {
        report = {
          contract_id: contractId,
          validation: {
            ok: false,
            errors: [clean.length % 2 !== 0 ? "bytecode hex length is odd" : "bytecode is not valid hex"],
          },
          limitations: [
            "Input failed static EVM runtime bytecode validation; disassembly, CFG, and ML inference were not executed.",
          ],
        };
      } else {
        report = {
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
    }
  }
  if (!report) {
    throw new ApiError("UNAVAILABLE", "Inference request failed.", 503);
  }
  void persistAnalysisRun(bytecode, report);
  return report;
}

export async function listAnalysisRuns(signal?: AbortSignal): Promise<AnalysisRun[]> {
  await gate(signal);
  assertAuth();
  requirePermission("diagnostics:read");
  if (isFirestoreDataEnabled()) return fs.fsListAnalysisRuns();
  return memory.analysisRuns.map((r) => ({ ...r, topFeatures: r.topFeatures.map((f) => ({ ...f })) }));
}

export type IncidentExportResult = {
  filename: string;
  relativePath: string | null;
  savedToRepo: boolean;
};

export async function downloadIncidentExport(
  format: "csv" | "json",
): Promise<IncidentExportResult> {
  assertAuth();
  requirePermission("analytics:export");
  const [runs, txs] = await Promise.all([listAnalysisRuns(), getTransactions()]);
  const content =
    format === "json"
      ? JSON.stringify(
          {
            exportedAt: new Date().toISOString(),
            analysisRuns: runs,
            mempoolTransactions: txs,
          },
          null,
          2,
        )
      : runs.length > 0
        ? analysisRunsToCsv(runs)
        : transactionsToCsv(txs);
  const mime = format === "json" ? "application/json" : "text/csv;charset=utf-8";
  const saved = await saveExportToRepo(format, content);
  const filename = saved?.filename ?? fallbackExportFilename(format);
  triggerDownload(filename, content, mime);
  return {
    filename,
    relativePath: saved?.relative_path ?? null,
    savedToRepo: Boolean(saved?.relative_path),
  };
}

function fallbackExportFilename(format: "csv" | "json"): string {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  return `incidents_${stamp}.${format}`;
}

async function saveExportToRepo(
  format: "csv" | "json",
  content: string,
): Promise<{ filename: string; relative_path: string } | null> {
  try {
    const res = await fetch(`${INFERENCE_API_BASE}/api/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, content }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      ok?: boolean;
      filename?: string;
      relative_path?: string;
    };
    if (!data.ok || !data.filename || !data.relative_path) return null;
    return { filename: data.filename, relative_path: data.relative_path };
  } catch {
    return null;
  }
}

async function persistAnalysisRun(
  bytecode: string,
  report: BytecodeAnalysisReport,
): Promise<void> {
  try {
    const session = getCurrentSession();
    if (!session) return;
    const run = await buildAnalysisRun(bytecode, report, session.user.id, session.user.email);
    if (isFirestoreDataEnabled()) {
      await fs.fsSaveAnalysisRun(run);
      return;
    }
    memory.analysisRuns.unshift(run);
    if (memory.analysisRuns.length > 500) memory.analysisRuns.length = 500;
  } catch {
    /* best-effort — never block inference UI */
  }
}

async function buildAnalysisRun(
  bytecode: string,
  report: BytecodeAnalysisReport,
  userId: string,
  userEmail: string,
): Promise<AnalysisRun> {
  const text = (bytecode || "").trim();
  const pred = report.prediction;
  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    userId,
    userEmail,
    contractId: report.contract_id ?? null,
    bytecodeSha256: await sha256Hex(text),
    bytecodeSizeBytes: report.validation.bytecode_size_bytes ?? Math.ceil(text.replace(/^0x/i, "").length / 2),
    validationOk: report.validation.ok,
    validationErrors: report.validation.errors.slice(0, 8),
    predictedClass: pred?.predicted_class ?? null,
    confidence: pred?.confidence ?? null,
    featureGroup: pred?.feature_group ?? null,
    featureCount: pred?.feature_count ?? null,
    estimatorType: pred?.estimator_type ?? null,
    modelArtifact: pred?.artifact_path ?? null,
    instructionCount: report.disassembly?.instruction_count ?? report.validation.instruction_count ?? null,
    cfgBlockCount: report.cfg?.block_count ?? null,
    cfgResolvedJumps: report.cfg?.resolved_jumps ?? null,
    cfgUnresolvedJumps: report.cfg?.unresolved_jumps ?? null,
    topFeatures: (pred?.top_feature_evidence ?? []).slice(0, 5).map((f) => ({
      feature: f.feature,
      contribution: f.contribution,
      direction: f.direction,
    })),
    limitations: (report.limitations ?? []).slice(0, 6),
  };
}

async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text.toLowerCase());
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function csvEscape(value: string | number | boolean | null | undefined): string {
  const s = value == null ? "" : String(value);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function analysisRunsToCsv(runs: AnalysisRun[]): string {
  const header = [
    "id",
    "createdAt",
    "userEmail",
    "contractId",
    "bytecodeSha256",
    "bytecodeSizeBytes",
    "validationOk",
    "predictedClass",
    "confidence",
    "featureGroup",
    "featureCount",
    "estimatorType",
    "modelArtifact",
    "instructionCount",
    "cfgBlockCount",
  ];
  const lines = [header.join(",")];
  for (const r of runs) {
    lines.push(
      [
        r.id,
        r.createdAt,
        r.userEmail,
        r.contractId,
        r.bytecodeSha256,
        r.bytecodeSizeBytes,
        r.validationOk,
        r.predictedClass,
        r.confidence,
        r.featureGroup,
        r.featureCount,
        r.estimatorType,
        r.modelArtifact,
        r.instructionCount,
        r.cfgBlockCount,
      ]
        .map(csvEscape)
        .join(","),
    );
  }
  return lines.join("\n");
}

function transactionsToCsv(txs: Transaction[]): string {
  const header = [
    "id",
    "hash",
    "contractName",
    "contractAddress",
    "gasPrice",
    "fingerprintScore",
    "structuralScore",
    "intent",
    "action",
  ];
  const lines = [header.join(",")];
  for (const t of txs) {
    lines.push(
      [
        t.id,
        t.hash,
        t.contractName,
        t.contractAddress,
        t.gasPrice,
        t.fingerprintScore,
        t.structuralScore,
        t.intent,
        t.action,
      ]
        .map(csvEscape)
        .join(","),
    );
  }
  return lines.join("\n");
}

function triggerDownload(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
