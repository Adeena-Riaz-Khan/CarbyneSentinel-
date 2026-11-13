/** Firestore collection / document paths for seeds → live data later. */
export const FS = {
  stats: { col: "stats", doc: "global" },
  settings: { col: "settings", doc: "pipeline" },
  benchmarks: { col: "benchmarks", doc: "latest" },
  transactions: "transactions",
  analysisRuns: "analysis_runs",
  users: "users",
} as const;
