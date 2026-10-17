import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MEMPOOL_COLUMNS, PENDING_FEED_TOTAL } from "../contracts/grids";
import { filterTransactions } from "../domain/calculations";
import {
  __resetAuthForTests,
  bootstrapDemoUsers,
  signIn,
} from "../services/authService";
import { __resetApiForTests, getTransactions } from "../services/apiClient";
import { __resetSessionStoreForTests } from "../services/sessionStore";
import { subscribeTransactions } from "../services/subscriptions";

beforeEach(async () => {
  __resetAuthForTests();
  __resetSessionStoreForTests();
  __resetApiForTests();
  await bootstrapDemoUsers();
  await signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("edge cases + cleanup", () => {
  it("grid columns stay stable for regression", () => {
    expect(MEMPOOL_COLUMNS.map((c) => c.id)).toEqual([
      "hash",
      "contract",
      "gas",
      "fingerprint",
      "structural",
      "intent",
      "action",
      "inspect",
    ]);
    expect(PENDING_FEED_TOTAL).toBe(1289);
  });

  it("empty state path when filter excludes all", async () => {
    const txs = await getTransactions();
    expect(filterTransactions(txs, "no-such-hash-zzzz", "All risk levels")).toHaveLength(0);
  });

  it("subscription unsubscribe stops timers (explicit cleanup)", async () => {
    vi.useFakeTimers();
    let calls = 0;
    const unsub = subscribeTransactions(
      () => {
        calls += 1;
      },
      () => undefined,
      500,
    );
    await vi.advanceTimersByTimeAsync(50);
    const afterFirst = calls;
    unsub();
    await vi.advanceTimersByTimeAsync(2000);
    expect(calls).toBe(afterFirst);
  });
});
