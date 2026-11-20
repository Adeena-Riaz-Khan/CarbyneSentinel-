# Authentication & Authorization

## Threat model (short)

| Boundary | Threat | Mitigation |
|----------|--------|------------|
| Login form | Brute force | 5 failures → 15 min lockout (BR-AUTH-1) |
| Login form | User enumeration | Same error for unknown email / bad password |
| Session | XSS token theft | Access token held in memory only |
| Session | Stale access | Absolute expiry + idle check |
| Pages / mutations | Privilege escalation | RBAC on UI **and** service layer |
| Wallet connect | Spoofed address | Format validate; demo maps to Analyst only |

## Roles → permissions

| Permission | security_admin | analyst | viewer |
|------------|:--------------:|:-------:|:------:|
| console:access | ✓ | ✓ | ✓ |
| mempool:read | ✓ | ✓ | ✓ |
| mempool:simulate | ✓ | ✓ | |
| agents:read | ✓ | ✓ | ✓ |
| agents:freeze | ✓ | | |
| analytics:read | ✓ | ✓ | ✓ |
| analytics:export | ✓ | ✓ | |
| settings:read | ✓ | ✓ | |
| settings:write | ✓ | | |
| diagnostics:read | ✓ | ✓ | ✓ |
| diagnostics:block | ✓ | ✓ | |

## Demo accounts (local mock only)

| Email | Password | Role |
|-------|----------|------|
| `alex@carbyne.security` | `Carbyne#Secure1!` | security_admin |
| `analyst@carbyne.security` | `Analyst#Secure1!` | analyst |
| `viewer@carbyne.security` | `Viewer#Secure1!` | viewer |

**Firebase:** set `VITE_FIREBASE_*` (see `docs/FIREBASE_AUTH.md`). Same UI; `authService` routes to Firebase Auth. Keep the permission matrix; enforce roles with custom claims + backend before production.

## Session lifecycle

1. `signIn` / `signUp` / `connectWallet` → validate → issue opaque access token + `expiresAt`
2. Token stored in module memory (`sessionStore`); optional **session flag only** in `sessionStorage` (boolean “hasSession”) for refresh UX — **never** the raw token
3. Expiry timer calls `signOut`
4. `signOut` clears memory, timers, listeners, and session flag

## Production checklist (when leaving mock)

- [ ] httpOnly Secure SameSite cookies for session
- [ ] CSRF protection for cookie sessions
- [ ] Argon2id / Firebase password hashing server-side
- [ ] Rotate refresh tokens; short-lived access tokens
- [ ] Audit log for login, freeze, settings write, block
