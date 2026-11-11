/**
 * Authenticated Report Downloads Component.
 * Dispatches streaming downloads for publication-ready PDF and structured CSV reports
 * with Bearer token authentication and download progress tracking.
 */

import React, { useState } from 'react';
import { FileText, FileSpreadsheet, Download, Sparkles, CheckCircle, AlertCircle } from 'lucide-react';
import { api, APIError } from '../services/api';

interface ReportActionsProps {
  analysisId: string;
}

export const ReportActions: React.FC<ReportActionsProps> = ({ analysisId }) => {
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);

  const handleDownload = async (type: 'pdf' | 'csv') => {
    setStatusMessage(null);
    setIsError(false);
    if (type === 'pdf') setDownloadingPdf(true);
    else setDownloadingCsv(true);

    try {
      await api.downloadReport(analysisId, type);
      setStatusMessage(`Successfully downloaded ${type.toUpperCase()} report.`);
    } catch (err: any) {
      setIsError(true);
      const detail = err instanceof APIError ? err.detail : err.message || 'Download failed';
      setStatusMessage(detail);
    } finally {
      if (type === 'pdf') setDownloadingPdf(false);
      else setDownloadingCsv(false);
    }
  };

  return (
    <div className="report-actions-card card p-4 mb-4">
      <div className="card-header mb-3 flex-between">
        <div className="flex-center gap-2">
          <Download size={18} className="text-forest" />
          <h3 className="card-title">Scientific Report & Data Export</h3>
        </div>
        <span className="mono text-2xs text-muted">Immutable Manifest</span>
      </div>

      {statusMessage && (
        <div className={`alert ${isError ? 'alert-error' : 'alert-success'} text-xs mb-3`}>
          {isError ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
          <span>{statusMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {/* PDF Report Download Button */}
        <div className="report-option-box p-3 bg-slate rounded border border-subtle flex-between">
          <div className="flex-start gap-2.5">
            <FileText size={28} className="text-forest flex-shrink-0" />
            <div>
              <div className="font-semibold text-xs text-text-h">Publication PDF Report</div>
              <div className="text-2xs text-muted mt-0.5">
                ReportLab generated · Figures, metrics, & scientific caveats
              </div>
            </div>
          </div>
          <button
            type="button"
            disabled={downloadingPdf}
            onClick={() => handleDownload('pdf')}
            className="btn btn-primary btn-sm flex-center gap-1.5 mono text-xs"
          >
            {downloadingPdf ? (
              <>
                <Sparkles size={13} className="spin" />
                <span>Downloading...</span>
              </>
            ) : (
              <>
                <Download size={13} />
                <span>PDF</span>
              </>
            )}
          </button>
        </div>

        {/* CSV Report Download Button */}
        <div className="report-option-box p-3 bg-slate rounded border border-subtle flex-between">
          <div className="flex-start gap-2.5">
            <FileSpreadsheet size={28} className="text-teal flex-shrink-0" />
            <div>
              <div className="font-semibold text-xs text-text-h">CSV Data Manifest</div>
              <div className="text-2xs text-muted mt-0.5">
                Structured tabular data · Pixel counts, areas, & timestamps
              </div>
            </div>
          </div>
          <button
            type="button"
            disabled={downloadingCsv}
            onClick={() => handleDownload('csv')}
            className="btn btn-outline btn-sm flex-center gap-1.5 mono text-xs"
          >
            {downloadingCsv ? (
              <>
                <Sparkles size={13} className="spin" />
                <span>Downloading...</span>
              </>
            ) : (
              <>
                <Download size={13} />
                <span>CSV</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
