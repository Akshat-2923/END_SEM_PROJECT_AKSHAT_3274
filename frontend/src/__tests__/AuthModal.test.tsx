/**
 * Component tests for AuthModal and session switching.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthModal } from '../components/AuthModal';
import { AuthProvider } from '../context/AuthContext';

describe('AuthModal Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders developer / hydrologist preset options', () => {
    render(
      <AuthProvider>
        <AuthModal isOpen={true} onClose={() => {}} />
      </AuthProvider>
    );

    expect(screen.getByText('DharaScope Authentication')).toBeInTheDocument();
    expect(screen.getByText('Dr. Gomti Hydrologist')).toBeInTheDocument();
    expect(screen.getByText('GIS Operations Lead')).toBeInTheDocument();
  });

  it('switches tabs between Developer, Bearer JWT, and Supabase Cloud', () => {
    render(
      <AuthProvider>
        <AuthModal isOpen={true} onClose={() => {}} />
      </AuthProvider>
    );

    const tokenTab = screen.getByText('Bearer JWT');
    fireEvent.click(tokenTab);
    expect(screen.getByText(/Paste an existing Supabase JWT Bearer token/i)).toBeInTheDocument();

    const devTab = screen.getByText('Developer / Hydrologist');
    fireEvent.click(devTab);
    expect(screen.getByText('Dr. Gomti Hydrologist')).toBeInTheDocument();
  });
});
