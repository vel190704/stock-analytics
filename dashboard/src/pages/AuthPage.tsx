import { FormEvent, useMemo, useState } from 'react';
import { api, clearAuthToken, getAuthToken, setAuthToken } from '@/api/client';

function extractAuthError(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string | string[] } } })?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.join(', ');
  }
  if (typeof detail === 'string' && detail.trim().length > 0) {
    return detail;
  }
  return 'Authentication request failed';
}

export function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tokenVersion, setTokenVersion] = useState(0);

  const token = useMemo(() => getAuthToken(), [tokenVersion]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      const response =
        mode === 'register'
          ? await api.auth.register(email.trim().toLowerCase(), password)
          : await api.auth.login(email.trim().toLowerCase(), password);

      setAuthToken(response.access_token);
      setTokenVersion((v) => v + 1);
      setMessage(`${mode === 'register' ? 'Registration' : 'Login'} successful. JWT saved for protected API calls.`);
      setPassword('');
    } catch (err) {
      setError(extractAuthError(err));
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    clearAuthToken();
    setTokenVersion((v) => v + 1);
    setMessage('Logged out locally.');
    setError(null);
  };

  return (
    <div className="mx-auto grid w-full max-w-5xl grid-cols-1 gap-4 xl:grid-cols-[420px_1fr]">
      <div className="rounded-lg border border-border bg-bg-secondary p-5">
        <h1 className="mb-1 font-sans text-2xl font-semibold text-text-primary">Authentication</h1>
        <p className="mb-4 text-sm text-text-muted">
          Authenticate once to enable protected write endpoints for alerts, portfolio, and backtesting.
        </p>

        <div className="mb-4 inline-flex rounded-md border border-border bg-bg-card p-1">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`rounded px-3 py-1.5 font-mono text-xs ${mode === 'login' ? 'bg-accent text-black' : 'text-text-muted'}`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`rounded px-3 py-1.5 font-mono text-xs ${mode === 'register' ? 'bg-accent text-black' : 'text-text-muted'}`}
          >
            Register
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Email</label>
            <input
              data-testid="auth-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="mb-1 block font-mono text-xs text-text-muted">Password</label>
            <input
              data-testid="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm"
              placeholder="••••••••"
            />
          </div>

          <button
            data-testid="auth-submit"
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-accent px-4 py-2 font-mono text-xs font-semibold text-black disabled:opacity-70"
          >
            {busy ? 'Please wait…' : mode === 'register' ? 'Create Account + Issue JWT' : 'Login + Issue JWT'}
          </button>
        </form>

        {error && <p className="mt-3 text-sm text-loss">{error}</p>}
        {message && <p className="mt-3 text-sm text-gain">{message}</p>}
      </div>

      <div className="rounded-lg border border-border bg-bg-secondary p-5">
        <h2 className="mb-3 font-sans text-lg font-semibold text-text-primary">Session Token</h2>
        {token ? (
          <>
            <p className="mb-2 text-xs text-text-muted">JWT present in localStorage.</p>
            <pre className="max-h-40 overflow-auto rounded border border-border bg-bg-card p-3 font-mono text-[11px] text-text-primary">
              {token}
            </pre>
            <button
              type="button"
              onClick={logout}
              className="mt-3 rounded border border-border px-3 py-2 font-mono text-xs text-text-primary"
            >
              Logout (Clear Token)
            </button>
          </>
        ) : (
          <p className="text-sm text-text-muted">No JWT token stored yet.</p>
        )}

        <div className="mt-5 rounded-md border border-border bg-bg-card p-3">
          <h3 className="mb-2 font-mono text-xs uppercase tracking-wide text-text-muted">Protected Endpoints</h3>
          <ul className="space-y-1 font-mono text-xs text-text-primary">
            <li>POST /alerts/rules</li>
            <li>POST /portfolio/positions</li>
            <li>POST /portfolio/trades</li>
            <li>POST /backtest/run</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
