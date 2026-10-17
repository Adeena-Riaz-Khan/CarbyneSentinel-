import type { Session } from "../contracts/auth";

/**
 * In-memory session store.
 * Access tokens NEVER go to localStorage (XSS).
 * sessionStorage only holds a boolean flag for “was signed in this tab”.
 */
const FLAG_KEY = "cs.session.active";

let current: Session | null = null;
let expiryTimer: ReturnType<typeof setTimeout> | null = null;
const listeners = new Set<(session: Session | null) => void>();

function notify() {
  for (const l of listeners) l(current);
}

export function getSession(): Session | null {
  return current;
}

export function getAccessToken(): string | null {
  return current?.accessToken ?? null;
}

export function setSession(session: Session, onExpire: () => void): void {
  clearExpiryTimer();
  current = session;
  try {
    sessionStorage.setItem(FLAG_KEY, "1");
  } catch {
    /* private mode */
  }
  const ms = Math.max(0, session.expiresAt - Date.now());
  expiryTimer = setTimeout(() => {
    onExpire();
  }, ms);
  notify();
}

export function clearSession(): void {
  clearExpiryTimer();
  current = null;
  try {
    sessionStorage.removeItem(FLAG_KEY);
  } catch {
    /* ignore */
  }
  notify();
}

export function hadSessionFlag(): boolean {
  try {
    return sessionStorage.getItem(FLAG_KEY) === "1";
  } catch {
    return false;
  }
}

export function onSessionChange(listener: (session: Session | null) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function clearExpiryTimer() {
  if (expiryTimer) {
    clearTimeout(expiryTimer);
    expiryTimer = null;
  }
}

/** Test helper — reset module state. */
export function __resetSessionStoreForTests() {
  clearSession();
  listeners.clear();
}
