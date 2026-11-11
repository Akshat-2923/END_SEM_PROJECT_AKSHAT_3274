/**
 * Real-Time Satellite Analysis Lifecycle Tracker.
 * Manages polling GET /api/v1/analyses/{id} through QUEUED -> PROCESSING -> SUCCESS / FAILED,
 * and displays Sentinel-2 scene discovery metadata.
 */

import React, { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  Calendar,
  Cloud,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { AnalysisResponse } from '../types/api';
import { api } from '../services/api';

interface AnalysisStatusProps {
  analysis: AnalysisResponse;
  onAnalysisUpdated: (analysis: AnalysisResponse) => void;
}

export const AnalysisStatus: React.FC<AnalysisStatusProps> = ({
  analysis,
  onAnalysisUpdated,
}) => {
  const [elapsed, setElapsed] = useState<number>(0);

  // Poll status while job is active
  useEffect(() => {
    if (analysis.status === 'SUCCESS' || analysis.status === 'FAILED') {
      return;
    }

    const startTime = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const poller = setInterval(async () => {
      try {
        const fresh = await api.getAnalysis(analysis.id);
        onAnalysisUpdated(fresh);
        if (fresh.status === 'SUCCESS' || fresh.status === 'FAILED') {
          clearInterval(poller);
          clearInterval(timer);
        }
      } catch (err) {
        console.warn('Error polling analysis status:', err);
      }
    }, 2000);

    return () => {
      clearInterval(timer);
      clearInterval(poller);
    };
  }, [analysis.id, analysis.status, onAnalysisUpdated]);

  const isPending = analysis.status === 'QUEUED' || analysis.status === 'PROCESSING';

  return (
    <div className="analysis-status-card card p-4 mb-4">
      <div className="flex-between mb-3 border-b border-subtle pb-2">
        <div className="flex-center gap-2">
          <Activity size={18} className="text-forest" />
          <h4 className="card-subtitle">Run Lifecycle & Satellite Metadata</h4>
        </div>

        {/* Live Status Badge */}
        <div className="flex-center gap-2">
          {analysis.status === 'QUEUED' && (
            <span className="badge badge-queued flex-center gap-1">
              <Clock size={12} className="spin" />
              <span>QUEUED</span>
            </span>
          )}
          {analysis.status === 'PROCESSING' && (
            <span className="badge badge-processing flex-center gap-1">
              <Sparkles size={12} className="spin" />
              <span>PROCESSING PIPELINE</span>
            </span>
          )}
          {analysis.status === 'SUCCESS' && (
            <span className="badge badge-success flex-center gap-1">
              <CheckCircle size={12} />
              <span>SUCCESS</span>
            </span>
          )}
          {analysis.status === 'FAILED' && (
            <span className="badge badge-failed flex-center gap-1">
              <AlertCircle size={12} />
              <span>FAILED</span>
            </span>
          )}

          <span className="mono text-2xs text-muted">
            Run ID: {analysis.id.slice(0, 8)}...
          </span>
        </div>
      </div>

      {/* Progress / Failure banner */}
      {isPending && (
        <div className="pending-progress-banner p-3 mb-3 bg-slate rounded border border-subtle">
          <div className="flex-between text-xs mb-1.5">
            <span className="text-forest font-semibold flex-center gap-1">
              <Sparkles size={13} className="spin" />
              <span>Executing spectral index calculations & NDWI thresholding...</span>
            </span>
            <span className="mono text-muted">{elapsed}s elapsed</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill animated-shimmer" />
          </div>
        </div>
      )}

      {analysis.status === 'FAILED' && (
        <div className="alert alert-error text-xs mb-3">
          <div className="font-semibold mb-0.5">Analysis Pipeline Error</div>
          <div>{analysis.error_message || 'Unknown pipeline execution failure.'}</div>
        </div>
      )}

      {/* Sentinel-2 Discovery Metadata Grid */}
      <div className="satellite-metadata-grid grid grid-cols-2 gap-3">
        {/* T1 Baseline Observation */}
        <div className="observation-box p-3 bg-slate rounded border border-subtle">
          <div className="flex-between mb-2">
            <span className="badge badge-t1 mono text-2xs">T1: Post-Monsoon Baseline</span>
            <span className="mono text-2xs text-muted flex-center gap-1">
              <Calendar size={11} />
              {new Date(analysis.t1_date).toLocaleDateString()}
            </span>
          </div>
          <div className="mono text-xs font-semibold text-text-h truncate mb-1" title={analysis.t1_scene_id}>
            {analysis.t1_scene_id}
          </div>
          <div className="flex-between text-2xs text-muted mono">
            <span className="flex-center gap-1">
              <Cloud size={11} />
              <span>Cloud: {analysis.t1_cloud_cover !== null ? `${analysis.t1_cloud_cover.toFixed(1)}%` : 'N/A'}</span>
            </span>
            <span>B03 (Green) / B08 (NIR)</span>
          </div>
        </div>

        {/* T2 Later Observation */}
        <div className="observation-box p-3 bg-slate rounded border border-subtle">
          <div className="flex-between mb-2">
            <span className="badge badge-t2 mono text-2xs">T2: Pre-Monsoon Comparison</span>
            <span className="mono text-2xs text-muted flex-center gap-1">
              <Calendar size={11} />
              {new Date(analysis.t2_date).toLocaleDateString()}
            </span>
          </div>
          <div className="mono text-xs font-semibold text-text-h truncate mb-1" title={analysis.t2_scene_id}>
            {analysis.t2_scene_id}
          </div>
          <div className="flex-between text-2xs text-muted mono">
            <span className="flex-center gap-1">
              <Cloud size={11} />
              <span>Cloud: {analysis.t2_cloud_cover !== null ? `${analysis.t2_cloud_cover.toFixed(1)}%` : 'N/A'}</span>
            </span>
            <span>B03 (Green) / B08 (NIR)</span>
          </div>
        </div>
      </div>

      {/* Provider & Execution Metrics Footer */}
      <div className="mt-3 pt-2 border-t border-subtle flex-between text-2xs mono text-muted">
        <div className="flex-center gap-2">
          <span className="flex-center gap-1">
            <Layers size={11} />
            <span>Provider: {analysis.data_provider}</span>
          </span>
          <span>·</span>
          <span>
            {analysis.is_real_data ? (
              <span className="text-forest">Real Sentinel-2 Multi-spectral</span>
            ) : (
              <span className="text-amber">Synthetic Benchmark Calibration</span>
            )}
          </span>
        </div>
        {analysis.execution_duration_sec && (
          <div className="flex-center gap-1">
            <Clock size={11} />
            <span>Duration: {analysis.execution_duration_sec.toFixed(2)}s</span>
          </div>
        )}
      </div>
    </div>
  );
};
