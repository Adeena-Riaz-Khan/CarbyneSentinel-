import {
  collection,
  doc,
  getDoc,
  getDocs,
  setDoc,
  type Firestore,
} from "firebase/firestore";
import type {
  BenchmarkDoc,
  GlobalStats,
  SettingsDoc,
  Transaction,
} from "../contracts/domain";
import { ApiError } from "../contracts/errors";
import { PENDING_FEED_TOTAL } from "../contracts/grids";
import { FS } from "../lib/collections";
import { getFirebaseDb } from "../lib/firebaseApp";
import { validateSettingsPatch } from "../validation/forms";

function db(): Firestore {
  return getFirebaseDb();
}

function missing(path: string): never {
  throw new ApiError(
    "NOT_FOUND",
    `Missing Firestore doc: ${path}. Run npm run emulators:seed`,
    404,
  );
}

export async function fsGetStats(): Promise<GlobalStats> {
  const snap = await getDoc(doc(db(), FS.stats.col, FS.stats.doc));
  if (!snap.exists()) missing(`${FS.stats.col}/${FS.stats.doc}`);
  const data = snap.data() as GlobalStats;
  return { ...data, pendingTotal: data.pendingTotal ?? PENDING_FEED_TOTAL };
}

export async function fsGetTransactions(): Promise<Transaction[]> {
  const snap = await getDocs(collection(db(), FS.transactions));
  return snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<Transaction, "id">) }));
}

export async function fsGetBenchmarks(): Promise<BenchmarkDoc> {
  const snap = await getDoc(doc(db(), FS.benchmarks.col, FS.benchmarks.doc));
  if (!snap.exists()) missing(`${FS.benchmarks.col}/${FS.benchmarks.doc}`);
  const raw = snap.data() as BenchmarkDoc & {
    matrixRows?: { cells: number[] }[];
  };
  const matrix =
    raw.matrix ??
    raw.matrixRows?.map((r) => r.cells) ??
    [];
  const { matrixRows: _rows, ...rest } = raw as typeof raw & {
    matrixRows?: unknown;
  };
  return { ...rest, matrix } as BenchmarkDoc;
}

export async function fsGetSettings(): Promise<SettingsDoc> {
  const snap = await getDoc(doc(db(), FS.settings.col, FS.settings.doc));
  if (!snap.exists()) missing(`${FS.settings.col}/${FS.settings.doc}`);
  return snap.data() as SettingsDoc;
}

export async function fsPatchSettings(
  patch: Partial<SettingsDoc>,
): Promise<SettingsDoc> {
  const current = await fsGetSettings();
  const parsed = validateSettingsPatch(patch, current);
  if (!parsed.ok) {
    throw new ApiError("VALIDATION", parsed.message, 400, parsed.errors);
  }
  const next = { ...current, ...parsed.data };
  await setDoc(doc(db(), FS.settings.col, FS.settings.doc), next, { merge: true });
  return next;
}
