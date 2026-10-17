/** Column definitions for heavy grids — single source for UI + tests. */

export type GridColumn = {
  id: string;
  header: string;
  field?: string;
  widthHint?: string;
};

export const MEMPOOL_COLUMNS: readonly GridColumn[] = [
  { id: "hash", header: "Tx hash", field: "hash" },
  { id: "contract", header: "Target contract", field: "contractName" },
  { id: "gas", header: "Gas price", field: "gasPrice" },
  { id: "fingerprint", header: "Fingerprint", field: "fingerprintScore" },
  { id: "structural", header: "Structural", field: "structuralScore" },
  { id: "intent", header: "Semantic intent", field: "intent" },
  { id: "action", header: "Action", field: "action" },
  { id: "inspect", header: "Inspect" },
] as const;

export const AGENT_TX_COLUMNS: readonly GridColumn[] = [
  { id: "status", header: "Status", field: "status" },
  { id: "label", header: "Description", field: "label" },
  { id: "ago", header: "When", field: "ago" },
  { id: "amount", header: "Amount", field: "amount" },
] as const;

/** Seed / API meta for feed footer (BR-MON-1). */
export const PENDING_FEED_TOTAL = 1289;
