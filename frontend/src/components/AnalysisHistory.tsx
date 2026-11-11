/**
 * Analysis Runs History and Archive Drawer.
 * Fetches user's historical runs (GET /api/v1/analyses), enables 1-click loading
 * of past runs into the dashboard, and supports run deletion.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { History, RefreshCw, Trash2, CheckCircle, AlertCircle, Clock, ChevronRight } from 'lucide-react';
import type { AnalysisResponse } from '../types/api';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface AnalysisHistoryProps {
  selectedAnalysisId: string | null;
  onSelectAnalysis: (analysis: AnalysisResponse) => void;
  onDeleteAnalysis?: (deletedId: string) => void;
  refreshTrigger?: number;
}

export const AnalysisHistory: React.FC<AnalysisHistoryProps> = ({
  selectedAnalysisId,
  onSelectAnalysis,
  onDeleteAnalysis,
  refreshTrigger = 0,
}) => {
  const { isAuthenticated } = useAuth();
  const [runs, setRuns] = useState<AnalysisResponse[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchRuns = useCallback(async () => {
    if (!isAuthenticated) {
      setRuns([]);
      return;
    }
    setLoading(true);
    try {
      const res = await api.listAnalyses({ limit: 20 });
      setRuns(res.items);
    } catch (e) {
      console.warn('Failed to load past runs:', e);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns, refreshTrigger]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this analysis run and all associated metrics and artifacts?')) {
      return;
    }
    try {
      await api.deleteAnalysis(id);
      if (onDeleteAnalysis) onDeleteAnalysis(id);
      await fetchRuns();
    } catch (err: any) {
      alert(err.detail || 'Failed to delete analysis run');
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="analysis-history-card card p-4 mb-4">
      <div className="flex-between mb-3 border-b border-subtle pb-2">
        <div className="flex-center gap-2">
          <History size={18} className="text-forest" />
          <h4 className="card-subtitle">Recent Analysis Runs Archive</h4>
        </div>
        <button
          type="button"
          onClick={fetchRuns}
          disabled={loading}
          className="btn btn-icon btn-ghost btn-xs text-muted"
          title="Refresh run history"
        >
          <RefreshCw size={12} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {loading && runs.length === 0 ? (
        <div className="text-muted text-xs p-3 text-center">Loading run history...</div>
      ) : runs.length === 0 ? (
        <div className="text-muted text-xs p-4 text-center border border-dashed border-subtle rounded">
          No analysis runs recorded yet. Configure parameters above and launch an analysis.
        </div>
      ) : (
        <div className="history-runs-list flex-col gap-2 max-h-56 overflow-y-auto">
          {runs.map((run) => {
            const isSelected = run.id === selectedAnalysisId;
            return (
              <div
                key={run.id}
                onClick={() => onSelectAnalysis(run)}
                className={`history-item p-2.5 rounded cursor-pointer border flex-between ${
                  isSelected ? 'bg-forest-light border-forest' : 'bg-slate border-subtle'
                }`}
              >
                <div className="flex-start gap-2 text-xs">
                  {run.status === 'SUCCESS' && <CheckCircle size={15} className="text-forest mt-0.5" />}
                  {run.status === 'FAILED' && <AlertCircle size={15} className="text-amber mt-0.5" />}
                  {run.status === 'PROCESSING' && <Clock size={15} className="text-teal spin mt-0.5" />}
                  {run.status === 'QUEUED' && <Clock size={15} className="text-muted mt-0.5" />}

                  <div>
                    <div className="flex-center gap-2">
                      <span className="font-semibold text-text-h mono text-xs">
                        {run.id.slice(0, 8)}...
                      </span>
                      <span className="badge badge-neutral mono text-3xs">
                        τ={run.ndwi_threshold.toFixed(2)}
                      </span>
                      <span className="mono text-3xs text-muted">
                        {run.is_real_data ? 'Real S2' : 'Synthetic'}
                      </span>
                    </div>

                    <div className="text-3xs text-muted mono mt-0.5">
                      {new Date(run.created_at).toLocaleString()}
                      {run.execution_duration_sec && ` · ${run.execution_duration_sec.toFixed(1)}s`}
                    </div>
                  </div>
                </div>

                <div className="flex-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => handleDelete(run.id, e)}
                    className="btn btn-icon btn-ghost btn-xs text-muted hover-text-red"
                    title="Delete run"
                  >
                    <Trash2 size={12} />
                  </button>
                  <ChevronRight size={14} className="text-muted" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
