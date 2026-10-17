import type { BenchmarkDoc, Transaction } from "../contracts/domain";

/** BR-AG-1 */
export function agentUtilizationPct(spent: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.min(100, Math.round((spent / limit) * 100));
}

/** BR-AG-1 */
export function agentRemainingPct(spent: number, limit: number): number {
  return Math.max(0, 100 - agentUtilizationPct(spent, limit));
}

/** BR-MON-2 */
export type RiskBand = "safe" | "warning" | "danger";

export function scoreRiskBand(value: number): RiskBand {
  if (value > 0.75) return "danger";
  if (value > 0.4) return "warning";
  return "safe";
}

/** BR-MON-1 */
export function intentToneClass(intent: string): string {
  const t = intent.toLowerCase();
  if (t.includes("benign") || t.includes("transfer")) return "intent safe-intent";
  if (t.includes("arbitrage") || t.includes("dex")) return "intent blue-intent";
  if (t.includes("flash")) return "intent warn-intent";
  return "intent danger-intent";
}

/** BR-SET-1 */
export function fusionWeightSum(w1: number, w2: number, w3: number): number {
  return w1 + w2 + w3;
}

/** BR-AN-1 */
export function latencyTotalMs(stages: BenchmarkDoc["latencyStages"]): number {
  return stages.reduce((acc, s) => acc + s.ms, 0);
}

/** BR-AN-1 */
export function obfuscationDeltaPp(our: number, other: number): number {
  return our - other;
}

/** BR-MON-1 */
export function filterTransactions(
  txs: Transaction[],
  query: string,
  actionFilter: string,
): Transaction[] {
  const q = query.toLowerCase();
  return txs.filter((tx) => {
    const matchesQuery =
      !q ||
      `${tx.hash} ${tx.contractName} ${tx.contractAddress}`.toLowerCase().includes(q);
    const matchesAction = actionFilter === "All risk levels" || tx.action === actionFilter;
    return matchesQuery && matchesAction;
  });
}
