/** Domain shapes shared by UI, services, and tests. */

export type TxAction = "ALLOW" | "FLAG" | "BLOCK";
export type AgentStatus = "ACTIVE" | "FROZEN";
export type AgentColor = "blue" | "purple";

export type Transaction = {
  id: string;
  hash: string;
  contractName: string;
  contractAddress: string;
  gasPrice: number;
  fingerprintScore: number;
  structuralScore: number;
  intent: string;
  action: TxAction;
};

export type AgentRecentTx = {
  label: string;
  amount: string;
  status: "Allowed" | "Blocked";
  ago: string;
};

export type Agent = {
  id: string;
  initials: string;
  name: string;
  description: string;
  status: AgentStatus;
  spent: number;
  limit: number;
  color: AgentColor;
  recentTxs: AgentRecentTx[];
};

export type InterceptAlert = {
  id: string;
  agentName: string;
  title: string;
  blockedAgo: string;
  expectedRecipient: string;
  actualRecipient: string;
  explanation: string;
  attemptedValue: string;
  confidence: number;
};

export type GlobalStats = {
  activeAgents: number;
  interceptedCalls: number;
  protectedVolume: string;
  totalCalls: number;
  avgLatencyMs: number;
  throughputTps: number;
  bloomPruneRate: number;
  allowed: number;
  flagged: number;
  blocked: number;
  blockHeight: number;
  pendingTotal?: number;
};

export type SettingsDoc = {
  fingerprintWeight: number;
  gcnWeight: number;
  llmWeight: number;
  timeoutMs: number;
  failClosed: boolean;
  adaptiveRouting: boolean;
  webhookUrl: string;
  minSeverity: string;
  authType: string;
  archiveRecords: number;
  archiveSizeMb: number;
};

export type BenchmarkDoc = {
  dataset: string;
  lastRun: string;
  otherToolPct: number;
  ourModelPct: number;
  deltaPp: number;
  f1Pct: number;
  matrix: number[][];
  latencyStages: { stage: string; ms: number }[];
  totalMedianMs: number;
};

export type ProfileUser = {
  initials: string;
  wallet: string;
  role: string;
  network: string;
};
