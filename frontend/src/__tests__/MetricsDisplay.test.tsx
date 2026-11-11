/**
 * Component tests for MetricsDisplay.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { MetricsDisplay } from '../components/MetricsDisplay';
import type { WaterMetricsResponse } from '../types/api';

const mockMetrics: WaterMetricsResponse = {
  id: '8bb85f64-5717-4562-b3fc-2c963f66afb2',
  analysis_run_id: 'e4585f64-5717-4562-b3fc-2c963f66afa7',
  common_valid_pixels: 1323037,
  common_valid_area_ha: 13230.37,
  pixel_size_m2: 100.0,
  t1_water_pixels: 18456,
  t1_water_area_m2: 1845600.0,
  t1_water_area_ha: 184.56,
  t2_water_pixels: 13933,
  t2_water_area_m2: 1393300.0,
  t2_water_area_ha: 139.33,
  absolute_change_m2: -452300.0,
  absolute_change_ha: -45.23,
  percentage_change: -24.51,
  persistent_water_m2: 1251800.0,
  persistent_water_ha: 125.18,
  apparent_loss_m2: 593800.0,
  apparent_loss_ha: 59.38,
  apparent_gain_m2: 141500.0,
  apparent_gain_ha: 14.15,
  limitation_statement:
    'Surface area changes indicate inundation variations and do not measure water volume or depth.',
  created_at: '2026-11-10T16:54:35Z',
};

describe('MetricsDisplay Component', () => {
  it('renders baseline T1 and later T2 surface water areas correctly', () => {
    render(<MetricsDisplay metrics={mockMetrics} />);

    expect(screen.getByText('184.56')).toBeInTheDocument();
    expect(screen.getByText('139.33')).toBeInTheDocument();
    expect(screen.getByText('-45.23')).toBeInTheDocument();
    expect(screen.getByText('-24.51% net change')).toBeInTheDocument();
  });

  it('renders 4-class categorical transitions breakdown', () => {
    render(<MetricsDisplay metrics={mockMetrics} />);

    expect(screen.getByText('Persistent Water (Perennial)')).toBeInTheDocument();
    expect(screen.getByText('125.18 ha')).toBeInTheDocument();

    expect(screen.getByText('Apparent Water Loss (Recession)')).toBeInTheDocument();
    expect(screen.getByText('59.38 ha')).toBeInTheDocument();

    expect(screen.getByText('Apparent Water Gain (Inundation)')).toBeInTheDocument();
    expect(screen.getByText('14.15 ha')).toBeInTheDocument();
  });

  it('renders mandatory hydrological limitation statement', () => {
    render(<MetricsDisplay metrics={mockMetrics} />);

    expect(
      screen.getByText(/Surface area changes indicate inundation variations and do not measure water volume/i)
    ).toBeInTheDocument();
  });

  it('visibly labels synthetic benchmark data and prevents silent spoofing', () => {
    const { rerender } = render(<MetricsDisplay metrics={mockMetrics} isRealData={false} />);
    expect(screen.getByText('SYNTHETIC BENCHMARK DATASET')).toBeInTheDocument();
    expect(
      screen.getByText(/computed from an offline synthetic calibration sample/i)
    ).toBeInTheDocument();

    rerender(<MetricsDisplay metrics={mockMetrics} isRealData={true} />);
    expect(screen.queryByText('SYNTHETIC BENCHMARK DATASET')).not.toBeInTheDocument();
  });
});
