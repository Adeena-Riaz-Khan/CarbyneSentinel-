/** Domain shapes shared by UI, services, and tests. */

export type TxAction = "ALLOW" | "FLAG" | "BLOCK";

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

export type GlobalStats = {
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

export type DemoExample = {
  id: string;
  title: string;
  description: string;
  ground_truth_label: string | null;
  dataset_source: string;
  split: string | null;
  compiler_version: string | null;
  recovery_status: string;
  used_fallback: boolean;
  bytecode: string;
};

export type FeatureEvidence = {
  feature: string;
  raw_value: number;
  z_score: number;
  global_importance?: number | null;
  weight: number;
  contribution: number;
  direction: string;
};

export type BytecodeAnalysisReport = {
  contract_id?: string | null;
  validation: {
    ok: boolean;
    errors: string[];
    bytecode_size_bytes?: number;
    instruction_count?: number;
    truncated_push_at_tail?: boolean;
    unknown_opcode_count?: number;
  };
  disassembly?: {
    instruction_count: number;
    preview_listing: string;
    top_opcode_ratios: { opcode: string; ratio: number }[];
  };
  cfg?: {
    block_count: number;
    edge_count: number;
    resolved_jumps: number;
    unresolved_jumps: number;
    dynamic_jump_note: string;
  };
  fingerprint?: {
    bytecode_size_bytes: number;
    bytecode_shannon_entropy: number;
    opcode_shannon_entropy: number;
    total_instruction_count: number;
    jump_count: number;
    jumpi_count: number;
    total_jump_count: number;
    jump_ratio: number;
    conditional_jump_ratio: number;
    unconditional_jump_ratio: number;
  };
  feature_vector?: {
    dimension: number;
    feature_group?: string;
    feature_names: string[];
    values: number[];
    full_159_dimension?: number;
  };
  prediction?: {
    model_available: boolean;
    artifact_path: string;
    model_name?: string;
    estimator_type?: string;
    feature_group?: string;
    feature_count?: number;
    status: string;
    predicted_class: string | null;
    confidence: number | null;
    class_probabilities: Record<string, number> | null;
    explanation_method?: string | null;
    explanation_note?: string | null;
    top_feature_evidence: FeatureEvidence[];
  };
  limitations: string[];
};

export type AnalysisRun = {
  id: string;
  createdAt: string;
  userId: string;
  userEmail: string;
  contractId: string | null;
  bytecodeSha256: string;
  bytecodeSizeBytes: number;
  validationOk: boolean;
  validationErrors: string[];
  predictedClass: string | null;
  confidence: number | null;
  featureGroup: string | null;
  featureCount: number | null;
  estimatorType: string | null;
  modelArtifact: string | null;
  instructionCount: number | null;
  cfgBlockCount: number | null;
  cfgResolvedJumps: number | null;
  cfgUnresolvedJumps: number | null;
  topFeatures: { feature: string; contribution: number; direction: string }[];
  limitations: string[];
};

