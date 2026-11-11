/**
 * Scientific GIS Workstation Header.
 * Displays DharaScope identity, Sentinel-2 MSI telemetry specs, backend connectivity,
 * and user profile/session status.
 */

import React, { useEffect, useState } from 'react';
import { Database, Satellite, User, LogOut, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { HealthResponse } from '../types/api';

interface HeaderProps {
  onOpenAuthModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenAuthModal }) => {
  const { user, isAuthenticated, isAdmin, signOut } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function checkHealth() {
      try {
        const res = await api.getHealth();
        if (mounted) setHealth(res);
      } catch {
        if (mounted) setHealth(null);
      } finally {
        if (mounted) setHealthLoading(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="header-container">
      {/* Brand Identity & Mission */}
      <div className="header-brand">
        <div className="brand-logo">
          <Satellite className="icon-satellite" size={24} />
        </div>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-title">DharaScope</h1>
            <span className="badge badge-version">v2.3</span>
          </div>
          <p className="brand-subtitle">
            Satellite-Based River Surface Water Dynamics Platform | Sentinel-2 MSI
          </p>
        </div>
      </div>

      {/* Telemetry & System Status Indicators */}
      <div className="header-telemetry">
        {/* Sensor & Spatial Resolution */}
        <div className="telemetry-pill">
          <Satellite size={14} className="text-forest" />
          <span className="mono text-xs">S2-MSI · 10m GSD · B03/B08</span>
        </div>

        {/* Database & Backend Health */}
        <div className="telemetry-pill">
          <Database size={14} className={health?.database === 'connected' ? 'text-forest' : 'text-amber'} />
          <span className="mono text-xs">
            {healthLoading
              ? 'Checking API...'
              : health?.status === 'healthy'
              ? `API Online (${health.database})`
              : 'API Offline'}
          </span>
          <span
            className={`status-dot ${health?.status === 'healthy' ? 'dot-online' : 'dot-offline'}`}
          />
        </div>

        {/* User / Session Indicator */}
        {isAuthenticated && user ? (
          <div className="user-profile-badge">
            <div className="user-info">
              <div className="user-name-row">
                <User size={13} />
                <span className="user-name">{user.full_name || user.email.split('@')[0]}</span>
                <span className={`badge ${isAdmin ? 'badge-admin' : 'badge-user'}`}>
                  {isAdmin ? 'ADMIN' : 'USER'}
                </span>
              </div>
              <div className="user-quota mono text-xs">
                Quota: {user.quota_monthly_runs} runs/mo
              </div>
            </div>
            <button
              onClick={() => signOut()}
              className="btn btn-icon btn-secondary"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuthModal}
            className="btn btn-primary btn-sm flex-center gap-1"
          >
            <LogIn size={15} />
            <span>Connect / Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
