# Firebase Auth (presentation setup)

The UI keeps the same Figma screens. Auth switches automatically:

| Config | Mode | Footer on login |
|--------|------|-----------------|
| No `VITE_FIREBASE_*` | Mock (local demo users) | “Demo auth…” |
| Env filled | **Firebase Authentication** | “Secured with Firebase Authentication” |

## 1. Create a Firebase project

1. Open [Firebase Console](https://console.firebase.google.com/)
2. Create project (e.g. `carbynesentinel-demo`)
3. Add a **Web** app → copy the config object
4. **Build → Authentication → Get started → Email/Password → Enable**
5. (Optional) **Firestore** → create database (test mode for demos only)

## 2. Configure the frontend

```bash
cd frontend
cp .env.example .env.local
```

Fill:

```env
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=YOUR_PROJECT.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=YOUR_PROJECT
VITE_FIREBASE_STORAGE_BUCKET=YOUR_PROJECT.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

Restart `npm run dev`.

## 3. Seed demo users in Firebase Auth

**Authentication → Users → Add user** (or Sign up from the UI):

| Email | Password | Role (auto) |
|-------|----------|-------------|
| alex@carbyne.security | Carbyne#Secure1! | security_admin |
| analyst@carbyne.security | Analyst#Secure1! | analyst |
| viewer@carbyne.security | Viewer#Secure1! | viewer |

Role resolution order:

1. `VITE_FIREBASE_ADMIN_EMAILS` allowlist → admin  
2. ID token custom claim `role` (production)  
3. Firestore `users/{uid}.role`  
4. Email map above  
5. Default `viewer`

On first Sign up, a `users/{uid}` doc is written when Firestore is available.

## 4. Present

```bash
npm run dev
```

Login screen should show **Secured with Firebase Authentication**.  
“View live console” uses the Admin demo account (must exist in Firebase).

## 5. What this is / isn’t

**Good for:** investor/demo day, showing real AuthN, session restore, RBAC in UI + API mock.

**Still needed before production:** Cloud Functions / custom claims for roles, App Check, security rules, real backend enforcing ID tokens, no client-only permission trust.
