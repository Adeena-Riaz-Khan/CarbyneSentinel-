import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import heroPhoto from "./assets/carbyne-hero-chain-hand.png";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { EmptyState } from "./components/EmptyState";
import { ErrorBanner } from "./components/ErrorBanner";
import { RequirePermission } from "./components/RequirePermission";
import { DataProvider, useData } from "./context/DataContext";
import type { BytecodeAnalysisReport, DemoExample } from "./contracts/domain";
import { PENDING_FEED_TOTAL } from "./contracts/grids";
import {
  filterTransactions,
  intentToneClass,
  scoreRiskBand,
} from "./domain/calculations";
import AuthPage from "./pages/AuthPage";
import {
  analyzeBytecode,
  downloadIncidentExport,
  getDemoExamples,
  listAnalysisRuns,
} from "./services/apiClient";
import { sanitizeSearchQuery } from "./validation/forms";

type Page = "monitor" | "analytics" | "settings" | "auth";
type IconName =
  | "activity"
  | "analytics"
  | "settings"
  | "search"
  | "pause"
  | "play"
  | "shield"
  | "wallet"
  | "alert"
  | "close"
  | "arrow"
  | "copy"
  | "export"
  | "lock"
  | "check"
  | "chevron";

const paths: Record<IconName, ReactNode> = {
  activity: <><path d="M3 12h4l2.2-6 4 12 2.2-6H21" /></>,
  analytics: <><path d="M4 19V9M10 19V5M16 19v-7M22 19V3" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  pause: <><path d="M9 6v12M15 6v12" /></>,
  play: <><path d="m8 5 11 7-11 7Z" /></>,
  shield: <><path d="M12 3 20 6v5c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6l8-3Z" /><path d="m9 12 2 2 4-5" /></>,
  wallet: <><path d="M4 7h15a2 2 0 0 1 2 2v10H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h12" /><path d="M16 12h5v4h-5a2 2 0 0 1 0-4Z" /></>,
  alert: <><path d="M12 3 2.5 20h19L12 3Z" /><path d="M12 9v5M12 17h.01" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  arrow: <><path d="M5 12h14M14 7l5 5-5 5" /></>,
  copy: <><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>,
  export: <><path d="M12 3v12M7 10l5 5 5-5M5 21h14" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
  check: <><path d="m5 12 4 4L19 6" /></>,
  chevron: <><path d="m8 10 4 4 4-4" /></>,
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <svg className="brand-mark" viewBox="0 0 38 38" aria-hidden="true">
        <path d="M19 2.5 33 8v9.2c0 9-6 15.2-14 18.3C11 32.4 5 26.2 5 17.2V8l14-5.5Z" />
        <circle cx="19" cy="18" r="6" />
        <path d="M19 12V8M13.8 21l-3.7 2.2M24.2 21l3.7 2.2" />
      </svg>
      {!compact && <span>Carbyne<span>Sentinel</span></span>}
    </div>
  );
}

function HeroAssetFrame() {
  return (
    <div className="hero-asset-frame">
      <img src={heroPhoto} alt="Wireframe chain link floating above a cybernetic hand" />
    </div>
  );
}

const navItems: { id: Page; label: string; icon: IconName }[] = [
  { id: "monitor", label: "Mempool Monitor", icon: "activity" },
  { id: "analytics", label: "Analytics", icon: "analytics" },
  { id: "settings", label: "Settings", icon: "settings" },
];

function Header({ page, setPage }: { page: Page; setPage: (page: Page) => void }) {
  const { user, stats } = useData();
  const { signOut, can } = useAuth();
  return (
    <header className="topbar">
      <Brand />
      <nav className="nav-tabs">
        {navItems.map((item) => {
          if (item.id === "settings" && !can("settings:read")) return null;
          return (
            <button
              key={item.id}
              className={page === item.id ? "nav-item active" : "nav-item"}
              onClick={() => setPage(item.id)}
              type="button"
            >
              <Icon name={item.icon} size={18} /> {item.label}
            </button>
          );
        })}
      </nav>
      <div className="top-actions">
        <div className="node-status">
          <span className="pulse-dot" />
          <span>
            <b>{user.network}</b>
            <small>Connected — Block {stats?.blockHeight.toLocaleString() ?? "—"}</small>
          </span>
        </div>
        <button
          className="user-chip"
          onClick={() => {
            void signOut().then(() => setPage("auth"));
          }}
          type="button"
          title="Sign out"
        >
          <span className="avatar">{user.initials}</span>
          <span>
            <b>{user.wallet}</b>
            <small>{user.role}</small>
          </span>
          <Icon name="chevron" size={14} />
        </button>
      </div>
    </header>
  );
}

