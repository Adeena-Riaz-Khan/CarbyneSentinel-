# CarbyneSentinel frontend

React + Vite + TypeScript UI. Specs, auth, and tests live alongside the prototype without changing the Figma look.

## Run (UI only, mock data)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Run with local Firebase (Auth + Firestore seeds)

Needs **Java 21+**. See `docs/EMULATORS.md`.

```bash
cp .env.emulator .env.local
npm run emulators          # http://127.0.0.1:4000
npm run emulators:seed     # writes collections + demo users
npm run dev                # http://localhost:5173
```

## Test

```bash
npm test
npm run build
```

## Auth

| Email | Password | Role |
|-------|----------|------|
| alex@carbyne.security | Carbyne#Secure1! | Security Admin |
| analyst@carbyne.security | Analyst#Secure1! | Analyst |
| viewer@carbyne.security | Viewer#Secure1! | Viewer |

Docs: `docs/EMULATORS.md`, `docs/FIREBASE_AUTH.md`, `docs/SPEC.md`, `docs/AUTH.md`

## Scaffold layout

```
src/contracts/     typed domain, auth, grids, errors
src/validation/    form rules ↔ API contracts
src/services/      authService, apiClient, sessionStore, subscriptions
src/auth/          AuthProvider / RBAC
src/domain/        pure calculations (BR-traced)
src/components/    EmptyState, ErrorBanner, RequirePermission
src/__tests__/     edge cases, auth, permissions, regression
```
