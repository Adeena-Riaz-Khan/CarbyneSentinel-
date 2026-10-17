/**
 * Firebase app bootstrap.
 * - Emulator mode: VITE_USE_FIREBASE_EMULATOR=true (no cloud keys required)
 * - Cloud mode: VITE_FIREBASE_* from Console
 * - Otherwise: mock auth / in-memory API
 */
import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import { connectAuthEmulator, getAuth, type Auth } from "firebase/auth";
import { connectFirestoreEmulator, getFirestore, type Firestore } from "firebase/firestore";

export type FirebaseConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket?: string;
  messagingSenderId?: string;
  appId: string;
};

export function isEmulatorMode(): boolean {
  return import.meta.env.VITE_USE_FIREBASE_EMULATOR === "true";
}

function readConfig(): FirebaseConfig | null {
  if (isEmulatorMode()) {
    return {
      apiKey: "demo-api-key",
      authDomain: "localhost",
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim() || "carbynesentinel-local",
      storageBucket: "carbynesentinel-local.appspot.com",
      messagingSenderId: "1234567890",
      appId: "1:1234567890:web:localdemo",
    };
  }

  const apiKey = import.meta.env.VITE_FIREBASE_API_KEY?.trim();
  const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.trim();
  const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim();
  const appId = import.meta.env.VITE_FIREBASE_APP_ID?.trim();
  if (!apiKey || !authDomain || !projectId || !appId) return null;
  return {
    apiKey,
    authDomain,
    projectId,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET?.trim() || undefined,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID?.trim() || undefined,
    appId,
  };
}

const config = readConfig();

/** True when Firebase Auth should be used (emulator or cloud). */
export function isFirebaseConfigured(): boolean {
  if (import.meta.env.VITE_USE_MOCK_AUTH === "true") return false;
  return config !== null;
}

/** True when API data should come from Firestore (emulator recommended). */
export function isFirestoreDataEnabled(): boolean {
  if (import.meta.env.VITE_USE_MOCK_AUTH === "true") return false;
  if (isEmulatorMode()) return true;
  return import.meta.env.VITE_USE_FIRESTORE_DATA === "true" && isFirebaseConfigured();
}

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let db: Firestore | null = null;
let emulatorsConnected = false;

export function getFirebaseApp(): FirebaseApp {
  if (!config) throw new Error("Firebase is not configured.");
  if (!app) {
    app = getApps().length ? getApps()[0]! : initializeApp(config);
  }
  return app;
}

function connectEmulatorsOnce(a: Auth, f: Firestore) {
  if (!isEmulatorMode() || emulatorsConnected) return;
  connectAuthEmulator(a, "http://127.0.0.1:9099", { disableWarnings: true });
  connectFirestoreEmulator(f, "127.0.0.1", 8080);
  emulatorsConnected = true;
}

export function getFirebaseAuth(): Auth {
  if (!auth) {
    auth = getAuth(getFirebaseApp());
    if (isEmulatorMode()) {
      // Ensure Firestore is created so both emulators connect together.
      const f = getFirestore(getFirebaseApp());
      db = f;
      connectEmulatorsOnce(auth, f);
    }
  }
  return auth;
}

export function getFirebaseDb(): Firestore {
  if (!db) {
    db = getFirestore(getFirebaseApp());
    if (isEmulatorMode()) {
      const a = getAuth(getFirebaseApp());
      auth = a;
      connectEmulatorsOnce(a, db);
    }
  }
  return db;
}

export function getFirebaseProjectId(): string | null {
  return config?.projectId ?? null;
}

export function authBackendLabel(): "firebase-emulator" | "firebase" | "mock" {
  if (!isFirebaseConfigured()) return "mock";
  if (isEmulatorMode()) return "firebase-emulator";
  return "firebase";
}