function PageHeading({ eyebrow, title, copy, children }: { eyebrow: string; title: string; copy: string; children?: ReactNode }) {
  return (
    <div className="page-heading">
      <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{copy}</p></div>
      {children && <div className="heading-actions">{children}</div>}
    </div>
  );
}

function Score({ value }: { value: number }) {
  const level = scoreRiskBand(value);
  return <div className="score-cell"><span className={`score-dot ${level}`} />{value.toFixed(2)}<span className="mini-track"><i className={level} style={{ width: `${value * 100}%` }} /></span></div>;
}

function Metrics() {
  const { stats } = useData();
  if (!stats) return null;
  const metrics = [
    { label: "Average latency", value: String(stats.avgLatencyMs), unit: "ms", foot: "SLA target <500ms", trend: "+12.4%", cls: "safe" },
    { label: "Ingestion throughput", value: stats.throughputTps.toLocaleString(), unit: "tx/s", foot: "Live mempool feed", trend: "LIVE", cls: "blue" },
    { label: "Bloom pruning rate", value: String(stats.bloomPruneRate), unit: "%", foot: "Noise filtered pre-GCN", trend: "OPTIMAL", cls: "amber" },
  ];
  return (
    <div className="metrics-grid">
      {metrics.map((m) => (
        <article className="metric-card" key={m.label}>
          <div className="metric-top"><span>{m.label}</span><span className={`micro-badge ${m.cls}`}>{m.trend}</span></div>
          <div className="metric-value">{m.value}<small>{m.unit}</small></div>
          <div className="metric-foot">{m.foot}</div>
        </article>
      ))}
      <article className="metric-card action-card">
        <div className="metric-top"><span>Real-time actions</span><span className="live-label"><i />LIVE</span></div>
        <div className="action-counts">
          <div><b>{stats.allowed.toLocaleString()}</b><small>Allowed</small></div>
          <div><b>{stats.flagged}</b><small>Flagged</small></div>
          <div><b>{stats.blocked}</b><small>Blocked</small></div>
        </div>
        <div className="stacked-bar"><i /><i /><i /></div>
      </article>
    </div>
  );
}

