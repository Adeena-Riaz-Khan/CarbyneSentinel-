import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import heroPhoto from "./assets/carbyne-hero-chain-hand.png";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { EmptyState } from "./components/EmptyState";
import { ErrorBanner } from "./components/ErrorBanner";
import { RequirePermission } from "./components/RequirePermission";
import { DataProvider, useData } from "./context/DataContext";
import { PENDING_FEED_TOTAL } from "./contracts/grids";
import {
  filterTransactions,
  intentToneClass,
  scoreRiskBand,
} from "./domain/calculations";
import AuthPage from "./pages/AuthPage";
import { sanitizeSearchQuery } from "./validation/forms";

type Page = "monitor" | "agents" | "analytics" | "settings" | "auth";
type IconName =
  | "activity"
  | "agent"
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
  agent: <><rect x="5" y="7" width="14" height="12" rx="3" /><path d="M9 7V5a3 3 0 0 1 6 0v2M9 13h.01M15 13h.01M9 16h6" /></>,
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
  { id: "agents", label: "AgentGuard", icon: "agent" },
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
              <Icon name={item.icon} size={16} /> {item.label}
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
            <span className="pulse-dot" /> TRI-SIGNAL PIPELINE LIVE <b>{stats?.avgLatencyMs ?? "—"}MS AVG</b>
          </div>
          <div className="eyebrow">REAL-TIME THREAT OPERATIONS</div>
          <h1>Live Mempool <span>Monitor</span></h1>
          <p>Sub-500ms transaction intelligence powered by fingerprinting, structural GCN analysis, and semantic auditing.</p>
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
              <h2>Pending transaction feed</h2>
              <span className="live-label"><i /> STREAMING</span>
            </div>
            <p>Prioritized by aggregated threat confidence</p>
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

function RiskGraph() {
  return <div className="graph"><svg viewBox="0 0 300 120"><path className="edge" d="M32 62 96 27M32 62l67 40M96 27l54 35M99 102l51-40m0 0 56-36m-56 36 60 41m-60-41h112" /><path className="danger-edge" d="M150 62c70-50 94 45 18 37-45-5-29-70 31-48" /><g>{[[32,62],[96,27],[99,102],[150,62],[206,26],[210,103],[262,62]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r={i===3?11:7} className={i===3?"danger-node":"node"} />)}</g></svg><span className="graph-tag">Reentrant call loop</span></div>;
}

function Inspector({ close }: { close: () => void }) {
  return (
    <div className="modal-backdrop" onMouseDown={close}>
      <section className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div><div className="eyebrow danger-text">CRITICAL THREAT · PENDING</div><h2>Transaction diagnostics</h2><div className="tx-meta"><code>0x3c1b8e749f4a...2dA7a82</code><span>Block pending</span><span>64.1 Gwei</span></div></div>
          <button className="icon-btn" onClick={close}><Icon name="close" /></button>
        </div>
        <div className="code-grid">
          <div><div className="code-label"><span>Raw bytecode</span><button><Icon name="copy" size={13} /> Copy</button></div><code>0x608060405234801561001057600080fd5b50<span>6107d8</span>806100206000396000f3fe...</code></div>
          <div><div className="code-label"><span>Disassembled EVM opcodes</span><span>412 instructions</span></div><code>PUSH1 0x80 · PUSH1 0x40 · MSTORE · CALLVALUE · <span>DELEGATECALL</span> · JUMPI</code></div>
        </div>
        <div className="signal-grid">
          <article className="signal-card fingerprint">
            <div className="signal-title"><span className="signal-index">01</span><div><h3>Manipulation fingerprint</h3><p>Code-level evasion analysis</p></div><span className="signal-ok"><Icon name="check" size={13} /></span></div>
            <div className="big-score"><span>Entropy score</span><b>0.91</b></div><div className="meter"><i style={{width:"91%"}} /></div>
            <div className="threat-label"><Icon name="alert" size={14} /> Deliberately disguised / obfuscated</div>
            <dl><div><dt>Junk insertion</dt><dd>Detected</dd></div><div><dt>Control flow flattening</dt><dd>High</dd></div><div><dt>Bytecode similarity</dt><dd>8.3%</dd></div></dl>
          </article>
          <article className="signal-card structural">
            <div className="signal-title"><span className="signal-index">02</span><div><h3>Structural GCN detector</h3><p>Control-flow graph analysis</p></div><span className="signal-ok"><Icon name="check" size={13} /></span></div>
            <div className="big-score"><span>CFG risk score</span><b>0.84</b></div><div className="meter"><i style={{width:"84%"}} /></div>
            <RiskGraph /><div className="graph-legend"><span><i className="node-key" /> Normal node</span><span><i className="risk-key" /> Flagged loop</span></div>
          </article>
          <article className="signal-card semantic">
            <div className="signal-title"><span className="signal-index">03</span><div><h3>Semantic LLM auditor</h3><p>QLoRA intent reasoning</p></div><span className="signal-ok"><Icon name="check" size={13} /></span></div>
            <div className="intent-box"><span>Classified intent</span><b>Actual exploit</b><em>94.2% confidence</em></div>
            <div className="explanation"><span>Model explanation</span><p>The transaction uses a flash loan to distort the pool's spot price, then calls the protocol's unguarded oracle before liquidity normalizes. Expected extraction: <b>$1.82M.</b></p></div>
            <div className="model-meta"><span>Model <b>Sentinel-7B</b></span><span>Inference <b>207ms</b></span></div>
          </article>
        </div>
        <footer className="modal-footer">
          <div className="risk-gauge"><div className="gauge"><span>0.89</span></div><div><span>Aggregated risk score</span><b>HIGH RISK</b><small>Fusion threshold exceeded by 0.21</small></div></div>
          <div className="decision"><label className="override-toggle"><span>Manual override</span><input type="checkbox"/><i/></label><button className="btn danger block-action" onClick={close}><Icon name="lock" size={15} />BLOCK TRANSACTION</button></div>
        </footer>
      </section>
    </div>
  );
}

