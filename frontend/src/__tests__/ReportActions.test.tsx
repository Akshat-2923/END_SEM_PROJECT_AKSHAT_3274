/**
 * Component tests for ReportActions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ReportActions } from '../components/ReportActions';
import { api } from '../services/api';

describe('ReportActions Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders PDF and CSV download options', () => {
    render(<ReportActions analysisId="e4585f64-5717-4562-b3fc-2c963f66afa7" />);

    expect(screen.getByText('Publication PDF Report')).toBeInTheDocument();
    expect(screen.getByText('CSV Data Manifest')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /PDF/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /CSV/i })).toBeInTheDocument();
  });

  it('triggers PDF download and displays success notification', async () => {
    const downloadSpy = vi.spyOn(api, 'downloadReport').mockResolvedValue(undefined);

    render(<ReportActions analysisId="e4585f64-5717-4562-b3fc-2c963f66afa7" />);

    const pdfBtn = screen.getByRole('button', { name: /PDF/i });
    fireEvent.click(pdfBtn);

    expect(downloadSpy).toHaveBeenCalledWith('e4585f64-5717-4562-b3fc-2c963f66afa7', 'pdf');

    await waitFor(() => {
      expect(screen.getByText(/Successfully downloaded PDF report/i)).toBeInTheDocument();
    });
  });

  it('triggers CSV download and displays success notification', async () => {
    const downloadSpy = vi.spyOn(api, 'downloadReport').mockResolvedValue(undefined);

    render(<ReportActions analysisId="e4585f64-5717-4562-b3fc-2c963f66afa7" />);

    const csvBtn = screen.getByRole('button', { name: /CSV/i });
    fireEvent.click(csvBtn);

    expect(downloadSpy).toHaveBeenCalledWith('e4585f64-5717-4562-b3fc-2c963f66afa7', 'csv');

    await waitFor(() => {
      expect(screen.getByText(/Successfully downloaded CSV report/i)).toBeInTheDocument();
    });
  });
});
