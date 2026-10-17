import { describe, expect, it } from "vitest";
import { seedSettings } from "../data/seeds";
import {
  sanitizeSearchQuery,
  validateLogin,
  validateSettingsPatch,
  validateSpendingCeiling,
  validateWalletAddress,
} from "../validation/forms";

describe("auth form validation (BR-AUTH-1)", () => {
  it("rejects empty email", () => {
    const r = validateLogin({ email: "", password: "Carbyne#Secure1!" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.email).toMatch(/valid work email/i);
  });

  it("rejects weak password", () => {
    const r = validateLogin({ email: "alex@carbyne.security", password: "short" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.password).toMatch(/12 characters/i);
  });

  it("accepts contract-valid credentials", () => {
    const r = validateLogin({
      email: "alex@carbyne.security",
      password: "Carbyne#Secure1!",
    });
    expect(r.ok).toBe(true);
  });
});

describe("settings validation (BR-SET-1..3)", () => {
  it("rejects weight sum != 100", () => {
    const r = validateSettingsPatch(
      { fingerprintWeight: 40, gcnWeight: 40, llmWeight: 40 },
      seedSettings,
    );
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.message).toMatch(/100%/);
  });

  it("rejects timeout boundary 199", () => {
    const r = validateSettingsPatch({ timeoutMs: 199 }, seedSettings);
    expect(r.ok).toBe(false);
  });

  it("rejects http webhook", () => {
    const r = validateSettingsPatch(
      { webhookUrl: "http://evil.example/hook" },
      seedSettings,
    );
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.webhookUrl).toMatch(/HTTPS/);
  });

  it("accepts valid patch", () => {
    const r = validateSettingsPatch(
      {
        fingerprintWeight: 25,
        gcnWeight: 32,
        llmWeight: 43,
        timeoutMs: 450,
        webhookUrl: "https://api.carbyne.internal/v1/incidents",
      },
      seedSettings,
    );
    expect(r.ok).toBe(true);
  });
});

describe("boundary values", () => {
  it("rejects spending ceiling 0", () => {
    expect(validateSpendingCeiling(0).ok).toBe(false);
  });

  it("accepts eth address", () => {
    const r = validateWalletAddress("0x71F28a4c9e2b1d3f4a5b6c7d8e9f0a1b2c3d4e5f");
    expect(r.ok).toBe(true);
  });

  it("sanitizes search query length and controls", () => {
    const q = sanitizeSearchQuery(`ab\u0000${"x".repeat(200)}`);
    expect(q.includes("\u0000")).toBe(false);
    expect(q.length).toBe(128);
  });
});
