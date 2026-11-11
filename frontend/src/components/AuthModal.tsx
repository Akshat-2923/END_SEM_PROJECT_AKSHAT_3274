/**
 * Authentication Modal Component.
 * Supports live Supabase credentials, pre-configured development hydrologist sessions,
 * and direct Bearer JWT token input.
 */

import React, { useState } from 'react';
import { X, Shield, Key, UserCheck, AlertTriangle, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const {
    isSupabaseLive,
    signInWithSupabase,
    signUpWithSupabase,
    signInWithToken,
    signInDevAccount,
    error,
    clearError,
  } = useAuth();

  const isDevEnvironment = import.meta.env.DEV;
  const [mode, setMode] = useState<'dev' | 'supabase' | 'token'>(
    isDevEnvironment ? 'dev' : isSupabaseLive ? 'supabase' : 'token'
  );
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [customToken, setCustomToken] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localSuccess, setLocalSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSupabaseAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setLocalSuccess(null);
    clearError();
    try {
      if (isSignUp) {
        await signUpWithSupabase(email, password, fullName);
        setLocalSuccess('Account created and authenticated successfully.');
      } else {
        await signInWithSupabase(email, password);
        setLocalSuccess('Signed in successfully.');
      }
      setTimeout(() => {
        onClose();
      }, 700);
    } catch {
      // error is handled in context
    } finally {
      setSubmitting(false);
    }
  };

  const handleDevLogin = async (role: 'user' | 'admin') => {
    setSubmitting(true);
    setLocalSuccess(null);
    clearError();
    try {
      await signInDevAccount(role);
      setLocalSuccess(`Authenticated as ${role === 'admin' ? 'GIS Operations Lead (Admin)' : 'Dr. Gomti Hydrologist (User)'}.`);
      setTimeout(() => {
        onClose();
      }, 600);
    } catch {
      // error handled in context
    } finally {
      setSubmitting(false);
    }
  };

  const handleCustomTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customToken.trim()) return;
    setSubmitting(true);
    setLocalSuccess(null);
    clearError();
    try {
      await signInWithToken(customToken.trim());
      setLocalSuccess('Custom Bearer JWT validated and authenticated.');
      setTimeout(() => {
        onClose();
      }, 600);
    } catch {
      // error handled in context
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="flex-center gap-2">
            <Shield size={20} className="text-forest" />
            <h2 className="modal-title">DharaScope Authentication</h2>
          </div>
          <button onClick={onClose} className="btn btn-icon btn-ghost" aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>

        {/* Mode Selector Tabs */}
        <div className="tab-bar">
          {isDevEnvironment && (
            <button
              onClick={() => {
                setMode('dev');
                clearError();
              }}
              className={`tab-btn ${mode === 'dev' ? 'tab-btn-active' : ''}`}
            >
              <UserCheck size={14} />
              <span>Developer / Hydrologist</span>
            </button>
          )}
          <button
            onClick={() => {
              setMode('token');
              clearError();
            }}
            className={`tab-btn ${mode === 'token' ? 'tab-btn-active' : ''}`}
          >
            <Key size={14} />
            <span>Bearer JWT</span>
          </button>
          <button
            onClick={() => {
              setMode('supabase');
              clearError();
            }}
            className={`tab-btn ${mode === 'supabase' ? 'tab-btn-active' : ''}`}
          >
            <Shield size={14} />
            <span>Supabase Cloud {isSupabaseLive ? '(Active)' : '(Mock/Offline)'}</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {error && (
            <div className="alert alert-error">
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}

          {localSuccess && (
            <div className="alert alert-success">
              <CheckCircle size={16} />
              <span>{localSuccess}</span>
            </div>
          )}

          {/* Dev Preset Mode - Only in Development */}
          {isDevEnvironment && mode === 'dev' && (
            <div className="dev-mode-pane">
              <p className="text-sm text-muted mb-4">
                Instantly generate a cryptographically valid HS256 JWT authenticated against the
                FastAPI backend and PostgreSQL Row-Level Security:
              </p>
              <div className="flex-col gap-3">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDevLogin('user')}
                  className="btn btn-outline btn-block flex-between"
                >
                  <div className="text-left">
                    <div className="font-semibold text-forest">Dr. Gomti Hydrologist</div>
                    <div className="mono text-xs text-muted">Role: user · 50 runs/mo quota</div>
                  </div>
                  <UserCheck size={18} className="text-forest" />
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDevLogin('admin')}
                  className="btn btn-outline btn-block flex-between border-amber"
                >
                  <div className="text-left">
                    <div className="font-semibold text-amber">GIS Operations Lead</div>
                    <div className="mono text-xs text-muted">Role: admin · 500 runs/mo quota</div>
                  </div>
                  <Shield size={18} className="text-amber" />
                </button>
              </div>
            </div>
          )}

          {/* Direct Bearer Token Mode */}
          {mode === 'token' && (
            <form onSubmit={handleCustomTokenSubmit} className="token-mode-pane">
              <p className="text-sm text-muted mb-3">
                Paste an existing Supabase JWT Bearer token to authenticate:
              </p>
              <div className="form-group mb-4">
                <label className="form-label mono text-xs">Authorization: Bearer &lt;JWT&gt;</label>
                <textarea
                  className="form-textarea mono text-xs"
                  rows={4}
                  placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                  value={customToken}
                  onChange={(e) => setCustomToken(e.target.value)}
                  required
                />
              </div>
              <button
                type="submit"
                disabled={submitting || !customToken.trim()}
                className="btn btn-primary btn-block"
              >
                {submitting ? 'Verifying Token...' : 'Authenticate with JWT'}
              </button>
            </form>
          )}

          {/* Supabase Email/Password Mode */}
          {mode === 'supabase' && (
            <form onSubmit={handleSupabaseAuth} className="supabase-mode-pane">
              {!isSupabaseLive && (
                <div className="alert alert-info mb-3">
                  <span className="text-xs">
                    <code>VITE_SUPABASE_URL</code> is not configured in <code>frontend/.env</code>.
                    To use live Supabase Auth, add your project credentials or use the Developer mode.
                  </span>
                </div>
              )}

              {isSignUp && (
                <div className="form-group mb-3">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Dr. Gomti Hydrologist"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required={isSignUp}
                  />
                </div>
              )}

              <div className="form-group mb-3">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="hydrologist@dharascope.org"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="form-group mb-4">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>

              <button
                type="submit"
                disabled={submitting || !isSupabaseLive}
                className="btn btn-primary btn-block mb-3"
              >
                {submitting
                  ? 'Processing...'
                  : isSignUp
                  ? 'Create Hydrologist Account'
                  : 'Sign In via Supabase'}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  className="btn btn-link text-xs"
                  onClick={() => setIsSignUp(!isSignUp)}
                >
                  {isSignUp
                    ? 'Already registered? Sign in instead'
                    : 'Need an account? Register with email'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
