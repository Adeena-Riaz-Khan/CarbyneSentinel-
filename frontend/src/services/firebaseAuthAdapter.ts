import {
  createUserWithEmailAndPassword,
  onAuthStateChanged as fbOnAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as fbSignOut,
  updateProfile,
  type User,
} from "firebase/auth";
import { doc, getDoc, setDoc } from "firebase/firestore";
import type { AuthUser, Role, Session } from "../contracts/auth";
import { ApiError } from "../contracts/errors";
import { getFirebaseAuth, getFirebaseDb, isFirebaseConfigured } from "../lib/firebaseApp";

const DEFAULT_NETWORK = "Ethereum Mainnet Fork";

/** Presentation role map when custom claims / Firestore role are absent. */
const EMAIL_ROLE_MAP: Record<string, Role> = {
  "alex@carbyne.security": "security_admin",
  "analyst@carbyne.security": "analyst",
  "viewer@carbyne.security": "viewer",
};

function adminEmailAllowlist(): Set<string> {
  const raw = import.meta.env.VITE_FIREBASE_ADMIN_EMAILS?.trim() ?? "";
  return new Set(
    raw
      .split(",")
      .map((e: string) => e.trim().toLowerCase())
      .filter(Boolean),
  );
}

function initialsFrom(name: string, email: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0]![0]}${parts[1]![0]}`.toUpperCase();
  if (parts.length === 1 && parts[0]!.length >= 2) return parts[0]!.slice(0, 2).toUpperCase();
  return email.slice(0, 2).toUpperCase();
}

function mapFirebaseError(code: string): ApiError {
  switch (code) {
    case "auth/invalid-credential":
    case "auth/wrong-password":
    case "auth/user-not-found":
    case "auth/invalid-email":
      return new ApiError("UNAUTHORIZED", "Invalid email or password.", 401);
    case "auth/email-already-in-use":
      return new ApiError("CONFLICT", "An account with this email already exists.", 409);
    case "auth/weak-password":
      return new ApiError(
        "VALIDATION",
        "Password must be at least 12 characters and include upper, lower, number, and symbol.",
        400,
        { password: "Password must be at least 12 characters and include upper, lower, number, and symbol." },
      );
    case "auth/too-many-requests":
      return new ApiError("RATE_LIMIT", "Too many attempts. Try again in 15 minutes.", 429);
    case "auth/network-request-failed":
      return new ApiError("NETWORK", "Network error talking to Firebase Auth.", 503);
    default:
      return new ApiError("INTERNAL", "Authentication failed. Try again.", 500);
  }
}

async function resolveRole(user: User, email: string): Promise<Role> {
  const admins = adminEmailAllowlist();
  if (admins.has(email.toLowerCase())) return "security_admin";

  try {
    const token = await user.getIdTokenResult(true);
    const claim = token.claims.role;
    if (claim === "security_admin" || claim === "analyst" || claim === "viewer") {
      return claim;
    }
  } catch {
    /* ignore claim fetch errors — fall through */
  }

  try {
    const snap = await getDoc(doc(getFirebaseDb(), "users", user.uid));
    const role = snap.data()?.role;
    if (role === "security_admin" || role === "analyst" || role === "viewer") {
      return role;
    }
  } catch {
    /* Firestore optional for presentation */
  }

  return EMAIL_ROLE_MAP[email.toLowerCase()] ?? "viewer";
}

async function toAuthUser(user: User): Promise<AuthUser> {
  const email = (user.email ?? "").toLowerCase();
  const name = user.displayName || email.split("@")[0] || "User";
  const role = await resolveRole(user, email);
  return {
    id: user.uid,
    email,
    name,
    role,
    initials: initialsFrom(name, email),
    wallet: `0x${user.uid.replace(/-/g, "").slice(0, 4)}...${user.uid.replace(/-/g, "").slice(-4)}`,
    network: DEFAULT_NETWORK,
  };
}

async function toSession(user: User): Promise<Session> {
  const tokenResult = await user.getIdTokenResult();
  const accessToken = tokenResult.token;
  const expiresAt = new Date(tokenResult.expirationTime).getTime();
  const authUser = await toAuthUser(user);
  return { user: authUser, accessToken, expiresAt };
}

async function ensureUserProfile(user: User, name: string, role: Role): Promise<void> {
  try {
    const ref = doc(getFirebaseDb(), "users", user.uid);
    const existing = await getDoc(ref);
    if (existing.exists()) return;
    await setDoc(ref, {
      email: user.email,
      name,
      role,
      createdAt: new Date().toISOString(),
    });
  } catch {
    /* Profile write is best-effort for presentation */
  }
}

export function firebaseAuthEnabled(): boolean {
  return isFirebaseConfigured();
}

export async function firebaseSignIn(email: string, password: string): Promise<Session> {
  try {
    const cred = await signInWithEmailAndPassword(getFirebaseAuth(), email, password);
    return toSession(cred.user);
  } catch (e) {
    const code = (e as { code?: string }).code ?? "";
    throw mapFirebaseError(code);
  }
}

export async function firebaseSignUp(
  name: string,
  email: string,
  password: string,
): Promise<Session> {
  try {
    const cred = await createUserWithEmailAndPassword(getFirebaseAuth(), email, password);
    await updateProfile(cred.user, { displayName: name });
    const role: Role = EMAIL_ROLE_MAP[email.toLowerCase()] ?? "viewer";
    await ensureUserProfile(cred.user, name, role);
    return toSession(cred.user);
  } catch (e) {
    const code = (e as { code?: string }).code ?? "";
    throw mapFirebaseError(code);
  }
}

export async function firebaseSignOut(): Promise<void> {
  if (!firebaseAuthEnabled()) return;
  await fbSignOut(getFirebaseAuth());
}

/**
 * Subscribe to Firebase Auth persistence (IndexedDB).
 * Returns unsubscribe. No-op disposer when Firebase is off.
 */
export function listenFirebaseAuth(
  onSession: (session: Session | null) => void,
): () => void {
  if (!firebaseAuthEnabled()) {
    onSession(null);
    return () => undefined;
  }
  return fbOnAuthStateChanged(getFirebaseAuth(), (user) => {
    if (!user) {
      onSession(null);
      return;
    }
    void toSession(user)
      .then(onSession)
      .catch(() => onSession(null));
  });
}

export async function firebaseCurrentSession(): Promise<Session | null> {
  if (!firebaseAuthEnabled()) return null;
  const user = getFirebaseAuth().currentUser;
  if (!user) return null;
  return toSession(user);
}
