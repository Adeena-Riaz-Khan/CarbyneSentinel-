import { beforeEach, describe, expect, it } from "vitest";
import { ApiError } from "../contracts/errors";
import {
  __resetApiForTests,
  __setNetworkDown,
  freezeAgent,
  getStats,
  getTransactions,
  patchSettings,
} from "../services/apiClient";
import {
  __resetAuthForTests,
  bootstrapDemoUsers,
  signIn,
  signOut,
} from "../services/authService";
import { __resetSessionStoreForTests } from "../services/sessionStore";

beforeEach(async () => {
  __resetAuthForTests();
  __resetSessionStoreForTests();
  __resetApiForTests();
  await bootstrapDemoUsers();
});

describe("apiClient authz + network (BR-NET-1, BR-PERM-1)", () => {
  it("rejects unauthenticated reads", async () => {
    await expect(getTransactions()).rejects.toMatchObject({ code: "UNAUTHORIZED" });
  });

  it("returns seed transactions for admin", async () => {
    await signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" });
    const txs = await getTransactions();
    expect(txs.length).toBeGreaterThan(0);
    const stats = await getStats();
    expect(stats.avgLatencyMs).toBe(285);
  });

  it("forbids viewer freeze", async () => {
    await signIn({ email: "viewer@carbyne.security", password: "Viewer#Secure1!" });
    await expect(freezeAgent("ag1", true)).rejects.toMatchObject({ code: "FORBIDDEN" });
  });

  it("surfaces network failure", async () => {
    await signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" });
    __setNetworkDown(true);
    await expect(getStats()).rejects.toBeInstanceOf(ApiError);
    await expect(getStats()).rejects.toMatchObject({ code: "UNAVAILABLE" });
  });

  it("rejects invalid settings write", async () => {
    await signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" });
    await expect(
      patchSettings({ fingerprintWeight: 10, gcnWeight: 10, llmWeight: 10 }),
    ).rejects.toMatchObject({ code: "VALIDATION" });
  });

  it("clears access after signOut", async () => {
    await signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" });
    await signOut();
    await expect(getTransactions()).rejects.toMatchObject({ code: "UNAUTHORIZED" });
  });
});
