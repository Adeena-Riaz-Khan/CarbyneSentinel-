/**
 * Seeds Auth emulator users + Firestore collections from src/data/seeds.ts
 * Prerequisites: `npm run emulators` already running.
 */
import { initializeApp } from "firebase/app";
import {
  connectAuthEmulator,
  createUserWithEmailAndPassword,
  getAuth,
  signInWithEmailAndPassword,
  updateProfile,
} from "firebase/auth";
import {
  connectFirestoreEmulator,
  doc,
  getFirestore,
  setDoc,
  writeBatch,
} from "firebase/firestore";
import { PENDING_FEED_TOTAL } from "../src/contracts/grids";
import { FS } from "../src/lib/collections";
import {
  seedBenchmark,
  seedSettings,
  seedStats,
  seedTransactions,
} from "../src/data/seeds";

const PROJECT_ID = process.env.VITE_FIREBASE_PROJECT_ID || "carbynesentinel-local";

const app = initializeApp({
  apiKey: "demo-api-key",
  authDomain: "localhost",
  projectId: PROJECT_ID,
  appId: "1:1234567890:web:localdemo",
});

const auth = getAuth(app);
const db = getFirestore(app);
connectAuthEmulator(auth, "http://127.0.0.1:9099", { disableWarnings: true });
connectFirestoreEmulator(db, "127.0.0.1", 8080);

const DEMO_USERS = [
  {
    email: "alex@carbyne.security",
    password: "Carbyne#Secure1!",
    name: "Alex Sentinel",
    role: "security_admin",
  },
  {
    email: "analyst@carbyne.security",
    password: "Analyst#Secure1!",
    name: "Casey Analyst",
    role: "analyst",
  },
  {
    email: "viewer@carbyne.security",
    password: "Viewer#Secure1!",
    name: "Riley Viewer",
    role: "viewer",
  },
] as const;

async function ensureUser(u: (typeof DEMO_USERS)[number]) {
  try {
    const cred = await createUserWithEmailAndPassword(auth, u.email, u.password);
    await updateProfile(cred.user, { displayName: u.name });
    await setDoc(doc(db, FS.users, cred.user.uid), {
      email: u.email,
      name: u.name,
      role: u.role,
      createdAt: new Date().toISOString(),
    });
    console.log(`  + auth user ${u.email} (${u.role})`);
  } catch (e) {
    const code = (e as { code?: string }).code;
    if (code === "auth/email-already-in-use") {
      const cred = await signInWithEmailAndPassword(auth, u.email, u.password);
      await setDoc(
        doc(db, FS.users, cred.user.uid),
        {
          email: u.email,
          name: u.name,
          role: u.role,
          updatedAt: new Date().toISOString(),
        },
        { merge: true },
      );
      console.log(`  ~ auth user exists ${u.email}`);
      return;
    }
    throw e;
  }
}

async function seedCollections() {
  await setDoc(doc(db, FS.stats.col, FS.stats.doc), {
    ...seedStats,
    pendingTotal: PENDING_FEED_TOTAL,
  });
  await setDoc(doc(db, FS.settings.col, FS.settings.doc), seedSettings);
  // Firestore forbids nested arrays — store matrix as rows of { cells: number[] }.
  const { matrix, latencyStages, ...benchRest } = seedBenchmark;
  await setDoc(doc(db, FS.benchmarks.col, FS.benchmarks.doc), {
    ...benchRest,
    matrixRows: matrix.map((cells) => ({ cells })),
    latencyStages,
  });

  const batch = writeBatch(db);
  for (const tx of seedTransactions) {
    const { id, ...rest } = tx;
    batch.set(doc(db, FS.transactions, id), rest);
  }
  await batch.commit();
  console.log("  + stats/global, settings/pipeline, benchmarks/latest");
  console.log(`  + ${seedTransactions.length} transactions`);
}

async function main() {
  console.log(`Seeding Firebase emulators (project=${PROJECT_ID})…`);
  console.log("Auth users:");
  for (const u of DEMO_USERS) {
    await ensureUser(u);
  }
  console.log("Firestore collections:");
  await seedCollections();
  console.log("Done. Emulator UI: http://127.0.0.1:4000");
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  console.error("\nIs the emulator running?  npm run emulators");
  process.exit(1);
});
