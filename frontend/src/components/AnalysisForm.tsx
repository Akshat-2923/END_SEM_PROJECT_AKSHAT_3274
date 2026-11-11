/**
 * Multi-Temporal Satellite Surface Water Analysis Control Form.
 * Configures NDWI threshold (tau in [-0.30, 0.30]), cloud cover filter (<=10%),
 * temporal search window, and satellite data retrieval tier.
 */

import React, { useState } from 'react';
import { Sliders, Play, Clock, Cloud, Layers, Zap } from 'lucide-react';
import type { AnalysisCreateRequest, GeoJSONPolygon, AnalysisResponse } from '../types/api';
import { api, APIError } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface AnalysisFormProps {
  currentGeometry: GeoJSONPolygon;
  selectedAoiId: string | null;
  onAnalysisCreated: (analysis: AnalysisResponse) => void;
}

export const AnalysisForm: React.FC<AnalysisFormProps> = ({
  currentGeometry,
  selectedAoiId,
  onAnalysisCreated,
}) => {
  const { isAuthenticated, user } = useAuth();

  const [ndwiThreshold, setNdwiThreshold] = useState<number>(0.0);
  const [maxCloudCover, setMaxCloudCover] = useState<number>(10.0);
  const [datetimeRange, setDatetimeRange] = useState<string>(
    '2023-10-01T00:00:00Z/2024-05-31T23:59:59Z'
  );
  const [dataSource, setDataSource] = useState<'auto' | 'cdse' | 'public' | 'synthetic'>('auto');
  const [syncMode, setSyncMode] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) return;

    setIsSubmitting(true);
    setSubmitError(null);

    const payload: AnalysisCreateRequest = {
      ndwi_threshold: ndwiThreshold,
      max_cloud_cover: maxCloudCover,
      datetime_range: datetimeRange,
      data_source: dataSource,
    };

    if (selectedAoiId) {
      payload.aoi_id = selectedAoiId;
    } else {
      payload.aoi_geometry = currentGeometry;
      payload.aoi_name = 'Ad-hoc Gomti Analysis Reach';
    }

    try {
      const response = await api.createAnalysis(payload, syncMode);
      onAnalysisCreated(response);
    } catch (err: any) {
      const detail = err instanceof APIError ? err.detail : err.message || 'Failed to dispatch analysis';
      setSubmitError(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="analysis-form-card card p-4 mb-4">
      <div className="card-header mb-3 flex-between">
        <div className="flex-center gap-2">
          <Sliders size={18} className="text-forest" />
          <h3 className="card-title">Analysis Parameters & Execution</h3>
        </div>
        <span className="badge badge-neutral mono text-xs">Sentinel-2 L2A</span>
      </div>

      {submitError && (
        <div className="alert alert-error text-xs mb-3">
          {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* NDWI Water Classification Threshold */}
        <div className="form-group mb-4">
          <div className="flex-between mb-1">
            <label className="form-label text-xs font-semibold">
              NDWI Classification Threshold (τ)
            </label>
            <span className="mono text-xs text-forest font-bold">
              {ndwiThreshold >= 0 ? `+${ndwiThreshold.toFixed(2)}` : ndwiThreshold.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="-0.30"
            max="0.30"
            step="0.01"
            className="form-range"
            value={ndwiThreshold}
            onChange={(e) => setNdwiThreshold(parseFloat(e.target.value))}
          />
          <div className="flex-between text-2xs mono text-muted mt-0.5">
            <span>-0.30 (Turbid / Wet Soil)</span>
            <span>0.00 (Standard Water)</span>
            <span>+0.30 (Deep Clear Water)</span>
          </div>
        </div>

        {/* Cloud Cover Filter */}
        <div className="form-group mb-4">
          <div className="flex-between mb-1">
            <label className="form-label text-xs font-semibold flex-center gap-1">
              <Cloud size={13} />
              <span>Max Scene Cloud Cover</span>
            </label>
            <span className="mono text-xs font-bold text-amber">
              {maxCloudCover.toFixed(1)}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="30"
            step="1"
            className="form-range"
            value={maxCloudCover}
            onChange={(e) => setMaxCloudCover(parseFloat(e.target.value))}
          />
          <div className="flex-between text-2xs mono text-muted mt-0.5">
            <span>0% (Pristine)</span>
            <span>10% (Recommended)</span>
            <span>30% (Permissive)</span>
          </div>
        </div>

        {/* Temporal Search Window */}
        <div className="form-group mb-4">
          <label className="form-label text-xs font-semibold flex-center gap-1 mb-1">
            <Clock size={13} />
            <span>Temporal Search Interval (ISO-8601)</span>
          </label>
          <input
            type="text"
            className="form-input mono text-xs"
            value={datetimeRange}
            onChange={(e) => setDatetimeRange(e.target.value)}
            placeholder="2023-10-01T00:00:00Z/2024-05-31T23:59:59Z"
            required
          />
          <span className="form-hint text-2xs text-muted mt-1 block">
            Post-monsoon (T1: Oct-Nov) vs Pre-monsoon (T2: Apr-May) seasonal cycle.
          </span>
        </div>

        {/* Satellite Data Provider Tier */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="form-group">
            <label className="form-label text-xs font-semibold flex-center gap-1 mb-1">
              <Layers size={13} />
              <span>Retrieval Tier</span>
            </label>
            <select
              className="form-select text-xs"
              value={dataSource}
              onChange={(e) => setDataSource(e.target.value as any)}
            >
              <option value="auto">Auto (CDSE &gt; Public STAC &gt; Cache)</option>
              <option value="cdse">Copernicus Data Space (CDSE)</option>
              <option value="public">Earth Search / AWS STAC</option>
              <option value="synthetic">Synthetic GIS Benchmark</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label text-xs font-semibold flex-center gap-1 mb-1">
              <Zap size={13} />
              <span>Execution Mode</span>
            </label>
            <div className="flex-center gap-2 pt-1.5">
              <label className="text-xs flex-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={syncMode}
                  onChange={(e) => setSyncMode(e.target.checked)}
                />
                <span className="mono text-2xs">Synchronous (?sync=true)</span>
              </label>
            </div>
          </div>
        </div>

        {/* Submit Execution Button */}
        <button
          type="submit"
          disabled={!isAuthenticated || isSubmitting || (user?.quota_monthly_runs ?? 0) <= 0}
          className="btn btn-primary btn-block flex-center gap-2 py-2.5"
        >
          <Play size={16} />
          <span className="font-semibold">
            {isSubmitting
              ? 'Dispatching Analysis...'
              : !isAuthenticated
              ? 'Sign In to Run Analysis'
              : 'Launch Surface Water Analysis'}
          </span>
        </button>
      </form>
    </div>
  );
};
