import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApiError, type Api, type User } from "./api";
import { Progress } from "./ui";

const EMAIL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;
const EMAIL_MAX = 254;
const PASSWORD_MAX = 128;

export type LoginErrors = { email?: string; password?: string };

/** The same rules as the server (app/auth/validation.py), checked before anything is sent. */
export function validateLogin(email: string, password: string): LoginErrors {
  const errors: LoginErrors = {};
  const trimmed = email.trim();
  if (!trimmed) errors.email = "Enter your email address.";
  else if (trimmed.length > EMAIL_MAX || !EMAIL.test(trimmed)) errors.email = "Enter a valid email address.";
  if (!password) errors.password = "Enter your password.";
  else if (password.length > PASSWORD_MAX) errors.password = `Use at most ${PASSWORD_MAX} characters.`;
  return errors;
}

export function LoginPage({ api, onSignedIn }: { api: Api; onSignedIn: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [shown, setShown] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  // Shown as soon as a field has been left, and for both fields after a submit attempt.
  const errors = validateLogin(email, password);
  const showEmail = touched.email ? errors.email : undefined;
  const showPassword = touched.password ? errors.password : undefined;

  const watchCaps = (event: KeyboardEvent<HTMLInputElement>) =>
    setCapsLock(event.getModifierState("CapsLock"));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setServerError(null);
    setTouched({ email: true, password: true });
    if (errors.email) return emailRef.current?.focus();
    if (errors.password) return passwordRef.current?.focus();
    setBusy(true);
    try {
      onSignedIn(await api.login(email.trim(), password));
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : "Something went wrong. Try again.");
      setPassword("");
      passwordRef.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <main data-slot="login">
      <form data-slot="login-card" onSubmit={submit} noValidate aria-labelledby="login-title">
        <span data-slot="logo" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
            <path d="M14 3v5h5" />
            <path d="M9 13h6" />
            <path d="M9 17h4" />
          </svg>
        </span>
        <h1 id="login-title" data-slot="panel-title">Sign in</h1>
        <p data-slot="panel-lede">ContractTracker. Every deadline, with the sentence that sets it.</p>

        {serverError && (
          <p data-slot="notice" data-tone="bad" role="alert">
            {serverError}
          </p>
        )}

        <div data-slot="field-group">
          <label data-slot="label" htmlFor="login-email">Email</label>
          <input
            id="login-email"
            ref={emailRef}
            data-slot="input"
            type="email"
            name="email"
            autoComplete="username"
            inputMode="email"
            autoFocus
            maxLength={EMAIL_MAX}
            value={email}
            aria-invalid={showEmail ? true : undefined}
            aria-describedby={showEmail ? "login-email-error" : undefined}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, email: true }))}
          />
          {showEmail && <p id="login-email-error" data-slot="field-error">{showEmail}</p>}
        </div>

        <div data-slot="field-group">
          <label data-slot="label" htmlFor="login-password">Password</label>
          <div data-slot="password-row">
            <input
              id="login-password"
              ref={passwordRef}
              data-slot="input"
              type={shown ? "text" : "password"}
              name="password"
              autoComplete="current-password"
              maxLength={PASSWORD_MAX}
              value={password}
              aria-invalid={showPassword ? true : undefined}
              aria-describedby={showPassword ? "login-password-error" : undefined}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, password: true }))}
              onKeyUp={watchCaps}
              onKeyDown={watchCaps}
            />
            <button
              type="button"
              data-slot="button"
              aria-pressed={shown}
              aria-label={shown ? "Hide password" : "Show password"}
              onClick={() => setShown((s) => !s)}
            >
              {shown ? "Hide" : "Show"}
            </button>
          </div>
          {showPassword && <p id="login-password-error" data-slot="field-error">{showPassword}</p>}
          {capsLock && <p data-slot="hint">Caps Lock is on.</p>}
        </div>

        <button data-slot="button" data-primary type="submit" disabled={busy} aria-busy={busy}>
          Sign in
        </button>
        {busy && <Progress label="Signing in" />}
        <p data-slot="hint">There is no sign-up. Ask the owner to create your account.</p>
      </form>
    </main>
  );
}
