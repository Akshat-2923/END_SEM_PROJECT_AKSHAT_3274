/**
 * Component tests for MapPicker AOI validation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import L from 'leaflet';
import React from 'react';
import { MapPicker, LUCKNOW_GOMTI_PRESET } from '../components/MapPicker';
import { AuthProvider } from '../context/AuthContext';
import { api, APIError, setAuthToken } from '../services/api';

describe('MapPicker Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    setAuthToken(null);
  });

  it('renders Esri dark canvas map and labels with sign-in prompt when unauthenticated', () => {
    const tileSpy = vi.spyOn(L, 'tileLayer');
    const validateSpy = vi.spyOn(api, 'validateAOI');

    render(
      <AuthProvider>
        <MapPicker geometry={LUCKNOW_GOMTI_PRESET} onChangeGeometry={() => {}} />
      </AuthProvider>
    );

    expect(screen.getByText('Geographical Area of Interest (AOI)')).toBeInTheDocument();
    expect(screen.getByText('Gomti Reach (Lucknow)')).toBeInTheDocument();
    expect(screen.getByText('GeoJSON Editor')).toBeInTheDocument();

    // Preserves authentication requirement with calm info banner instead of error banner
    expect(screen.getByText('Sign in to validate AOI geometry')).toBeInTheDocument();
    expect(screen.queryByText('AOI Validation Failed')).not.toBeInTheDocument();
    expect(validateSpy).not.toHaveBeenCalled();

    // Uses verified Esri Dark Gray Canvas base + reference labels, never retired CARTO URL
    const tileUrls = tileSpy.mock.calls.map(([url]) => url);
    expect(tileUrls).toContain(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
    );
    expect(tileUrls).toContain(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}'
    );
    expect(tileUrls.some((url) => url.includes('cartocdn.com'))).toBe(false);
  });

  it('displays validated area and coordinates when authenticated backend returns valid response', async () => {
    const validateSpy = vi.spyOn(api, 'validateAOI').mockResolvedValue({
      valid: true,
      geometry: LUCKNOW_GOMTI_PRESET,
      geometry_type: 'Polygon',
      bbox: [80.9, 26.84, 80.92, 26.86],
      centroid: [80.91, 26.85],
      area_m2: 4402123.45,
      area_km2: 4.4021,
      area_hectares: 440.21,
      vertex_count: 5,
    });

    // Set token so isAuthenticated becomes true after AuthProvider loads profile
    setAuthToken('valid_test_token');
    vi.spyOn(api, 'getCurrentUser').mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      email: 'hydrologist@dharascope.org',
      full_name: 'Dr. Gomti Hydrologist',
      role: 'user',
      quota_monthly_runs: 50,
      created_at: '2026-11-10T00:00:00Z',
      updated_at: '2026-11-10T00:00:00Z',
    });

    render(
      <AuthProvider>
        <MapPicker geometry={LUCKNOW_GOMTI_PRESET} onChangeGeometry={() => {}} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(validateSpy).toHaveBeenCalledWith({ geometry: LUCKNOW_GOMTI_PRESET });
      expect(screen.getByText('Valid AOI Geometry (PostGIS Verified)')).toBeInTheDocument();
      expect(screen.getByText('4.4021')).toBeInTheDocument();
      expect(screen.getByText('440.21')).toBeInTheDocument();
      expect(screen.getByText('5 / 500')).toBeInTheDocument();
    });
  });

  it('displays validation failure alert when authenticated geometry validation fails', async () => {
    vi.spyOn(api, 'validateAOI').mockRejectedValue(
      new APIError(400, 'AOIValidationError', 'Area exceeds 100.00 km² limit.')
    );

    setAuthToken('valid_test_token');
    vi.spyOn(api, 'getCurrentUser').mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      email: 'hydrologist@dharascope.org',
      full_name: 'Dr. Gomti Hydrologist',
      role: 'user',
      quota_monthly_runs: 50,
      created_at: '2026-11-10T00:00:00Z',
      updated_at: '2026-11-10T00:00:00Z',
    });

    render(
      <AuthProvider>
        <MapPicker geometry={LUCKNOW_GOMTI_PRESET} onChangeGeometry={() => {}} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('AOI Validation Failed')).toBeInTheDocument();
      expect(screen.getByText('Area exceeds 100.00 km² limit.')).toBeInTheDocument();
    });
  });
});
