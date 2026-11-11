/**
 * Unit tests for API service layer and Bearer token management.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { api, setAuthToken, getAuthToken, APIError, downloadFile } from '../services/api';

describe('API Service Layer', () => {
  beforeEach(() => {
    localStorage.clear();
    setAuthToken(null);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('manages token storage and retrieval', () => {
    expect(getAuthToken()).toBeNull();
    setAuthToken('test_jwt_token_123');
    expect(getAuthToken()).toBe('test_jwt_token_123');
    expect(localStorage.getItem('dharascope_token')).toBe('test_jwt_token_123');
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });

  it('attaches Authorization Bearer header when token is present', async () => {
    setAuthToken('bearer_xyz_789');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: '11111111-1111-1111-1111-111111111111',
        email: 'test@dharascope.org',
        role: 'user',
        quota_monthly_runs: 50,
      }),
    });
    global.fetch = mockFetch;

    const profile = await api.getCurrentUser();
    expect(profile.email).toBe('test@dharascope.org');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledHeaders = mockFetch.mock.calls[0][1].headers;
    expect(calledHeaders.get('Authorization')).toBe('Bearer bearer_xyz_789');
  });

  it('throws structured APIError on 400 Bad Request', async () => {
    setAuthToken('test_token');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({
        error: 'AOIValidationError',
        detail: 'AOI surface area (0.0500 km²) is below the minimum threshold of 0.10 km².',
        status_code: 400,
      }),
    });
    global.fetch = mockFetch;

    await expect(
      api.validateAOI({
        geometry: {
          type: 'Polygon',
          coordinates: [[[0, 0], [0, 0.001], [0.001, 0.001], [0, 0]]],
        },
      })
    ).rejects.toThrow('AOI surface area (0.0500 km²) is below the minimum threshold of 0.10 km².');
  });

  it('throws APIError on 401 Unauthorized', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({
        error: 'HTTPException',
        detail: 'Missing or expired authentication token',
        status_code: 401,
      }),
    });
    global.fetch = mockFetch;

    try {
      await api.getCurrentUser();
      expect.fail('Should have thrown APIError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(APIError);
      expect(err.status_code).toBe(401);
      expect(err.detail).toContain('Missing or expired');
    }
  });

  it('downloads file and creates object URL', async () => {
    setAuthToken('test_token');

    const blobContent = 'col1,col2\nval1,val2';
    const mockBlob = new Blob([blobContent], { type: 'text/csv' });

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        'content-disposition': 'attachment; filename="test_report.csv"',
      }),
      blob: async () => mockBlob,
    });
    global.fetch = mockFetch;

    // Mock URL.createObjectURL and URL.revokeObjectURL
    const createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/mock-uuid');
    const revokeObjectURL = vi.fn();
    window.URL.createObjectURL = createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURL;

    await downloadFile('/analyses/test-id/reports/csv', 'fallback.csv');

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-uuid');
  });
});