function AgentGuard() {
  const { agents, stats, intercept, toggleFreeze } = useData();
  const fmt = (n: number) => `$${n.toLocaleString()}`;
  return (
    <>
      <PageHeading eyebrow="AUTONOMOUS SECURITY LAYER" title="AgentGuard" copy="Policy enforcement for autonomous AI payment workflows.">
        <button className="btn secondary"><Icon name="settings" size={15} />Global policies</button>
        <button className="btn primary">Register agent <Icon name="arrow" size={15} /></button>
      </PageHeading>
      <div className="hero-banner">
        <div>
          <span className="hero-icon"><Icon name="agent" size={25} /></span>
          <div className="eyebrow">AI-NATIVE PAYMENT DEFENSE</div>
          <h2>Autonomous AI payment guardrails</h2>
          <p>Every agent call is screened for prompt injection, recipient drift, and policy violations before it reaches the chain.</p>
        </div>
        <div className="radar"><span /><i /><b><Icon name="shield" size={25} /></b></div>
      </div>
      <div className="summary-grid">
        {[
          [String(stats?.activeAgents ?? "—"), "Active monitored agents", "All systems nominal"],
          [String(stats?.interceptedCalls ?? "—"), "Intercepted injected calls", "Last 24 hours"],
          [stats?.protectedVolume ?? "—", "Protected volume", `Across ${(stats?.totalCalls ?? 0).toLocaleString()} calls`],
        ].map((x, i) => (
          <article className="summary-card" key={x[1]}>
            <span className={`summary-icon s${i}`}><Icon name={i === 0 ? "agent" : i === 1 ? "shield" : "activity"} /></span>
            <div><b>{x[0]}</b><span>{x[1]}</span><small>{x[2]}</small></div>
          </article>
        ))}
      </div>
      <section className="agent-layout">
        <div className="agent-list">
          <div className="section-head">
            <div><h2>Monitored agents</h2><p>Live policy status and spending utilization</p></div>
            <span>{stats?.activeAgents ?? agents.length} agents · {agents.length} shown</span>
          </div>
          <div className="agent-grid">
            {agents.map((a) => {
              const pct = Math.round((a.spent / a.limit) * 100);
              return (
                <article className="agent-card" key={a.id}>
                  <div className="agent-card-head">
                    <span className={`agent-avatar ${a.color}`}>{a.initials}</span>
                    <div><h3>{a.name} Agent</h3><p>{a.description}</p></div>
                    <span className="status-badge"><i />{a.status}</span>
                  </div>
                  <div className="allowance">
                    <div><span>Daily spending allowance</span><b>{fmt(a.spent)} <small>/ {fmt(a.limit)}</small></b></div>
                    <div className="allowance-track"><i style={{ width: `${pct}%` }} /></div>
                    <small>{100 - pct}% remaining · Resets in 08:42:19</small>
                  </div>
                  <div className="recent-label">RECENT TRANSACTIONS</div>
                  {a.recentTxs.map((tx) => (
                    <div className="agent-tx" key={tx.label}>
                      <span className={tx.status === "Blocked" ? "tx-icon blocked" : "tx-icon"}>
                        <Icon name={tx.status === "Blocked" ? "close" : "check"} size={12} />
                      </span>
                      <div><b>{tx.label}</b><small>{tx.ago} · Ethereum</small></div>
                      <span><b>{tx.amount}</b><small className={tx.status === "Blocked" ? "danger-text" : "safe-text"}>{tx.status}</small></span>
                    </div>
                  ))}
                  <div className="agent-controls">
                    <label>
                      <span>Spending ceiling</span>
                      <div><input defaultValue={a.limit.toLocaleString()} /><small>USD / day</small></div>
                    </label>
                    <RequirePermission
                      permission="agents:freeze"
                      fallback={<span className="perm-hint">Freeze requires Security Admin</span>}
                    >
                      <button className="freeze-btn" onClick={() => void toggleFreeze(a.id)} type="button">
                        <Icon name={a.status === "FROZEN" ? "play" : "lock"} size={15} />
                        {a.status === "FROZEN" ? "Unfreeze agent" : "Emergency freeze"}
                      </button>
                    </RequirePermission>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
        {intercept && (
          <aside className="intercept-alert">
            <div className="alert-head">
              <span><Icon name="alert" /></span>
              <div>
                <div className="eyebrow danger-text">INTERCEPTED CALL</div>
                <h3>{intercept.title}</h3>
                <p>{intercept.blockedAgo}</p>
              </div>
            </div>
            <div className="alert-flow">
              <div><span>Expected recipient</span><code>{intercept.expectedRecipient}</code></div>
              <Icon name="arrow" />
              <div><span>Actual recipient</span><code>{intercept.actualRecipient}</code></div>
            </div>
            <div className="alert-copy">
              <b>Recipient drift identified</b>
              <p>{intercept.explanation}</p>
            </div>
            <dl>
              <div><dt>Agent</dt><dd>{intercept.agentName}</dd></div>
              <div><dt>Attempted value</dt><dd>{intercept.attemptedValue}</dd></div>
              <div><dt>Confidence</dt><dd>{intercept.confidence}%</dd></div>
            </dl>
            <button className="inspect-alert">Open incident report <Icon name="arrow" size={14} /></button>
          </aside>
        )}
      </section>
    </>
  );
}

function Analytics() {
  const { benchmarks } = useData();
  if (!benchmarks) return null;
  const labels = ["Transfer", "Arbitrage", "Exploit"];
  const matrixClasses = ["m90", "m80", "m100"];
  return (
    <>
      <PageHeading eyebrow="MODEL RESEARCH & VALIDATION" title="Benchmark Analytics" copy="Transparent performance across adversarial Web3 evaluation sets.">
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
              <h2>Obfuscation survival rate</h2>
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
              <h2>DeFi intent matrix</h2>
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
              <h2>Sub-500ms latency breakdown</h2>
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

  useEffect(() => {
    if (!settings) return;
    setWeights([
      settings.fingerprintWeight,
      settings.gcnWeight,
      settings.llmWeight,
      settings.timeoutMs,
    ]);
  }, [settings]);

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
      <PageHeading eyebrow="SYSTEM CONFIGURATION" title="Settings" copy="Manage screening parameters, infrastructure, and incident retention.">
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
                <h2>Tri-signal fusion weights</h2>
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
                <h2>Pipeline performance</h2>
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
                <h2>Webhook alerts</h2>
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
                <h2>Incident export</h2>
                <p>Download transaction diagnostics for audit and review.</p>
              </div>
            </div>
            <div className="export-box">
              <div>
                <b>Incident archive</b>
                <span>{(settings.archiveRecords / 1e6).toFixed(1)}M records — Jan 1 — present</span>
              </div>
              <span className="micro-badge safe">{settings.archiveSizeMb} MB</span>
            </div>
            <div className="export-actions">
              <button className="btn secondary"><Icon name="export" size={15} />Export CSV</button>
              <button className="btn secondary"><Icon name="export" size={15} />Export JSON</button>
            </div>
            <small className="retention"><Icon name="lock" size={13} />Reports are encrypted and retained for 365 days.</small>
          </section>
        </div>
      ) : tab === "RPC nodes" ? (
        <section className="rpc-panel settings-card">
          <div className="settings-head">
            <span><Icon name="activity" /></span>
            <div>
              <h2>RPC connection strings</h2>
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
        {page === "agents" && <AgentGuard />}
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
