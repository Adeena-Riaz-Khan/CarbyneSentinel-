# Verification Matrix

## Edge cases

| Case | Expected | Test / check |
|------|----------|--------------|
| Empty transaction list | EmptyState, no table crash | `edgeCases.test.ts` |
| Filter matches nothing | EmptyState “No pending…” | Monitor filter + test |
| Network / 503 from API | ErrorBanner; prior data kept or cleared safely | `apiClient.test.ts` |
| Score = 0 / 1 | safe / danger band | `calculations.test.ts` |
| Weight sum 99 / 101 | save rejected | `validation.test.ts` |
| timeoutMs 199 / 1001 | rejected | `validation.test.ts` |
| http webhook URL | rejected | `validation.test.ts` |
| Viewer freezes agent | 403 / UI disabled | `permissions.test.ts` |
| Expired session | forced auth page | `authService.test.ts` |
| 5 bad logins | 429 lockout message | `authService.test.ts` |
| Spending limit 0 | validation fail | `validation.test.ts` |

## Form ↔ contract ↔ business message

| Field | Contract | Message | BR |
|-------|----------|---------|-----|
| email | login body | Enter a valid work email. | BR-AUTH-1 |
| password | login body | Password must be… | BR-AUTH-1 |
| weights sum | PATCH settings | Combined weight must equal 100%. | BR-SET-1 |
| timeout | PATCH settings | Timeout must be between 200ms and 1000ms. | BR-SET-2 |
| webhook | PATCH settings | Webhook URL must use HTTPS. | BR-SET-3 |

## User flows → BR

| Flow | BR |
|------|-----|
| Sign in → Mempool | BR-AUTH-1, BR-MON-1 |
| Simulate exploit → diagnostics → block | BR-DX-1, BR-PERM-1 |
| Emergency freeze | BR-AG-1, BR-AUTH-2 |
| Save settings | BR-SET-1..3, BR-AUTH-2 |
| Sign out → auth | BR-AUTH-3 |

## Responsive / cross-browser (manual)

| Surface | Chrome | Firefox | Edge | 375px | 768px | 1280px+ |
|---------|--------|---------|------|-------|-------|---------|
| Auth split / stack | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| Mempool table scroll | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| Agent grid → stack | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| Settings 2×2 → 1 col | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| Diagnostics modal | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

Run: `npm run test` then `npm run build` then `npm run dev` smoke (sign-in, nav all pages, inspect, settings save, sign-out).

## Regression (prototype must still work)

| Check | Pass |
|-------|------|
| Auth visual layout unchanged | ☐ |
| Mempool hero + feed render with seeds | ☐ |
| AgentGuard cards + intercept | ☐ |
| Analytics charts | ☐ |
| Settings sliders / toggles | ☐ |
| Diagnostics modal open/close | ☐ |
| `npm run build` succeeds | ☐ |
