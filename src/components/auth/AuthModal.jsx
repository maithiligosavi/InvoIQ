import React, { useState } from 'react';
import { User, Lock, Eye, EyeOff, FileText, AlertCircle, Loader2, CheckCircle2, X } from 'lucide-react';
import { loginUser, registerUser } from '../../services/api';

/**
 * Modern AuthModal styled with InvoIQ's custom warm palette:
 * - Background: #FFF5F5
 * - Cards/Containers: #F7D6D0
 * - Buttons & Interactive Accents: #E2B4BD
 * - Text & Headings: #4A4A4A
 */
export default function AuthModal({
  isOpen = true,
  onClose,
  onSuccess,
  initialMode = 'login',
}) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setUsername('');
    setPassword('');
    setConfirmPassword('');
    setError(null);
    setSuccessMsg(null);
  };

  const handleSwitchMode = (nextMode) => {
    setMode(nextMode);
    setError(null);
    setSuccessMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const cleanUser = username.trim();
    if (!cleanUser) {
      setError('Please enter a username.');
      return;
    }

    if (!password) {
      setError('Please enter a password.');
      return;
    }

    if (mode === 'register') {
      if (cleanUser.length < 3) {
        setError('Username must be at least 3 characters long.');
        return;
      }
      if (password.length < 4) {
        setError('Password must be at least 4 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match. Please verify.');
        return;
      }
    }

    setLoading(true);

    try {
      let res;
      if (mode === 'login') {
        res = await loginUser(cleanUser, password);
        setSuccessMsg('Logged in successfully!');
      } else {
        res = await registerUser(cleanUser, password);
        setSuccessMsg('Account created! Welcome to InvoIQ.');
      }

      const token = res.access_token;
      const loggedUser = res.username || cleanUser;

      setTimeout(() => {
        if (onSuccess) {
          onSuccess({ username: loggedUser, token });
        }
        if (onClose) {
          onClose();
        }
      }, 400);
    } catch (err) {
      console.error('Authentication error:', err);
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        (mode === 'login' ? 'Failed to sign in. Please check your credentials.' : 'Registration failed.');
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-sm animate-fade-in">
      {/* Outer Card Container styled with #F7D6D0 */}
      <div
        className="relative w-full max-w-md rounded-3xl p-1.5 sm:p-2 shadow-2xl transition-all"
        style={{
          backgroundColor: '#F7D6D0',
          boxShadow: '0 20px 40px -15px rgba(74, 74, 74, 0.25)',
        }}
      >
        {/* Inner Card styled with #FFF5F5 */}
        <div
          className="relative rounded-[22px] px-6 py-8 sm:px-8 sm:py-9"
          style={{ backgroundColor: '#FFF5F5' }}
        >
          {/* Close button if optional dismissal is provided */}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="absolute top-4 right-4 p-1.5 rounded-full text-[#4A4A4A]/60 hover:text-[#4A4A4A] hover:bg-[#F7D6D0]/60 transition-colors"
              aria-label="Close dialog"
            >
              <X size={18} />
            </button>
          )}

          {/* Brand Header */}
          <div className="text-center mb-6">
            <div
              className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-3 shadow-md transition-transform hover:scale-105"
              style={{
                backgroundColor: '#E2B4BD',
                color: '#4A4A4A',
              }}
            >
              <FileText size={28} strokeWidth={2.4} />
            </div>
            <h2
              className="text-2xl font-extrabold tracking-tight"
              style={{ color: '#4A4A4A' }}
            >
              InvoIQ
            </h2>
            <p
              className="text-xs uppercase tracking-widest font-semibold mt-0.5 opacity-70"
              style={{ color: '#4A4A4A' }}
            >
              Invoice Intelligence
            </p>
          </div>

          {/* Mode Switcher Tabs */}
          <div
            className="flex p-1 rounded-xl mb-6 border border-[#E2B4BD]/40"
            style={{ backgroundColor: '#F7D6D0' }}
          >
            <button
              type="button"
              onClick={() => handleSwitchMode('login')}
              className={`flex-1 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                mode === 'login'
                  ? 'shadow-sm'
                  : 'opacity-70 hover:opacity-100'
              }`}
              style={{
                backgroundColor: mode === 'login' ? '#FFF5F5' : 'transparent',
                color: '#4A4A4A',
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleSwitchMode('register')}
              className={`flex-1 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                mode === 'register'
                  ? 'shadow-sm'
                  : 'opacity-70 hover:opacity-100'
              }`}
              style={{
                backgroundColor: mode === 'register' ? '#FFF5F5' : 'transparent',
                color: '#4A4A4A',
              }}
            >
              Create Account
            </button>
          </div>

          {/* Form Description */}
          <div className="mb-5 text-center">
            <h3
              className="text-base font-bold"
              style={{ color: '#4A4A4A' }}
            >
              {mode === 'login' ? 'Welcome Back' : 'Create Your Account'}
            </h3>
            <p
              className="text-xs mt-1 opacity-75"
              style={{ color: '#4A4A4A' }}
            >
              {mode === 'login'
                ? 'Sign in to manage and process your invoices securely.'
                : 'Register to start extracting invoice intelligence.'}
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div
              className="flex items-start gap-2.5 p-3 rounded-xl mb-4 text-xs font-medium border border-[#E2B4BD]"
              style={{
                backgroundColor: '#F7D6D0',
                color: '#4A4A4A',
              }}
            >
              <AlertCircle size={16} className="shrink-0 mt-0.5 text-rose-700" />
              <div className="flex-1">{error}</div>
            </div>
          )}

          {/* Success Banner */}
          {successMsg && (
            <div
              className="flex items-center gap-2 p-3 rounded-xl mb-4 text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200"
            >
              <CheckCircle2 size={16} className="shrink-0 text-emerald-600" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Auth Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username Input */}
            <div>
              <label
                className="block text-xs font-bold mb-1.5 uppercase tracking-wider"
                style={{ color: '#4A4A4A' }}
              >
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none opacity-60">
                  <User size={17} style={{ color: '#4A4A4A' }} />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. alex_finance"
                  autoComplete="username"
                  required
                  disabled={loading}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border outline-none transition-all placeholder:text-[#4A4A4A]/40 focus:ring-2"
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2B4BD',
                    color: '#4A4A4A',
                  }}
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label
                className="block text-xs font-bold mb-1.5 uppercase tracking-wider"
                style={{ color: '#4A4A4A' }}
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none opacity-60">
                  <Lock size={17} style={{ color: '#4A4A4A' }} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  required
                  disabled={loading}
                  className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border outline-none transition-all placeholder:text-[#4A4A4A]/40 focus:ring-2"
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2B4BD',
                    color: '#4A4A4A',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center opacity-60 hover:opacity-100 transition-opacity"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff size={16} style={{ color: '#4A4A4A' }} />
                  ) : (
                    <Eye size={16} style={{ color: '#4A4A4A' }} />
                  )}
                </button>
              </div>
            </div>

            {/* Confirm Password (Register mode only) */}
            {mode === 'register' && (
              <div className="animate-fade-in">
                <label
                  className="block text-xs font-bold mb-1.5 uppercase tracking-wider"
                  style={{ color: '#4A4A4A' }}
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none opacity-60">
                    <Lock size={17} style={{ color: '#4A4A4A' }} />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="new-password"
                    required
                    disabled={loading}
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border outline-none transition-all placeholder:text-[#4A4A4A]/40 focus:ring-2"
                    style={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2B4BD',
                      color: '#4A4A4A',
                    }}
                  />
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-xl font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2 hover:brightness-95 active:scale-[0.99] disabled:opacity-60 cursor-pointer"
                style={{
                  backgroundColor: '#E2B4BD',
                  color: '#4A4A4A',
                  border: '1px solid rgba(74, 74, 74, 0.1)',
                }}
              >
                {loading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>{mode === 'login' ? 'Authenticating...' : 'Creating Account...'}</span>
                  </>
                ) : (
                  <span>{mode === 'login' ? 'Sign In to InvoIQ' : 'Create InvoIQ Account'}</span>
                )}
              </button>
            </div>
          </form>

          {/* Toggle mode prompt */}
          <div className="mt-6 text-center text-xs" style={{ color: '#4A4A4A' }}>
            {mode === 'login' ? (
              <p>
                Don&apos;t have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleSwitchMode('register')}
                  className="font-bold underline decoration-[#E2B4BD] underline-offset-2 hover:opacity-80 transition-opacity"
                  style={{ color: '#4A4A4A' }}
                >
                  Create one now
                </button>
              </p>
            ) : (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleSwitchMode('login')}
                  className="font-bold underline decoration-[#E2B4BD] underline-offset-2 hover:opacity-80 transition-opacity"
                  style={{ color: '#4A4A4A' }}
                >
                  Sign in instead
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

