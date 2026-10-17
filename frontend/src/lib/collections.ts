/** Firestore collection / document paths for seeds → live data later. */
export const FS = {
  stats: { col: "stats", doc: "global" },
  settings: { col: "settings", doc: "pipeline" },
  benchmarks: { col: "benchmarks", doc: "latest" },
  intercept: { col: "alerts", doc: "intercept" },
  transactions: "transactions",
  agents: "agents",
  users: "users",
} as const;
