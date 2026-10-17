import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner } from "../components/ErrorBanner";

function Brand() {
  return (
    <div className="brand">
      <svg className="brand-mark" viewBox="0 0 38 38" aria-hidden="true">
        <path d="M19 2.5 33 8v9.2c0 9-6 15.2-14 18.3C11 32.4 5 26.2 5 17.2V8l14-5.5Z" />
        <circle cx="19" cy="18" r="6" />
        <path d="M19 12V8M13.8 21l-3.7 2.2M24.2 21l3.7 2.2" />
      </svg>
      <span>
        Carbyne<span>Sentinel</span>
      </span>
    </div>
  );
}

const DEMO_WALLET = "0x71F28a4c9e2b1d3f4a5b6c7d8e9f0a1b2c3d4e5f";

export default function AuthPage({ onEnter }: { onEnter: () => void }) {
  const {
    signIn,
    signUp,
    connectWallet,
    enterDemoConsole,
    error,
    fieldErrors,
    clearError,
    authMode,
  } = useAuth();
  const [signup, setSignup] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const email = String(fd.get("email") ?? "");
    const password = String(fd.get("password") ?? "");
    const name = String(fd.get("name") ?? "");
    setBusy(true);
    const ok = signup
      ? await signUp({ name, email, password })
      : await signIn({ email, password });
    setBusy(false);
    if (ok) onEnter();
  }

  async function onDemo() {
    setBusy(true);
    const ok = await enterDemoConsole();
    setBusy(false);
    if (ok) onEnter();
  }

  async function onWallet() {
    setBusy(true);
    const ok = await connectWallet({ address: DEMO_WALLET });
    setBusy(false);
    if (ok) onEnter();
  }

  return (
    <main className="auth-shell">
      <section className="auth-form-side">
        <button className="back-app" type="button" onClick={() => void onDemo()} disabled={busy}>
          View live console
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <path d="M5 12h14M14 7l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <div className="auth-card">
          <div className="mobile-brand">
            <Brand />
          </div>
          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={!signup}
              className={!signup ? "active" : ""}
              onClick={() => {
                setSignup(false);
                clearError();
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={signup}
              className={signup ? "active" : ""}
              onClick={() => {
                setSignup(true);
                clearError();
              }}
            >
              Sign up
            </button>
          </div>
          <h2>{signup ? "Create your workspace" : "Welcome back"}</h2>
          <p>
            {signup
              ? "Start screening transactions in minutes."
              : "Sign in to access your security operations console."}
          </p>
          {error ? <ErrorBanner message={error} onDismiss={clearError} /> : null}
          <form onSubmit={(e) => void submit(e)} noValidate>
            {signup && (
              <label className="form-field">
                <span>Full name</span>
                <input name="name" placeholder="Alex Morgan" autoComplete="name" />
                {fieldErrors.name ? <em className="field-error">{fieldErrors.name}</em> : null}
              </label>
            )}
            <label className="form-field">
              <span>Work email</span>
              <input
                name="email"
                type="email"
                placeholder="name@company.com"
                autoComplete="email"
                defaultValue="alex@carbyne.security"
              />
              {fieldErrors.email ? <em className="field-error">{fieldErrors.email}</em> : null}
            </label>
            <label className="form-field">
              <span>Password</span>
              <input
                name="password"
                type="password"
                placeholder="••••••••••••"
                autoComplete={signup ? "new-password" : "current-password"}
                defaultValue="Carbyne#Secure1!"
              />
              {fieldErrors.password ? <em className="field-error">{fieldErrors.password}</em> : null}
            </label>
            <div className="form-helper">
              <label>
                <input type="checkbox" defaultChecked /> Remember me
              </label>
              <button type="button">Forgot password?</button>
            </div>
            <button className="auth-submit" type="submit" disabled={busy}>
              {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M5 12h14M14 7l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </form>
          <div className="or">
            <span />
            or
            <span />
          </div>
          <button className="wallet-btn" type="button" onClick={() => void onWallet()} disabled={busy}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
              <path d="M4 7h15a2 2 0 0 1 2 2v10H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h12" strokeLinecap="round" />
              <path d="M16 12h5v4h-5a2 2 0 0 1 0-4Z" />
            </svg>
            Connect Web3 wallet
            <small>MetaMask · Rabby</small>
          </button>
          <p className="terms">
            By continuing, you agree to our <u>Terms of Service</u> and <u>Privacy Policy</u>.
          </p>
          <p className="terms" style={{ marginTop: 8 }}>
            {authMode === "firebase-emulator"
              ? "Local Firebase Emulator · Auth + Firestore seeds"
              : authMode === "firebase"
                ? "Secured with Firebase Authentication"
                : "Demo auth (use npm run emulators for local Firebase)"}
          </p>
        </div>
      </section>

      <section className="auth-branding">
        <div className="auth-branding-top">
          <Brand />
        </div>
        <div className="auth-message">
          <div className="eyebrow">EVADE THE EVASION</div>
          <h1>
            Every transaction.
            <br />
            Under 500ms.
          </h1>
          <p>
            Real-time, evasion-resistant blockchain security powered by fused code, structure, and
            semantic intelligence.
          </p>
          <div className="signal-pills">
            <span>
              <i />
              Fingerprint
            </span>
            <span>
              <i />
              Structural GCN
            </span>
            <span>
              <i />
              Semantic LLM
            </span>
          </div>
        </div>
        <div className="auth-proof">
          <span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
              <path d="M12 3 20 6v5c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6l8-3Z" />
              <path d="m9 12 2 2 4-5" />
            </svg>
          </span>
          <p>
            <b>1.8B+ transactions screened</b>
            <small>Protecting critical Web3 infrastructure</small>
          </p>
        </div>
      </section>
    </main>
  );
}
