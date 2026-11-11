/**
 * Authentication Context Provider.
 * Manages Supabase sessions, JWT token state, profile synchronization,
 * and authoritative database role checks.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { UserProfileResponse } from '../types/api';
import { api, setAuthToken, getAuthToken } from '../services/api';
import { supabase, isSupabaseConfigured, createDevSignedJwt } from '../services/supabase';

interface AuthContextType {
  user: UserProfileResponse | null;
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  error: string | null;
  isSupabaseLive: boolean;
  signInWithSupabase: (email: string, password: string) => Promise<void>;
  signUpWithSupabase: (email: string, password: string, fullName: string) => Promise<void>;
  signInWithToken: (jwtToken: string) => Promise<void>;
  signInDevAccount: (role?: 'user' | 'admin') => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfileResponse | null>(null);
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  const fetchProfile = useCallback(async (authToken: string) => {
    try {
      setAuthToken(authToken);
      const profile = await api.getCurrentUser();
      setUser(profile);
      setToken(authToken);
      setError(null);
    } catch (err: any) {
      console.warn('Failed to fetch user profile with token:', err);
      // If token is invalid or expired, clear it
      if (err.status_code === 401) {
        setAuthToken(null);
        setToken(null);
        setUser(null);
      }
      setError(err.detail || err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize auth session on mount
  useEffect(() => {
    let mounted = true;

    async function initSession() {
      setIsLoading(true);

      // Check if Supabase client is live and has an active session
      if (isSupabaseConfigured && supabase) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token && mounted) {
            await fetchProfile(session.access_token);
            return;
          }
        } catch (e) {
          console.warn('Error reading Supabase session:', e);
        }
      }

      // Fallback: Check local stored token
      const savedToken = getAuthToken();
      if (savedToken && mounted) {
        await fetchProfile(savedToken);
      } else if (mounted) {
        setIsLoading(false);
      }
    }

    initSession();

    // Listen to Supabase auth state changes if configured
    if (isSupabaseConfigured && supabase) {
      const { data: authListener } = supabase.auth.onAuthStateChange(async (_event, session) => {
        if (!mounted) return;
        if (session?.access_token) {
          await fetchProfile(session.access_token);
        } else {
          setAuthToken(null);
          setToken(null);
          setUser(null);
        }
      });

      return () => {
        mounted = false;
        authListener.subscription.unsubscribe();
      };
    }

    return () => {
      mounted = false;
    };
  }, [fetchProfile]);

  const signInWithSupabase = async (email: string, password: string) => {
    if (!supabase) {
      throw new Error('Supabase is not configured. Use developer test mode or configure VITE_SUPABASE_URL in .env');
    }
    setIsLoading(true);
    setError(null);
    try {
      const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) throw signInError;
      if (data.session?.access_token) {
        await fetchProfile(data.session.access_token);
      }
    } catch (err: any) {
      setError(err.message || 'Sign in failed');
      setIsLoading(false);
      throw err;
    }
  };

  const signUpWithSupabase = async (email: string, password: string, fullName: string) => {
    if (!supabase) {
      throw new Error('Supabase is not configured. Use developer test mode or configure VITE_SUPABASE_URL in .env');
    }
    setIsLoading(true);
    setError(null);
    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });
      if (signUpError) throw signUpError;
      if (data.session?.access_token) {
        await fetchProfile(data.session.access_token);
      }
    } catch (err: any) {
      setError(err.message || 'Sign up failed');
      setIsLoading(false);
      throw err;
    }
  };

  const signInWithToken = async (jwtToken: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await fetchProfile(jwtToken);
    } finally {
      setIsLoading(false);
    }
  };

  const signInDevAccount = async (role: 'user' | 'admin' = 'user') => {
    setIsLoading(true);
    setError(null);
    try {
      const userId = role === 'admin'
        ? '77777777-7777-4777-8777-777777777777'
        : '66666666-6666-4666-8666-666666666666';
      const email = role === 'admin'
        ? 'gis.lead@dharascope.org'
        : 'gomti.hydrologist@dharascope.org';
      const name = role === 'admin'
        ? 'GIS Operations Lead'
        : 'Dr. Gomti Hydrologist';

      const devToken = await createDevSignedJwt(userId, email, role, name);
      await fetchProfile(devToken);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize dev account');
      setIsLoading(false);
    }
  };

  const signOut = async () => {
    setIsLoading(true);
    try {
      if (supabase) {
        await supabase.auth.signOut();
      }
    } catch (e) {
      console.warn('SignOut error from supabase:', e);
    } finally {
      setAuthToken(null);
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  const refreshProfile = async () => {
    const curToken = token || getAuthToken();
    if (curToken) {
      await fetchProfile(curToken);
    }
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isAdmin: user?.role === 'admin',
    isLoading,
    error,
    isSupabaseLive: isSupabaseConfigured,
    signInWithSupabase,
    signUpWithSupabase,
    signInWithToken,
    signInDevAccount,
    signOut,
    refreshProfile,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
