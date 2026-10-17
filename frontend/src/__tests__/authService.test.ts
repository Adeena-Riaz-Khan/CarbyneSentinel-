import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../contracts/errors";
import {
  __forceLockoutForTests,
  __resetAuthForTests,
  bootstrapDemoUsers,
  can,
  enterDemoConsole,
  getCurrentSession,
  signIn,
  signOut,
} from "../services/authService";
import { __resetSessionStoreForTests } from "../services/sessionStore";

beforeEach(() => {
  __resetAuthForTests();
  __resetSessionStoreForTests();
});

describe("authService (BR-AUTH-1..3)", () => {
  it("signs in demo admin and grants settings:write", async () => {
    await bootstrapDemoUsers();
    const session = await signIn({
      email: "alex@carbyne.security",
      password: "Carbyne#Secure1!",
    });
    expect(session.user.role).toBe("security_admin");
    expect(can("settings:write")).toBe(true);
    expect(getCurrentSession()?.accessToken).toBeTruthy();
  });

  it("rejects bad password with generic message", async () => {
    await bootstrapDemoUsers();
    await expect(
      signIn({ email: "alex@carbyne.security", password: "WrongPass#12345" }),
    ).rejects.toMatchObject({ code: "UNAUTHORIZED", message: "Invalid email or password." });
  });

  it("locks out after forced rate limit", async () => {
    await bootstrapDemoUsers();
    __forceLockoutForTests("alex@carbyne.security");
    await expect(
      signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" }),
    ).rejects.toBeInstanceOf(ApiError);
    try {
      await signIn({ email: "alex@carbyne.security", password: "Carbyne#Secure1!" });
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe("RATE_LIMIT");
    }
  });

  it("viewer cannot freeze agents", async () => {
    await bootstrapDemoUsers();
    await signIn({
      email: "viewer@carbyne.security",
      password: "Viewer#Secure1!",
    });
    expect(can("agents:freeze")).toBe(false);
    expect(can("mempool:read")).toBe(true);
  });

  it("signOut clears session (BR-AUTH-3)", async () => {
    await enterDemoConsole();
    expect(getCurrentSession()).not.toBeNull();
    await signOut();
    expect(getCurrentSession()).toBeNull();
    expect(can("console:access")).toBe(false);
  });

  it("keeps access token out of sessionStorage", async () => {
    const store = new Map<string, string>();
    vi.stubGlobal("sessionStorage", {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v);
      },
      removeItem: (k: string) => {
        store.delete(k);
      },
    });
    await enterDemoConsole();
    const token = getCurrentSession()!.accessToken;
    expect(store.get("cs.session.active")).toBe("1");
    expect([...store.values()].join("|")).not.toContain(token);
    vi.unstubAllGlobals();
  });
});
