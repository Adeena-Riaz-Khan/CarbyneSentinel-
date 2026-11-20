# Local Firebase Emulators (Auth + Firestore seeds)

Use this for demos: browse real **collections** in the Emulator UI while the React app reads the same data.

## Prereqs

- Node 20+
- **Java 21+** (Firestore emulator needs it) — [Adoptium](https://adoptium.net/)

## One-time setup

```bash
cd frontend
npm install
cp .env.emulator .env.local
```

## Every demo session (3 terminals)

**Terminal 1 — emulators**
```bash
npm run emulators
```
Opens Emulator Suite UI: **http://127.0.0.1:4000**

**Terminal 2 — seed Auth users + Firestore collections**
```bash
npm run emulators:seed
```

**Terminal 3 — UI**
```bash
npm run dev
```
App: **http://localhost:5173**  
Login footer: *Local Firebase Emulator · Auth + Firestore seeds*

Demo login: `alex@carbyne.security` / `Carbyne#Secure1!`

## Collections written by the seed

| Path | Contents |
|------|----------|
| `stats/global` | Latency, throughput, block height, … |
| `transactions/{id}` | Mempool feed rows |
| `agents/{id}` | AgentGuard agents |
| `alerts/intercept` | Prompt-injection alert |
| `settings/pipeline` | Fusion weights, webhooks, … |
| `benchmarks/latest` | Analytics charts |
| `users/{uid}` | Role profiles for Auth users |
| `analysis_runs/{id}` | Written live after each Inspect → Analyze (summary + SHA-256, not full bytecode) |

Inspect them in Emulator UI → **Firestore**. Later, point the same paths at a cloud project and replace seeds with live data.

**Settings → Export CSV / JSON** saves dated files under `exports/` (via the Python `--serve` API) and also triggers a browser download. Filenames look like `incidents_2026-11-13_145730.json`.

## Without emulators

Delete `.env.local` (or set `VITE_USE_MOCK_AUTH=true`). The UI falls back to in-memory mock auth + seeds.
