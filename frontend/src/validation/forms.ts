import type { SettingsDoc } from "../contracts/domain";

export type FieldErrors = Record<string, string>;

export type ValidationResult<T> =
  | { ok: true; data: T }
  | { ok: false; errors: FieldErrors; message: string };

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PASSWORD_RE = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$/;
const ETH_RE = /^0x[a-fA-F0-9]{40}$/;

export function validateEmail(email: string): string | null {
  const v = email.trim();
  if (!v) return "Enter a valid work email.";
  if (v.length > 254 || !EMAIL_RE.test(v)) return "Enter a valid work email.";
  return null;
}

export function validatePassword(password: string): string | null {
  if (!password) return "Password must be at least 12 characters and include upper, lower, number, and symbol.";
  if (!PASSWORD_RE.test(password)) {
    return "Password must be at least 12 characters and include upper, lower, number, and symbol.";
  }
  return null;
}

export function validateName(name: string): string | null {
  const v = name.trim();
  if (v.length < 2 || v.length > 80) return "Enter your full name.";
  return null;
}

export function validateLogin(input: {
  email: string;
  password: string;
}): ValidationResult<{ email: string; password: string }> {
  const errors: FieldErrors = {};
  const e = validateEmail(input.email);
  const p = validatePassword(input.password);
  if (e) errors.email = e;
  if (p) errors.password = p;
  if (Object.keys(errors).length) {
    return { ok: false, errors, message: "Fix the highlighted fields." };
  }
  return { ok: true, data: { email: input.email.trim().toLowerCase(), password: input.password } };
}

export function validateSignup(input: {
  name: string;
  email: string;
  password: string;
}): ValidationResult<{ name: string; email: string; password: string }> {
  const errors: FieldErrors = {};
  const n = validateName(input.name);
  const e = validateEmail(input.email);
  const p = validatePassword(input.password);
  if (n) errors.name = n;
  if (e) errors.email = e;
  if (p) errors.password = p;
  if (Object.keys(errors).length) {
    return { ok: false, errors, message: "Fix the highlighted fields." };
  }
  return {
    ok: true,
    data: {
      name: input.name.trim(),
      email: input.email.trim().toLowerCase(),
      password: input.password,
    },
  };
}

export function validateWalletAddress(address: string): ValidationResult<{ address: string }> {
  const v = address.trim();
  if (!ETH_RE.test(v)) {
    return {
      ok: false,
      errors: { address: "Enter a valid Ethereum address." },
      message: "Enter a valid Ethereum address.",
    };
  }
  return { ok: true, data: { address: v } };
}

export function validateSettingsPatch(
  patch: Partial<SettingsDoc>,
  current: SettingsDoc,
): ValidationResult<Partial<SettingsDoc>> {
  const next = { ...current, ...patch };
  const errors: FieldErrors = {};

  const sum = next.fingerprintWeight + next.gcnWeight + next.llmWeight;
  if (sum !== 100) {
    errors.weights = "Combined weight must equal 100%.";
  }
  for (const key of ["fingerprintWeight", "gcnWeight", "llmWeight"] as const) {
    const n = next[key];
    if (n < 0 || n > 100) errors[key] = "Weight must be between 0 and 100.";
  }
  if (!Number.isInteger(next.timeoutMs) || next.timeoutMs < 200 || next.timeoutMs > 1000) {
    errors.timeoutMs = "Timeout must be between 200ms and 1000ms.";
  }
  if (patch.webhookUrl !== undefined) {
    try {
      const u = new URL(next.webhookUrl);
      if (u.protocol !== "https:") errors.webhookUrl = "Webhook URL must use HTTPS.";
      if (next.webhookUrl.length > 2048) errors.webhookUrl = "Webhook URL must use HTTPS.";
    } catch {
      errors.webhookUrl = "Webhook URL must use HTTPS.";
    }
  }
  if (Object.keys(errors).length) {
    return {
      ok: false,
      errors,
      message: errors.weights ?? errors.timeoutMs ?? errors.webhookUrl ?? "Invalid settings.",
    };
  }
  return { ok: true, data: patch };
}

export function validateSpendingCeiling(value: number): ValidationResult<{ limit: number }> {
  if (!Number.isFinite(value) || value <= 0 || value > 10_000_000) {
    return {
      ok: false,
      errors: { limit: "Spending ceiling must be greater than zero." },
      message: "Spending ceiling must be greater than zero.",
    };
  }
  return { ok: true, data: { limit: value } };
}

/** Search box: strip controls, cap length (BR-MON-1). */
export function sanitizeSearchQuery(raw: string): string {
  return raw.replace(/[\u0000-\u001F\u007F]/g, "").slice(0, 128);
}
