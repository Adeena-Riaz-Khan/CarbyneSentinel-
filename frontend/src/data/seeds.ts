export type Transaction = {
  id: string;
  hash: string;
  contractName: string;
  contractAddress: string;
  gasPrice: number;
  fingerprintScore: number;
  structuralScore: number;
  intent: string;
  action: "ALLOW" | "FLAG" | "BLOCK";
};

export type GlobalStats = {
  totalCalls: number;
  avgLatencyMs: number;
  throughputTps: number;
  bloomPruneRate: number;
  allowed: number;
  flagged: number;
  blocked: number;
  blockHeight: number;
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

export const seedUser = {
  initials: "AS",
  wallet: "0x71F2...8A4C",
  role: "Security Admin",
  network: "Ethereum Mainnet Fork",
};

export const seedStats: GlobalStats = {
  totalCalls: 1852,
  avgLatencyMs: 285,
  throughputTps: 1428,
  bloomPruneRate: 38.2,
  allowed: 1249,
  flagged: 18,
  blocked: 5,
  blockHeight: 19847221,
};

export const seedTransactions: Transaction[] = [
  {
    id: "tx1",
    hash: "0x8a21...2fd9",
    contractName: "Uniswap V3 Router",
    contractAddress: "0xE592...1564",
    gasPrice: 18.2,
    fingerprintScore: 0.08,
    structuralScore: 0.12,
    intent: "DEX arbitrage",
    action: "ALLOW",
  },
  {
    id: "tx2",
    hash: "0x91de...0c44",
    contractName: "USDC Token",
    contractAddress: "0xA0b8...eB48",
    gasPrice: 14.7,
    fingerprintScore: 0.03,
    structuralScore: 0.05,
    intent: "Benign transfer",
    action: "ALLOW",
  },
  {
    id: "tx3",
    hash: "0x3c1b...7a82",
    contractName: "Curve Oracle Pool",
    contractAddress: "0xDc24...B91F",
    gasPrice: 64.1,
    fingerprintScore: 0.91,
    structuralScore: 0.84,
    intent: "Oracle manipulation",
    action: "BLOCK",
  },
  {
    id: "tx4",
    hash: "0xf402...9bc1",
    contractName: "Aave V3 Pool",
    contractAddress: "0x8787...a4E2",
    gasPrice: 32.5,
    fingerprintScore: 0.42,
    structuralScore: 0.61,
    intent: "Flash-loan sequence",
    action: "FLAG",
  },
  {
    id: "tx5",
    hash: "0x712a...4d0e",
    contractName: "Unknown Proxy",
    contractAddress: "0x3fB2...09C7",
    gasPrice: 81.3,
    fingerprintScore: 0.88,
    structuralScore: 0.93,
    intent: "Reentrancy exploit",
    action: "BLOCK",
  },
];

export const seedSettings: SettingsDoc = {
  fingerprintWeight: 25,
  gcnWeight: 32,
  llmWeight: 43,
  timeoutMs: 450,
  failClosed: true,
  adaptiveRouting: true,
  webhookUrl: "https://api.carbyne.internal/v1/incidents",
  minSeverity: "High & critical",
  authType: "Bearer token",
  archiveRecords: 2400000,
  archiveSizeMb: 18.4,
};

export const seedBenchmark: BenchmarkDoc = {
  dataset: "DeFi-intent-bench-v2.6",
  lastRun: "Today, 09:42 UTC",
  otherToolPct: 40,
  ourModelPct: 92,
  deltaPp: 52,
  f1Pct: 88.4,
  matrix: [
    [324, 7, 2],
    [9, 301, 5],
    [1, 12, 339],
  ],
  latencyStages: [
    { stage: "Mem Filter", ms: 2 },
    { stage: "Fingerprint", ms: 12 },
    { stage: "GCN Graph", ms: 85 },
    { stage: "LLM/SLM", ms: 210 },
  ],
  totalMedianMs: 309,
};
