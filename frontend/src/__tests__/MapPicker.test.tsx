/**
 * Component tests for MapPicker AOI validation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MapPicker, LUCKNOW_GOMTI_PRESET } from '../components/MapPicker';
import { AuthProvider } from '../context/AuthContext';
import { api } from '../services/api';

describe('MapPicker Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders card title and preset buttons', () => {
    render(
      <AuthProvider>
        <MapPicker geometry={LUCKNOW_GOMTI_PRESET} onChangeGeometry={() => {}} />
      </AuthProvider>
    );

    expect(screen.getByText('Geographical Area of Interest (AOI)')).toBeInTheDocument();
    expect(screen.getByText('Gomti Reach (Lucknow)')).toBeInTheDocument();
    expect(screen.getByText('GeoJSON Editor')).toBeInTheDocument();
  });

  it('displays validated area and coordinates when backend returns valid response', async () => {
    vi.spyOn(api, 'validateAOI').mockResolvedValue({
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

    // Set token so isAuthenticated is true
    localStorage.setItem('dharascope_token', 'valid_test_token');
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
      expect(screen.getByText('Valid AOI Geometry (PostGIS Verified)')).toBeInTheDocument();
      expect(screen.getByText('4.4021')).toBeInTheDocument();
      expect(screen.getByText('440.21')).toBeInTheDocument();
      expect(screen.getByText('5 / 500')).toBeInTheDocument();
    });
  });
});