function Monitor({ openInspector }: { openInspector: () => void }) {
  const { transactions, stats, error, clearError } = useData();
  const { can } = useAuth();
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState("All risk levels");
  const [query, setQuery] = useState("");
  const shown = useMemo(
    () => filterTransactions(transactions, sanitizeSearchQuery(query), filter),
    [filter, query, transactions],
  );
  return (
    <>
      {error ? <ErrorBanner message={error} onDismiss={clearError} /> : null}
      <section className="monitor-hero">
        <div className="monitor-hero-copy">
          <div className="hero-status">
            <span className="pulse-dot" /> PIPELINE LIVE <b>{stats?.avgLatencyMs ?? "—"} MS AVG</b>
          </div>
          <div className="eyebrow">REAL-TIME THREAT OPERATIONS</div>
          <h1>Live Mempool <span>Monitor</span></h1>
          <p>Bytecode fingerprinting, control-flow analysis, and vulnerability classification for pending transactions.</p>
          <Metrics />
        </div>
        <div className="monitor-art-stage">
          <HeroAssetFrame />
        </div>
      </section>
      <section className="panel feed-panel">
        <div className="panel-header">
          <div>
            <div className="title-row">
              <h2>Pending Transaction Feed</h2>
              <span className="live-label"><i /> STREAMING</span>
            </div>
            <p>Ranked by threat confidence for review and inspection</p>
          </div>
          <div className="feed-controls">
            <label className="search-box">
              <Icon name="search" size={16} />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search hash or address" />
            </label>
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option>All risk levels</option>
              <option>ALLOW</option>
              <option>FLAG</option>
              <option>BLOCK</option>
            </select>
            <button className={paused ? "btn secondary active" : "btn secondary"} onClick={() => setPaused(!paused)}>
              <Icon name={paused ? "play" : "pause"} size={15} />
              {paused ? "Resume" : "Pause stream"}
            </button>
            <RequirePermission permission="mempool:simulate">
              <button className="btn primary simulate-btn" onClick={openInspector} type="button">
                <Icon name="alert" size={15} />Simulate exploit
              </button>
            </RequirePermission>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tx hash</th>
                <th>Target contract</th>
                <th>Gas price</th>
                <th>Fingerprint</th>
                <th>Structural</th>
                <th>Semantic intent</th>
                <th>Action</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {shown.map((tx) => (
                <tr key={tx.id} className={tx.action === "BLOCK" ? "risky-row" : ""}>
                  <td>
                    <button className="hash-link" onClick={openInspector} type="button">
                      {tx.hash}
                      <Icon name="copy" size={13} />
                    </button>
                  </td>
                  <td>
                    <b>{tx.contractName}</b>
                    <small>{tx.contractAddress}</small>
                  </td>
                  <td>
                    {tx.gasPrice} <small>Gwei</small>
                  </td>
                  <td><Score value={tx.fingerprintScore} /></td>
                  <td><Score value={tx.structuralScore} /></td>
                  <td><span className={intentToneClass(tx.intent)}>{tx.intent}</span></td>
                  <td>
                    <span className={`action-badge ${tx.action.toLowerCase()}`}>
                      {tx.action === "ALLOW" && <Icon name="check" size={12} />}
                      {tx.action}
                    </span>
                  </td>
                  <td>
                    <button className="inspect-btn" onClick={openInspector} type="button">
                      Inspect <Icon name="arrow" size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {shown.length === 0 && (
            <EmptyState
              title="No pending transactions match this filter."
              detail={transactions.length === 0 ? "Waiting for mempool data." : undefined}
            />
          )}
        </div>
        <div className="table-footer">
          <span>
            Showing {shown.length} of {stats?.pendingTotal ?? PENDING_FEED_TOTAL} pending transactions
          </span>
          <span>
            Last updated just now · <b>{paused ? "Paused" : "Auto-refresh 500ms"}</b>
            {!can("mempool:simulate") ? " · View only" : ""}
          </span>
        </div>
      </section>
    </>
  );
}

function Inspector({ close }: { close: () => void }) {
  const [demos, setDemos] = useState<DemoExample[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [bytecode, setBytecode] = useState<string>("");
  const [report, setReport] = useState<BytecodeAnalysisReport | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  useEffect(() => {
    void getDemoExamples().then((list) => {
      setDemos(list);
      if (list.length > 0) {
        setSelectedId(list[0].id);
        setBytecode(list[0].bytecode);
        setBusy(true);
        void analyzeBytecode(list[0].bytecode, list[0].id)
          .then((r) => setReport(r))
          .finally(() => setBusy(false));
      }
    });
  }, []);

  const currentDemo = demos.find((d) => d.id === selectedId) ?? null;

  const runAnalysis = (bc: string, cid?: string | null) => {
    setBusy(true);
    void analyzeBytecode(bc, cid)
      .then((r) => setReport(r))
      .finally(() => setBusy(false));
  };

  const valOk = report?.validation.ok ?? false;
  const fp = report?.fingerprint;
  const cfg = report?.cfg;
  const pred = report?.prediction;
  const dis = report?.disassembly;
  const confPct = pred?.confidence != null ? Math.round(pred.confidence * 100) : 0;

  return (
    <div className="modal-backdrop" onMouseDown={close}>
      <section className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className={valOk ? "eyebrow" : "eyebrow danger-text"}>
              {valOk ? "LIVE BYTECODE INFERENCE · PHASE 5 PIPELINE" : "VALIDATION REJECTED · INPUT CHECK"}
            </div>
            <h2>Runtime Bytecode Security Analyzer</h2>
            <div className="tx-meta">
              <code>{report?.contract_id || "custom_runtime_bytecode"}</code>
              {currentDemo?.ground_truth_label && (
                <span>Dataset label: {currentDemo.ground_truth_label} ({currentDemo.dataset_source}, {currentDemo.split})</span>
              )}
              {currentDemo?.used_fallback && (
                <span>Fallback compiler ({currentDemo.compiler_version})</span>
              )}
            </div>
          </div>
          <button className="icon-btn" onClick={close}><Icon name="close" /></button>
        </div>

        <div style={{ padding: "12px 18px 0", display: "grid", gap: "8px" }}>
          <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={selectedId}
              onChange={(e) => {
                const id = e.target.value;
                setSelectedId(id);
                const found = demos.find((d) => d.id === id);
                if (found) {
                  setBytecode(found.bytecode);
                  runAnalysis(found.bytecode, found.id);
                }
              }}
              style={{ flex: 1, height: "35px", border: "1px solid #303139", borderRadius: "7px", background: "#0b0b0e", padding: "0 10px", fontSize: "10px" }}
            >
              {demos.map((d) => (
                <option key={d.id} value={d.id}>{d.title}</option>
              ))}
              <option value="CUSTOM">Custom pasted runtime bytecode</option>
            </select>
            <button
              className="btn primary"
              type="button"
              disabled={busy}
              onClick={() => runAnalysis(bytecode, selectedId === "CUSTOM" ? null : selectedId)}
            >
              <Icon name="play" size={14} /> {busy ? "Analyzing…" : "Analyze bytecode"}
            </button>
          </div>
          {currentDemo && (
            <small style={{ color: "#8994a7", fontSize: "9px" }}>{currentDemo.description}</small>
          )}
          <textarea
            value={bytecode}
            onChange={(e) => {
              setSelectedId("CUSTOM");
              setBytecode(e.target.value);
            }}
            placeholder="Paste EVM runtime bytecode (0x...)"
            rows={3}
            style={{ width: "100%", border: "1px solid #232f40", background: "#080c12", borderRadius: "7px", padding: "8px", fontSize: "9px", fontFamily: "JetBrains Mono, monospace", color: "#c6ced9", resize: "vertical" }}
          />
        </div>

        {report && !valOk && (
          <div style={{ margin: "12px 18px", padding: "12px", border: "1px solid rgba(239,68,68,.35)", background: "rgba(239,68,68,.08)", borderRadius: "8px" }}>
            <b style={{ color: "#f27575", fontSize: "11px", display: "block" }}>Input Validation Errors</b>
            {report.validation.errors.map((err, i) => (
              <p key={i} style={{ color: "#ffb4b4", fontSize: "10px", marginTop: "4px" }}>• {err}</p>
            ))}
          </div>
        )}

        <div className="code-grid">
          <div>
            <div className="code-label">
              <span>Disassembly preview</span>
              <span>{dis ? `${dis.instruction_count} instructions (${report?.validation.bytecode_size_bytes ?? 0} bytes)` : "No instructions"}</span>
            </div>
            <pre style={{ margin: 0, maxHeight: "110px", overflow: "auto", fontSize: "8px", color: "#9ca8b9" }}>
              {dis?.preview_listing || "Validation failed — disassembly not executed."}
            </pre>
          </div>
          <div>
            <div className="code-label">
              <span>Top opcode frequency ratios (145-d vocabulary)</span>
              <span>Unknown bytes: {report?.validation.unknown_opcode_count ?? 0}</span>
            </div>
            <code style={{ display: "block", lineHeight: 1.7 }}>
              {dis?.top_opcode_ratios.map((o) => `${o.opcode}: ${(o.ratio * 100).toFixed(1)}%`).join(" · ") || "—"}
            </code>
          </div>
        </div>

        <div className="signal-grid">
          <article className="signal-card fingerprint">
            <div className="signal-title"><span className="signal-index">01</span><div><h3>Fingerprint v0</h3><p>Entropy & jump ratios (9 core + 5 extra)</p></div><span className="signal-ok"><Icon name="check" size={13} /></span></div>
            <div className="big-score"><span>Byte Shannon entropy</span><b>{fp ? fp.bytecode_shannon_entropy.toFixed(2) : "—"}</b></div>
            <div className="meter"><i style={{ width: `${fp ? Math.min(100, (fp.bytecode_shannon_entropy / 8) * 100) : 0}%` }} /></div>
            <dl>
              <div><dt>Opcode entropy</dt><dd>{fp ? fp.opcode_shannon_entropy.toFixed(3) : "—"}</dd></div>
              <div><dt>Jump ratio (JUMP+JUMPI)</dt><dd>{fp ? `${(fp.jump_ratio * 100).toFixed(2)}%` : "—"}</dd></div>
              <div><dt>Conditional / Uncond.</dt><dd>{fp ? `${fp.jumpi_count} / ${fp.jump_count}` : "—"}</dd></div>
              <div><dt>Tail truncated PUSH</dt><dd>{report?.validation.truncated_push_at_tail ? "Yes (CBOR tail)" : "No"}</dd></div>
            </dl>
          </article>

          <article className="signal-card structural">
            <div className="signal-title"><span className="signal-index">02</span><div><h3>Basic-Block CFG</h3><p>Static control-flow graph recovery</p></div><span className="signal-ok"><Icon name="check" size={13} /></span></div>
            <div className="big-score"><span>Basic blocks / edges</span><b>{cfg ? `${cfg.block_count} / ${cfg.edge_count}` : "—"}</b></div>
            <dl>
              <div><dt>Resolved static jumps</dt><dd>{cfg ? cfg.resolved_jumps : "—"}</dd></div>
              <div><dt>Unresolved dynamic jumps</dt><dd>{cfg ? cfg.unresolved_jumps : "—"}</dd></div>
            </dl>
            <div className="explanation" style={{ marginTop: "10px" }}>
              <span>Dynamic jump accounting</span>
              <p>{cfg?.dynamic_jump_note || "CFG resolves immediate PUSH+JUMP/JUMPI targets and explicitly tracks stack-computed jumps."}</p>
            </div>
          </article>

          <article className="signal-card semantic">
            <div className="signal-title">
              <span className="signal-index">03</span>
              <div>
                <h3>ML Vulnerability Classifier</h3>
                <p>{pred?.feature_count ?? 155}-d {pred?.feature_group ?? "pruned155"} ({pred?.estimator_type ?? "GradientBoostingClassifier"})</p>
              </div>
              <span className="signal-ok"><Icon name="check" size={13} /></span>
            </div>
            <div className="intent-box">
              <span>Predicted vulnerability class (9-class ranking)</span>
              <b>{pred?.model_available ? (pred.predicted_class ?? "—") : "Model artifact unavailable"}</b>
              {pred?.confidence != null && <em>{(pred.confidence * 100).toFixed(1)}% top class prob.</em>}
            </div>
            {pred?.class_probabilities && (
              <dl style={{ marginTop: "8px" }}>
                {Object.entries(pred.class_probabilities)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([cls, prob]) => (
                    <div key={cls}>
                      <dt>Prob ({cls})</dt>
                      <dd>{(prob * 100).toFixed(1)}%</dd>
                    </div>
                  ))}
              </dl>
            )}
            <div className="explanation">
              <span>Global GB feature importance & contract z-score</span>
              {pred?.model_available && pred.top_feature_evidence.length > 0 ? (
                <>
                  <dl style={{ marginTop: "6px" }}>
                    {pred.top_feature_evidence.slice(0, 5).map((ev) => (
                      <div key={ev.feature}>
                        <dt>{ev.feature} (val={ev.raw_value}, z={ev.z_score})</dt>
                        <dd>imp={(ev.global_importance ?? ev.weight).toFixed(3)}</dd>
                      </div>
                    ))}
                  </dl>
                  {pred.explanation_note && (
                    <p style={{ fontSize: "8px", marginTop: "6px" }}>{pred.explanation_note}</p>
                  )}
                </>
              ) : (
                <p>Model artifact {pred?.artifact_path || "phase5_model_gb_pruned155.joblib"} is missing or incompatible.</p>
              )}
            </div>
          </article>
        </div>

        <div style={{ padding: "0 18px 12px" }}>
          <div className="explanation">
            <span>Explicit limitations & evaluation caveats (not proof of exploitability)</span>
            {report?.limitations.map((lim, i) => (
              <p key={i} style={{ marginTop: "4px" }}>• {lim}</p>
            ))}
          </div>
        </div>

        <footer className="modal-footer">
          <div className="risk-gauge">
            <div className="gauge"><span>{pred?.confidence != null ? `${confPct}%` : `${pred?.feature_count ?? 155}d`}</span></div>
            <div>
              <span>Model & artifact status</span>
              <b>{pred?.model_available ? `${pred.model_name || "StandardScaler+GB"} · ${pred.artifact_path}` : "STATIC ANALYSIS ONLY"}</b>
              <small>Class probability ranking — not formal verification or clean/malicious certification</small>
            </div>
          </div>
          <div className="decision">
            <button className="btn secondary" onClick={close} type="button">Close analyzer</button>
          </div>
        </footer>
      </section>
    </div>
  );
}

function Analytics() {
  const { benchmarks } = useData();
  if (!benchmarks) return null;
  const labels = ["Transfer", "Arbitrage", "Exploit"];
  const matrixClasses = ["m90", "m80", "m100"];
  return (
    <>
      <PageHeading eyebrow="MODEL RESEARCH & VALIDATION" title="Benchmark Analytics" copy="Validation metrics, classification quality, and pipeline latency for the CarbyneSentinel detector.">
        <button className="btn secondary"><Icon name="export" size={15} />Export report</button>
      </PageHeading>
      <div className="analytics-meta">
        <span><i />Evaluation set complete</span>
        <span>Dataset: {benchmarks.dataset}</span>
        <span>Last run: {benchmarks.lastRun}</span>
      </div>
      <div className="analytics-grid">
        <article className="chart-card wide">
          <div className="chart-head">
            <div>
              <span>ADVERSARIAL ROBUSTNESS</span>
              <h2>Obfuscation Survival Rate</h2>
              <p>Detection accuracy after progressive bytecode manipulation</p>
            </div>
            <span className="chart-delta">+{benchmarks.deltaPp} pp</span>
          </div>
          <div className="bar-chart">
            <div className="axis"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div>
            <div className="bars">
              <div><i style={{ height: `${benchmarks.otherToolPct}%` }}><b>{benchmarks.otherToolPct}%</b></i><span>Other static tool</span></div>
              <div><i className="featured" style={{ height: `${benchmarks.ourModelPct}%` }}><b>{benchmarks.ourModelPct}%</b></i><span>Canyon (our) model</span></div>
            </div>
          </div>
          <div className="chart-note">
            <Icon name="shield" size={16} />
            <span><b>2.3× greater resilience</b> under control-flow flattening and junk insertion attacks.</span>
          </div>
        </article>
        <article className="chart-card">
          <div className="chart-head">
            <div>
              <span>CLASSIFICATION QUALITY</span>
              <h2>DeFi Intent Matrix</h2>
              <p>1,000 labeled transactions</p>
            </div>
            <span className="micro-badge blue">{benchmarks.f1Pct}% F1</span>
          </div>
          <div className="matrix-wrap">
            <span className="vertical-label">ACTUAL CLASS</span>
            <div className="matrix">
              <span />
              {labels.map((l) => <small key={l}>{l}</small>)}
              {benchmarks.matrix.map((row, ri) => (
                <Fragment key={labels[ri]}>
                  <b>{labels[ri]}</b>
                  {row.map((cell, ci) => (
                    <i key={`${ri}-${ci}`} className={ri === ci ? matrixClasses[ri] : undefined}>{cell}</i>
                  ))}
                </Fragment>
              ))}
            </div>
            <span className="horizontal-label">PREDICTED CLASS</span>
          </div>
        </article>
        <article className="chart-card full">
          <div className="chart-head">
            <div>
              <span>PIPELINE PERFORMANCE</span>
              <h2>Pipeline Latency Breakdown</h2>
              <p>Median stage latency across 10,000 pending transactions</p>
            </div>
            <div className="total-latency">
              <span>TOTAL MEDIAN</span>
              <b>{benchmarks.totalMedianMs}ms</b>
              <small>38% under SLA</small>
            </div>
          </div>
          <div className="histogram">
            <div className="histogram-y-title">Execution time (ms)</div>
            <div className="histogram-y-axis">{[500, 400, 300, 200, 100, 0].map((value) => <span key={value}>{value}</span>)}</div>
            <div className="histogram-plot">
              <div className="sla-line"><span>500MS SLA TARGET</span></div>
              <div className="hist-grid">{[400, 300, 200, 100, 0].map((value) => <i key={value} />)}</div>
              <div className="hist-bars">
                {benchmarks.latencyStages.map((s) => (
                  <div className="hist-column" key={s.stage}>
                    <div className="hist-bar-wrap">
                      <b>{s.ms}ms</b>
                      <i style={{ height: `${(s.ms / 500) * 100}%` }} />
                    </div>
                    <span>{s.stage}<small>[{s.ms}ms]</small></span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </article>
      </div>
    </>
  );
}

function Settings() {
  const { settings, saveSettings, error, clearError } = useData();
  const { can } = useAuth();
  const [tab, setTab] = useState("Pipeline parameters");
  const [saved, setSaved] = useState(false);
  const [weights, setWeights] = useState([25, 32, 43, 450]);
  const [runCount, setRunCount] = useState(0);
  const [exporting, setExporting] = useState<"csv" | "json" | null>(null);
  const [exportNote, setExportNote] = useState<string | null>(null);

  useEffect(() => {
    if (!settings) return;
    setWeights([
      settings.fingerprintWeight,
      settings.gcnWeight,
      settings.llmWeight,
      settings.timeoutMs,
    ]);
  }, [settings]);

  useEffect(() => {
    void listAnalysisRuns()
      .then((rows) => setRunCount(rows.length))
      .catch(() => setRunCount(0));
  }, [tab, saved]);

  const runExport = (format: "csv" | "json") => {
    if (!can("analytics:export")) return;
    setExporting(format);
    setExportNote(null);
    void downloadIncidentExport(format)
      .then((result) => {
        setExportNote(
          result.savedToRepo && result.relativePath
            ? `Saved to ${result.relativePath}`
            : `Downloaded ${result.filename} (start py --serve to also save under exports/)`,
        );
      })
      .catch(() => setExportNote("Export failed."))
      .finally(() => setExporting(null));
  };

  if (!can("settings:read")) {
    return (
      <EmptyState
        title="Settings unavailable"
        detail="Your role does not include settings:read."
      />
    );
  }

  if (!settings) {
    return <EmptyState title="Loading settings…" />;
  }

  const writable = can("settings:write");

  return (
    <>
      {error ? <ErrorBanner message={error} onDismiss={clearError} /> : null}
      <PageHeading eyebrow="SYSTEM CONFIGURATION" title="Detection Settings" copy="Risk thresholds, model weights, and retention used by the screening pipeline.">
        <RequirePermission permission="settings:write" fallback={<span className="perm-hint">Read-only</span>}>
          <button
            className="btn primary"
            type="button"
            onClick={() => {
              void saveSettings({
                fingerprintWeight: weights[0],
                gcnWeight: weights[1],
                llmWeight: weights[2],
                timeoutMs: weights[3],
              }).then((ok) => {
                if (!ok) return;
                setSaved(true);
                setTimeout(() => setSaved(false), 1800);
              });
            }}
          >
            <Icon name={saved ? "check" : "settings"} size={15} />
            {saved ? "Changes saved" : "Save changes"}
          </button>
        </RequirePermission>
      </PageHeading>
      <div className="settings-tabs">
        {["Pipeline parameters", "RPC nodes", "Incident archive"].map((x) => (
          <button key={x} onClick={() => setTab(x)} className={tab === x ? "active" : ""}>{x}</button>
        ))}
      </div>
      {tab === "Pipeline parameters" ? (
        <div className="settings-grid">
          <section className="settings-card">
            <div className="settings-head">
              <span><Icon name="activity" /></span>
              <div>
                <h2>Tri-Signal Fusion Weights</h2>
                <p>Balance each model's contribution to the aggregate threat score.</p>
              </div>
            </div>
            {[
              ["Fingerprint W1", "Meta-heuristics and session signatures"],
              ["Structural GCN W2", "Control flow graph anomalies"],
              ["Semantic LLM W3", "Intent and contextual meaning"],
            ].map((x, i) => (
              <div className="range-field" key={x[0]}>
                <div>
                  <span><b>{x[0]}</b><small>{x[1]}</small></span>
                  <output>{weights[i]}%</output>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={weights[i]}
                  disabled={!writable}
                  onChange={(e) => {
                    const n = [...weights];
                    n[i] = Number(e.target.value);
                    setWeights(n);
                  }}
                />
              </div>
            ))}
            <div className="weight-total">
              <span>Combined weight</span>
              <b>{weights[0] + weights[1] + weights[2]}%</b>
              <small>Weights synchronized</small>
            </div>
          </section>
          <section className="settings-card">
            <div className="settings-head">
              <span><Icon name="activity" /></span>
              <div>
                <h2>Pipeline Performance</h2>
                <p>Set execution limits for pending transaction analysis.</p>
              </div>
            </div>
            <div className="range-field">
              <div>
                <span><b>Timeout limit</b><small>Maximum end-to-end analysis latency</small></span>
                <output>{weights[3]}ms</output>
              </div>
              <input
                type="range"
                min="200"
                max="1000"
                value={weights[3]}
                disabled={!writable}
                onChange={(e) => {
                  const n = [...weights];
                  n[3] = Number(e.target.value);
                  setWeights(n);
                }}
              />
              <div className="range-marks"><span>200ms</span><span>1000ms</span></div>
            </div>
            <label className="switch-row">
              <span><b>Fail-closed mode</b><small>Block transactions when analysis times out.</small></span>
              <input
                type="checkbox"
                checked={settings.failClosed}
                disabled={!writable}
                onChange={(e) => void saveSettings({ failClosed: e.target.checked })}
              />
              <i />
            </label>
            <label className="switch-row">
              <span><b>Adaptive model routing</b><small>Skip LLM pass for high-confidence clean transactions.</small></span>
              <input
                type="checkbox"
                checked={settings.adaptiveRouting}
                disabled={!writable}
                onChange={(e) => void saveSettings({ adaptiveRouting: e.target.checked })}
              />
              <i />
            </label>
          </section>
          <section className="settings-card">
            <div className="settings-head">
              <span><Icon name="alert" /></span>
              <div>
                <h2>Webhook Alerts</h2>
                <p>Forward critical detections to your incident response stack.</p>
              </div>
            </div>
            <label className="form-field">
              <span>Webhook URL</span>
              <input
                defaultValue={settings.webhookUrl}
                onBlur={(e) => void saveSettings({ webhookUrl: e.target.value })}
              />
            </label>
            <div className="form-row">
              <label className="form-field">
                <span>Minimum severity</span>
                <select
                  value={settings.minSeverity}
                  onChange={(e) => void saveSettings({ minSeverity: e.target.value })}
                >
                  <option>High & critical</option>
                  <option>Critical only</option>
                  <option>All alerts</option>
                </select>
              </label>
              <label className="form-field">
                <span>Authentication</span>
                <select
                  value={settings.authType}
                  onChange={(e) => void saveSettings({ authType: e.target.value })}
                >
                  <option>Bearer token</option>
                  <option>HMAC signature</option>
                </select>
              </label>
            </div>
            <button className="btn secondary test-btn">Send test alert <Icon name="arrow" size={14} /></button>
          </section>
          <section className="settings-card">
            <div className="settings-head">
              <span><Icon name="export" /></span>
              <div>
                <h2>Incident Export</h2>
                <p>Download transaction diagnostics for audit and review.</p>
              </div>
            </div>
            <div className="export-box">
              <div>
                <b>Incident archive</b>
                <span>
                  {runCount} analysis run{runCount === 1 ? "" : "s"} in Firestore
                  {" · "}
                  {(settings.archiveRecords / 1e6).toFixed(1)}M seeded archive capacity
                </span>
              </div>
              <span className="micro-badge safe">{settings.archiveSizeMb} MB</span>
            </div>
            <div className="export-actions">
              <RequirePermission permission="analytics:export" fallback={<span className="perm-hint">Export requires analytics:export</span>}>
                <button
                  className="btn secondary"
                  type="button"
                  disabled={exporting !== null}
                  onClick={() => runExport("csv")}
                >
                  <Icon name="export" size={15} />
                  {exporting === "csv" ? "Exporting…" : "Export CSV"}
                </button>
                <button
                  className="btn secondary"
                  type="button"
                  disabled={exporting !== null}
                  onClick={() => runExport("json")}
                >
                  <Icon name="export" size={15} />
                  {exporting === "json" ? "Exporting…" : "Export JSON"}
                </button>
              </RequirePermission>
            </div>
            <small className="retention"><Icon name="lock" size={13} />Exports save to exports/incidents_YYYY-MM-DD_HHMMSS.csv|json and also download in the browser.</small>
            {exportNote ? <small className="retention" style={{ color: "#9fe7c7" }}>{exportNote}</small> : null}
          </section>
        </div>
      ) : tab === "RPC nodes" ? (
        <section className="rpc-panel settings-card">
          <div className="settings-head">
            <span><Icon name="activity" /></span>
            <div>
              <h2>RPC Connection Strings</h2>
              <p>Primary and failover endpoints used for live mempool ingestion.</p>
            </div>
            <span className="status-badge"><i />3 HEALTHY</span>
          </div>
          <div className="rpc-grid">
            <label className="form-field"><span>Primary Ethereum RPC</span><input defaultValue="wss://eth-mainnet.carbyne.internal/mempool" /></label>
            <label className="form-field"><span>Failover RPC</span><input defaultValue="wss://eth-failover.carbyne.internal/ws" /></label>
            <label className="form-field"><span>Archive RPC</span><input defaultValue="https://archive.carbyne.internal/v2" /></label>
          </div>
          <button className="btn primary">Test all connections <Icon name="arrow" size={14} /></button>
        </section>
      ) : (
        <section className="placeholder-panel">
          <span><Icon name="lock" size={28} /></span>
          <h2>{tab}</h2>
          <p>{(settings.archiveRecords / 1e6).toFixed(1)}M incidents are retained in encrypted storage.</p>
          <button className="btn primary">Manage {tab.toLowerCase()}</button>
        </section>
      )}
    </>
  );
}

function AppShell() {
  const { status } = useAuth();
  const [page, setPage] = useState<Page>("monitor");
  const [inspector, setInspector] = useState(false);

  useEffect(() => {
    if (status === "anonymous") setInspector(false);
  }, [status]);

  if (status === "loading") {
    return (
      <main className="auth-shell" style={{ placeItems: "center" }}>
        <p className="terms">Securing session…</p>
      </main>
    );
  }

  if (status === "anonymous") {
    return <AuthPage onEnter={() => setPage("monitor")} />;
  }

  return (
    <div className="app-shell">
      <Header page={page} setPage={setPage} />
      <main className="content">
        {page === "monitor" && <Monitor openInspector={() => setInspector(true)} />}
        {page === "analytics" && <Analytics />}
        {page === "settings" && <Settings />}
      </main>
      {inspector && <Inspector close={() => setInspector(false)} />}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <DataProvider>
        <AppShell />
      </DataProvider>
    </AuthProvider>
  );
}
