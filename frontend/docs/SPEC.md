# CarbyneSentinel Frontend — Component Spec, Data Shapes, Validation, Grids, API Contracts

**Scope:** `frontend/` only. Prototype UI stays intact; this document is the contract for tests, auth, and future backend wiring.

**Business requirements (BR) referenced throughout:**

| ID | Requirement |
|----|-------------|
| BR-AUTH-1 | Users must authenticate before console access |
| BR-AUTH-2 | Roles enforce least privilege (Admin / Analyst / Viewer) |
| BR-AUTH-3 | Sessions expire; logout clears all client secrets |
| BR-MON-1 | Pending feed shows threat-ranked transactions |
| BR-MON-2 | Scores [0,1]; action ∈ {ALLOW, FLAG, BLOCK} |
| BR-MON-3 | Empty/filtered feed shows empty state, not crash |
| BR-AG-1 | Agents show spending vs ceiling; freeze is Admin-only |
| BR-AG-2 | Intercept panel surfaces prompt-injection incidents |
| BR-AN-1 | Benchmark cards reflect seed/API benchmark doc |
| BR-SET-1 | Fusion weights must sum to 100 (±0) before save |
| BR-SET-2 | Timeout ∈ [200, 1000] ms; fail-closed / adaptive toggles |
| BR-SET-3 | Webhook URL must be https |
| BR-DX-1 | Diagnostics modal opens from inspect / simulate exploit |
| BR-NET-1 | Network failures surface recoverable error, not blank UI |
| BR-PERM-1 | Unauthorized actions return 403-shaped errors |

---

## 1. Component boundaries

| Component | Responsibility | Owns state? | Reads | Writes | Cleanup |
|-----------|----------------|-------------|-------|--------|---------|
| `AuthPage` | Sign-in / sign-up / wallet entry UI | Form local | — | `authService.signIn` | None (unmount ok) |
| `AppShell` | Page router after auth | `page`, `inspector` | `useAuth`, `useData` | — | Close modal on unmount |
| `Header` | Nav + identity chip | — | session user, stats | `signOut` / navigate auth | — |
| `Monitor` | Mempool hero + feed | filter, query, paused | transactions, stats | — | Abort search debounce |
| `AgentGuard` | Agents + intercept | — | agents, intercept | `freezeAgent` (gated) | — |
| `Analytics` | Benchmark charts | — | benchmarks | — | — |
| `Settings` | Pipeline / webhook / export | local draft weights | settings | `saveSettings` (gated) | Discard draft on leave |
| `Inspector` | Tx diagnostics modal | — | selected tx (future) | block action (gated) | Remove key listeners |
| `AuthProvider` | Session + permissions | session, status | `authService` | login/logout | Clear timers + subs |
| `DataProvider` | Domain collections | collections | `apiClient` | settings/agents | Abort in-flight loads |
| `EmptyState` | Empty grids / filters | — | message | — | — |
| `ErrorBanner` | Network / API errors | — | `ApiError` | dismiss | — |
| `RequirePermission` | Hide/disable by RBAC | — | permissions | — | — |

**Rule:** Presentational pages never call `fetch` directly — only services via context.

---

## 2. Data shapes (domain)

See also `src/contracts/domain.ts`.

```ts
Role = "security_admin" | "analyst" | "viewer"
Permission =
  | "console:access"
  | "mempool:read" | "mempool:simulate"
  | "agents:read" | "agents:freeze"
  | "analytics:read" | "analytics:export"
  | "settings:read" | "settings:write"
  | "diagnostics:read" | "diagnostics:block"

Transaction {
  id, hash, contractName, contractAddress,
  gasPrice: number >= 0,
  fingerprintScore: 0..1, structuralScore: 0..1,
  intent: string,
  action: "ALLOW" | "FLAG" | "BLOCK"
}

Agent {
  id, initials, name, description,
  status: "ACTIVE" | "FROZEN",
  spent: number >= 0, limit: number > 0,
  color: "blue" | "purple",
  recentTxs: { label, amount, status, ago }[]
}

SettingsDoc {
  fingerprintWeight, gcnWeight, llmWeight: 0..100,
  timeoutMs: 200..1000,
  failClosed, adaptiveRouting: boolean,
  webhookUrl: https URL,
  minSeverity, authType: string,
  archiveRecords, archiveSizeMb: number
}
```

---

## 3. Validation rules (forms ↔ backend contracts)

| Form field | Client rule | API contract | Error message (UX) | BR |
|------------|-------------|--------------|--------------------|----|
| email | required, RFC-ish email, max 254 | `POST /auth/login` body.email | “Enter a valid work email.” | BR-AUTH-1 |
| password | required, min 12, upper+lower+digit+symbol | same | “Password must be at least 12 characters and include upper, lower, number, and symbol.” | BR-AUTH-1 |
| signup name | required if signup, 2–80 chars | `POST /auth/signup` | “Enter your full name.” | BR-AUTH-1 |
| fusion weights | each 0–100; sum === 100 | `PATCH /settings` | “Combined weight must equal 100%.” | BR-SET-1 |
| timeoutMs | 200–1000 integer | `PATCH /settings` | “Timeout must be between 200ms and 1000ms.” | BR-SET-2 |
| webhookUrl | https URL, max 2048 | `PATCH /settings` | “Webhook URL must use HTTPS.” | BR-SET-3 |
| spending ceiling | > 0, ≤ 10_000_000 | `PATCH /agents/:id` | “Spending ceiling must be greater than zero.” | BR-AG-1 |
| search query | max 128, strip control chars | client filter only | (silent truncate) | BR-MON-1 |

