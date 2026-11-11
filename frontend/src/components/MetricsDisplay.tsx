/**
 * Quantitative Surface Water Area Metrics & Transition Dynamics Display.
 * Renders verified scientific KPIs and mandatory limitation statement.
 */

import React from 'react';
import {
  TrendingDown,
  TrendingUp,
  Droplets,
  Layers,
  Info,
} from 'lucide-react';
import type { WaterMetricsResponse } from '../types/api';

interface MetricsDisplayProps {
  metrics: WaterMetricsResponse;
}

export const MetricsDisplay: React.FC<MetricsDisplayProps> = ({ metrics }) => {
  const isLoss = metrics.absolute_change_ha < 0;

  return (
    <div className="metrics-display-card card p-4 mb-4">
      <div className="card-header mb-3 flex-between">
        <div className="flex-center gap-2">
          <Droplets size={18} className="text-forest" />
          <h3 className="card-title">Surface Water Area & Transition Dynamics</h3>
        </div>
        <span className="mono text-2xs text-muted">10m GSD (100 m²/px)</span>
      </div>

      {/* Primary KPI Ribbon */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {/* Baseline T1 Area */}
        <div className="stat-card p-3 bg-slate rounded border border-subtle">
          <div className="stat-label text-2xs mono text-muted mb-1">
            Baseline Water Area (T1)
          </div>
          <div className="stat-value mono text-lg font-bold text-text-h">
            {metrics.t1_water_area_ha.toFixed(2)} <span className="text-xs font-normal text-muted">ha</span>
          </div>
          <div className="stat-sub mono text-2xs text-muted mt-0.5">
            {metrics.t1_water_area_m2.toLocaleString()} m² · {metrics.t1_water_pixels.toLocaleString()} px
          </div>
        </div>

        {/* Comparison T2 Area */}
        <div className="stat-card p-3 bg-slate rounded border border-subtle">
          <div className="stat-label text-2xs mono text-muted mb-1">
            Later Water Area (T2)
          </div>
          <div className="stat-value mono text-lg font-bold text-text-h">
            {metrics.t2_water_area_ha.toFixed(2)} <span className="text-xs font-normal text-muted">ha</span>
          </div>
          <div className="stat-sub mono text-2xs text-muted mt-0.5">
            {metrics.t2_water_area_m2.toLocaleString()} m² · {metrics.t2_water_pixels.toLocaleString()} px
          </div>
        </div>

        {/* Net Water Dynamics Delta */}
        <div className={`stat-card p-3 bg-slate rounded border ${isLoss ? 'border-amber-light' : 'border-teal-light'}`}>
          <div className="stat-label text-2xs mono text-muted mb-1 flex-between">
            <span>Net Surface Delta (Δ)</span>
            {isLoss ? (
              <TrendingDown size={14} className="text-amber" />
            ) : (
              <TrendingUp size={14} className="text-teal" />
            )}
          </div>
          <div className={`stat-value mono text-lg font-bold ${isLoss ? 'text-amber' : 'text-teal'}`}>
            {metrics.absolute_change_ha > 0 ? `+${metrics.absolute_change_ha.toFixed(2)}` : metrics.absolute_change_ha.toFixed(2)}{' '}
            <span className="text-xs font-normal">ha</span>
          </div>
          <div className="stat-sub mono text-2xs text-muted mt-0.5">
            {metrics.percentage_change !== null
              ? `${metrics.percentage_change > 0 ? `+${metrics.percentage_change.toFixed(2)}` : metrics.percentage_change.toFixed(2)}% net change`
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* 4-Class Categorical Transition Breakdown */}
      <div className="transition-breakdown-box p-3 bg-slate rounded border border-subtle mb-4">
        <h4 className="text-xs font-semibold text-text-h mb-2.5 flex-center gap-1.5">
          <Layers size={13} className="text-forest" />
          <span>Categorical Water Dynamics Transitions</span>
        </h4>

        <div className="grid grid-cols-3 gap-3">
          {/* Persistent Water (Perennial) */}
          <div className="transition-col border-l-2 border-blue pl-2.5">
            <div className="text-2xs mono text-muted">Persistent Water (Perennial)</div>
            <div className="mono text-sm font-semibold text-blue mt-0.5">
              {metrics.persistent_water_ha.toFixed(2)} ha
            </div>
            <div className="mono text-3xs text-muted mt-0.5">
              {metrics.persistent_water_m2.toLocaleString()} m²
            </div>
          </div>

          {/* Apparent Loss (Recession) */}
          <div className="transition-col border-l-2 border-amber pl-2.5">
            <div className="text-2xs mono text-muted">Apparent Water Loss (Recession)</div>
            <div className="mono text-sm font-semibold text-amber mt-0.5">
              {metrics.apparent_loss_ha.toFixed(2)} ha
            </div>
            <div className="mono text-3xs text-muted mt-0.5">
              {metrics.apparent_loss_m2.toLocaleString()} m²
            </div>
          </div>

          {/* Apparent Gain (Inundation) */}
          <div className="transition-col border-l-2 border-teal pl-2.5">
            <div className="text-2xs mono text-muted">Apparent Water Gain (Inundation)</div>
            <div className="mono text-sm font-semibold text-teal mt-0.5">
              {metrics.apparent_gain_ha.toFixed(2)} ha
            </div>
            <div className="mono text-3xs text-muted mt-0.5">
              {metrics.apparent_gain_m2.toLocaleString()} m²
            </div>
          </div>
        </div>

        <div className="mt-3 pt-2 border-t border-subtle flex-between text-2xs mono text-muted">
          <span>Common Cloud-Free AOI Coverage:</span>
          <span>
            {metrics.common_valid_area_ha.toFixed(2)} ha ({metrics.common_valid_pixels.toLocaleString()} pixels)
          </span>
        </div>
      </div>

      {/* Mandatory Scientific Limitation Statement */}
      <div className="limitation-statement-box p-3 rounded border border-subtle flex-start gap-2.5 bg-canvas">
        <Info size={16} className="text-forest flex-shrink-0 mt-0.5" />
        <div className="text-2xs text-muted leading-relaxed">
          <strong className="text-text-h block mb-0.5">Hydrological Interpretation Note & Scientific Caveats:</strong>
          {metrics.limitation_statement}
        </div>
      </div>
    </div>
  );
};
