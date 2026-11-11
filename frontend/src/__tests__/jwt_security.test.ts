/**
 * Security audit tests for frontend JWT development signer.
 * Proves that development signing is strictly prohibited in production mode.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { createDevSignedJwt } from '../services/supabase';

describe('Frontend JWT Security & Environment Isolation', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('allows token creation in development environment', async () => {
    vi.stubEnv('PROD', false);
    vi.stubEnv('DEV', true);

    const token = await createDevSignedJwt(
      '66666666-6666-4666-8666-666666666666',
      'dev.test@dharascope.org',
      'user'
    );

    expect(typeof token).toBe('string');
    const parts = token.split('.');
    expect(parts.length).toBe(3);

    // Verify header
    const header = JSON.parse(atob(parts[0]));
    expect(header.alg).toBe('HS256');
    expect(header.typ).toBe('JWT');

    // Verify payload claims
    const payload = JSON.parse(atob(parts[1]));
    expect(payload.sub).toBe('66666666-6666-4666-8666-666666666666');
    expect(payload.aud).toBe('authenticated');
    expect(payload.app_metadata.role).toBe('user');
  });

  it('strictly rejects token signing in production environment', async () => {
    vi.stubEnv('PROD', true);
    vi.stubEnv('DEV', false);

    await expect(
      createDevSignedJwt(
        '66666666-6666-4666-8666-666666666666',
        'dev.test@dharascope.org',
        'user'
      )
    ).rejects.toThrow(/disabled in production environments/i);
  });
});
