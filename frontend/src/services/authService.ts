import {
  hasPermission,
  type AuthUser,
  type LoginInput,
  type Permission,
  type Role,
  type Session,
  type SignupInput,
  type WalletInput,
} from "../contracts/auth";
import { ApiError } from "../contracts/errors";
import { validateLogin, validateSignup, validateWalletAddress } from "../validation/forms";
import {
  clearSession,
  getSession,
  onSessionChange,
  setSession,
} from "./sessionStore";
import {
  firebaseAuthEnabled,
  firebaseCurrentSession,
  firebaseSignIn,
  firebaseSignOut,
  firebaseSignUp,
  listenFirebaseAuth,
} from "./firebaseAuthAdapter";

const SESSION_TTL_MS = 2 * 60 * 60 * 1000;
const LOCKOUT_AFTER = 5;
const LOCKOUT_MS = 15 * 60 * 1000;
const PEPPER = "carbynesentinel-demo-pepper-v1";

type StoredUser = AuthUser & { passwordHash: string };

const users = new Map<string, StoredUser>();
const failures = new Map<string, { count: number; lockedUntil: number }>();

const authListeners = new Set<(session: Session | null) => void>();
let bootstrapped = false;
let firebaseListenAttached = false;

async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function hashPassword(password: string): Promise<string> {
  return sha256Hex(`${PEPPER}:${password}`);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

function issueToken(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function toPublic(user: StoredUser): AuthUser {
  const { passwordHash: _, ...pub } = user;
  return pub;
}

function activateSession(session: Session): Session {
  setSession(session, () => {
    void signOut();
  });
  emit(session);
  return session;
}

function activate(user: AuthUser): Session {
  return activateSession({
    user,
    accessToken: issueToken(),
    expiresAt: Date.now() + SESSION_TTL_MS,
  });
}

function emit(session: Session | null) {
  for (const l of authListeners) l(session);
}

function assertNotLocked(email: string) {
  const rec = failures.get(email);
  if (rec && rec.lockedUntil > Date.now()) {
    throw new ApiError(
      "RATE_LIMIT",
      "Too many attempts. Try again in 15 minutes.",
      429,
    );
  }
}

function recordFailure(email: string) {
  const rec = failures.get(email) ?? { count: 0, lockedUntil: 0 };
  rec.count += 1;
  if (rec.count >= LOCKOUT_AFTER) {
    rec.lockedUntil = Date.now() + LOCKOUT_MS;
    rec.count = 0;
  }
  failures.set(email, rec);
}

function clearFailures(email: string) {
  failures.delete(email);
}

export function authMode(): "firebase" | "firebase-emulator" | "mock" {
  if (!firebaseAuthEnabled()) return "mock";
  return import.meta.env.VITE_USE_FIREBASE_EMULATOR === "true"
    ? "firebase-emulator"
    : "firebase";
}

export async function bootstrapDemoUsers(): Promise<void> {
  if (firebaseAuthEnabled()) {
    if (!firebaseListenAttached) {
      firebaseListenAttached = true;
      listenFirebaseAuth((session) => {
        if (session) activateSession(session);
        else {
          clearSession();
          emit(null);
        }
      });
    }
    return;
  }

  if (bootstrapped) return;
  const demos: Array<{
    email: string;
    password: string;
    name: string;
    role: Role;
    wallet: string;
  }> = [
    {
      email: "alex@carbyne.security",
      password: "Carbyne#Secure1!",
      name: "Alex Sentinel",
      role: "security_admin",
      wallet: "0x71F2...8A4C",
    },
    {
      email: "analyst@carbyne.security",
      password: "Analyst#Secure1!",
      name: "Casey Analyst",
      role: "analyst",
      wallet: "0x91A3...44B1",
    },
    {
      email: "viewer@carbyne.security",
      password: "Viewer#Secure1!",
      name: "Riley Viewer",
      role: "viewer",
      wallet: "0x22C0...09EE",
    },
  ];
  for (const d of demos) {
    const passwordHash = await hashPassword(d.password);
    users.set(d.email, {
      id: `usr_${d.role}`,
      email: d.email,
      name: d.name,
      role: d.role,
      initials: d.name
        .split(" ")
        .map((p) => p[0])
        .join("")
        .slice(0, 2)
        .toUpperCase(),
      wallet: d.wallet,
      network: "Ethereum Mainnet Fork",
      passwordHash,
    });
  }
  bootstrapped = true;
}

export async function signIn(input: LoginInput): Promise<Session> {
  await bootstrapDemoUsers();
  const parsed = validateLogin(input);
  if (!parsed.ok) {
    throw new ApiError("VALIDATION", parsed.message, 400, parsed.errors);
  }
  const { email, password } = parsed.data;
  assertNotLocked(email);

  if (firebaseAuthEnabled()) {
    try {
      const session = await firebaseSignIn(email, password);
      clearFailures(email);
      return activateSession(session);
    } catch (e) {
      if (e instanceof ApiError && e.code === "UNAUTHORIZED") recordFailure(email);
      throw e;
    }
  }

  const stored = users.get(email);
  const candidateHash = await hashPassword(password);
  const ok = stored && timingSafeEqual(stored.passwordHash, candidateHash);
  if (!ok) {
    recordFailure(email);
    throw new ApiError("UNAUTHORIZED", "Invalid email or password.", 401);
  }
  clearFailures(email);
  return activate(toPublic(stored!));
}

export async function signUp(input: SignupInput): Promise<Session> {
  await bootstrapDemoUsers();
  const parsed = validateSignup(input);
  if (!parsed.ok) {
    throw new ApiError("VALIDATION", parsed.message, 400, parsed.errors);
  }
  const { name, email, password } = parsed.data;

  if (firebaseAuthEnabled()) {
    const session = await firebaseSignUp(name, email, password);
    return activateSession(session);
  }

  if (users.has(email)) {
    throw new ApiError("CONFLICT", "An account with this email already exists.", 409);
  }
  const passwordHash = await hashPassword(password);
  const user: StoredUser = {
    id: `usr_${crypto.randomUUID()}`,
    email,
    name,
    role: "viewer",
    initials: name
      .split(/\s+/)
      .map((p) => p[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "U",
    wallet: "0x0000...0000",
    network: "Ethereum Mainnet Fork",
    passwordHash,
  };
  users.set(email, user);
  return activate(toPublic(user));
}

export async function connectWallet(input: WalletInput): Promise<Session> {
  await bootstrapDemoUsers();
  const parsed = validateWalletAddress(input.address);
  if (!parsed.ok) {
    throw new ApiError("VALIDATION", parsed.message, 400, parsed.errors);
  }
  // Wallet SIWE is not wired to Firebase yet — local analyst session for presentations.
  const address = parsed.data.address;
  const short = `${address.slice(0, 6)}...${address.slice(-4)}`;
  const user: AuthUser = {
    id: `wal_${address.toLowerCase()}`,
    email: `${address.slice(2, 8).toLowerCase()}@wallet.local`,
    name: "Wallet User",
    role: "analyst",
    initials: "WU",
    wallet: short,
    network: "Ethereum Mainnet Fork",
  };
  return activate(user);
}

/**
 * Demo console entry.
 * Firebase mode: signs in the seeded Admin account (must exist in Firebase Auth).
 * Mock mode: uses local demo admin.
 */
export async function enterDemoConsole(): Promise<Session> {
  return signIn({
    email: "alex@carbyne.security",
    password: "Carbyne#Secure1!",
  });
}

export async function signOut(): Promise<void> {
  if (firebaseAuthEnabled()) {
    try {
      await firebaseSignOut();
    } catch {
      /* still clear local session */
    }
  }
  clearSession();
  emit(null);
}

export function getCurrentSession(): Session | null {
  const s = getSession();
  if (!s) return null;
  if (s.expiresAt <= Date.now()) {
    clearSession();
    emit(null);
    return null;
  }
  return s;
}

export async function hydrateSession(): Promise<Session | null> {
  await bootstrapDemoUsers();
  if (firebaseAuthEnabled()) {
    const remote = await firebaseCurrentSession();
    if (remote) return activateSession(remote);
    return null;
  }
  return getCurrentSession();
}

export function can(permission: Permission): boolean {
  const s = getCurrentSession();
  if (!s) return false;
  return hasPermission(s.user.role, permission);
}

export function requirePermission(permission: Permission): void {
  if (!can(permission)) {
    throw new ApiError("FORBIDDEN", "You do not have permission for this action.", 403);
  }
}

export function onAuthStateChanged(listener: (session: Session | null) => void): () => void {
  authListeners.add(listener);
  const unsubStore = onSessionChange((s) => listener(s));
  return () => {
    authListeners.delete(listener);
    unsubStore();
  };
}

/** Test helpers */
export function __resetAuthForTests() {
  users.clear();
  failures.clear();
  authListeners.clear();
  bootstrapped = false;
  firebaseListenAttached = false;
  clearSession();
}

export function __forceLockoutForTests(email: string) {
  failures.set(email, { count: 0, lockedUntil: Date.now() + LOCKOUT_MS });
}