**Never trust client alone** — services re-validate before mutating memory/API.

---

## 4. Grid columns

### Mempool — Pending transaction feed (BR-MON-1)

| Column | Field | Format | Sort/Filter |
|--------|-------|--------|-------------|
| Tx hash | `hash` | truncated hex + copy | search |
| Target contract | `contractName` / `contractAddress` | name + small address | search |
| Gas price | `gasPrice` | `{n} Gwei` | — |
| Fingerprint | `fingerprintScore` | 0.00–1.00 + bar | — |
| Structural | `structuralScore` | 0.00–1.00 + bar | — |
| Semantic intent | `intent` | pill by tone | — |
| Action | `action` | ALLOW / FLAG / BLOCK badge | filter |
| Inspect | — | opens diagnostics | — |

**Footer calc:** `Showing {visible} of {totalPending}` — totalPending from stats feed meta (seed: 1289). BR-MON-1.

### Agent recent transactions (BR-AG-1)

| Column | Field |
|--------|-------|
| Status icon | `status` Allowed/Blocked |
| Description | `label` |
| When / chain | `ago` + network |
| Amount | `amount` |
| Outcome | `status` text |

### Analytics matrices (BR-AN-1)

- Obfuscation bars: `otherToolPct`, `ourModelPct`, delta = our − other (BR: +52 pp seed)
- Confusion matrix 3×3: Transfer / Arbitrage / Exploit
- Latency histogram: stages ms; SLA line 500ms; total median sum of stages (business: must stay under SLA narrative)

---

## 5. API contracts

Base: `VITE_API_BASE_URL` (default mock in-process). All JSON. Auth: `Authorization: Bearer <accessToken>`.

| Method | Path | Auth | Request | Success | Errors |
|--------|------|------|---------|---------|--------|
| POST | `/auth/login` | no | `{ email, password }` | `{ user, accessToken, expiresAt }` | 400 validation, 401 bad creds, 429 lockout |
| POST | `/auth/signup` | no | `{ name, email, password }` | same as login | 400, 409 email taken |
| POST | `/auth/wallet` | no | `{ address }` | session as analyst | 400 invalid address |
| POST | `/auth/logout` | yes | — | 204 | 401 |
| GET | `/auth/session` | yes | — | `{ user, expiresAt }` | 401 expired |
| GET | `/stats` | `mempool:read` | — | `GlobalStats` | 401/403/503 |
| GET | `/transactions` | `mempool:read` | `?q&action` | `Transaction[]` | 401/403/503 |
| GET | `/agents` | `agents:read` | — | `Agent[]` | 401/403 |
| POST | `/agents/:id/freeze` | `agents:freeze` | `{ frozen: boolean }` | `Agent[]` | 403 |
| GET | `/alerts/intercept` | `agents:read` | — | `InterceptAlert \| null` | 401 |
| GET | `/benchmarks` | `analytics:read` | — | `BenchmarkDoc` | 401/403 |
| GET | `/settings` | `settings:read` | — | `SettingsDoc` | 401/403 |
| PATCH | `/settings` | `settings:write` | `Partial<SettingsDoc>` | `SettingsDoc` | 400/403 |

**Error envelope:**

```ts
{ error: { code: string, message: string, fields?: Record<string, string> } }
```

---

## 6. Calculated fields → business requirements

| Calculation | Formula | BR |
|-------------|---------|----|
| Agent utilization % | `round(spent/limit*100)` | BR-AG-1 |
| Agent remaining % | `100 - utilization` | BR-AG-1 |
| Fusion combined weight | `W1+W2+W3` must be 100 | BR-SET-1 |
| Latency total median | `sum(latencyStages.ms)` | BR-AN-1 |
| Score risk band | `>0.75 danger, >0.4 warning, else safe` | BR-MON-2 |
| Intent tone | keyword → pill class | BR-MON-1 |
| Obfuscation delta pp | `ourModelPct - otherToolPct` | BR-AN-1 |
| Auth lockout | ≥5 failures / 15 min | BR-AUTH-1 |

---

## 7. Subscriptions & cleanup

| Subscription | Source | Cleanup |
|--------------|--------|---------|
| Session expiry timer | `authService` | `clearTimeout` on logout/unmount |
| Mempool auto-refresh (future) | `subscribeTransactions` | `unsubscribe()` |
| Auth state listeners | `authService.onAuthStateChanged` | return disposer |
| In-flight API | `AbortController` | `abort()` on unmount / new request |

---

## 8. AuthN / AuthZ (summary)

Full detail: `docs/AUTH.md`.

- Access token **memory-only** (not `localStorage`) — XSS-resistant pattern.
- Roles → permission sets; UI + service double-check.
- Login rate limit + generic failure messages (no user enumeration).
- Prototype demo users documented in AUTH.md only (not in public README secrets section beyond demo flag).
