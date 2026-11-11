/**
 * Supabase Client & Authentication Helper.
 * Supports live Supabase Auth credentials as well as local cryptographic
 * token generation for offline development and headless testing.
 *
 * Security Invariant: Development token signing and the development secret
 * are strictly tree-shaken and excluded from production client bundles.
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(
  SUPABASE_URL && SUPABASE_ANON_KEY && !SUPABASE_URL.includes('your-project-ref')
);

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  : null;

// Standard fallback secret matching src/auth.py default - strictly dev-only
const DEV_JWT_SECRET = import.meta.env.DEV
  ? 'dharascope_test_jwt_secret_key_minimum_32_bytes_long'
  : '';

function base64UrlEncode(str: string): string {
  const base64 = btoa(str);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function bufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return base64UrlEncode(binary);
}

/**
 * Creates a cryptographically signed HS256 JWT in the browser
 * using Web Crypto API matching the backend's development secret.
 * STRICTLY disabled in production builds.
 */
export async function createDevSignedJwt(
  userId: string,
  email: string,
  role: 'user' | 'admin' = 'user',
  fullName = 'Dr. Gomti Hydrologist'
): Promise<string> {
  if (import.meta.env.PROD || !import.meta.env.DEV) {
    throw new Error('Development token signing is disabled in production environments.');
  }

  const now = Math.floor(Date.now() / 1000);
  const header = {
    alg: 'HS256',
    typ: 'JWT',
  };

  const payload = {
    sub: userId,
    email,
    aud: 'authenticated',
    role: 'authenticated',
    app_metadata: {
      role,
      provider: 'email',
    },
    user_metadata: {
      full_name: fullName,
    },
    iat: now,
    exp: now + 86400 * 7, // 7 days validity
  };

  const headerB64 = base64UrlEncode(JSON.stringify(header));
  const payloadB64 = base64UrlEncode(JSON.stringify(payload));
  const dataToSign = `${headerB64}.${payloadB64}`;

  const encoder = new TextEncoder();
  const keyData = encoder.encode(DEV_JWT_SECRET);

  const cryptoKey = await window.crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signatureBuffer = await window.crypto.subtle.sign(
    'HMAC',
    cryptoKey,
    encoder.encode(dataToSign)
  );

  const signatureB64 = bufferToBase64Url(signatureBuffer);
  return `${dataToSign}.${signatureB64}`;
}
