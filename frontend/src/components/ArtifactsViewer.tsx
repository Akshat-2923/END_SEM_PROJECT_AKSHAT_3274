/**
 * Cartographic Visualization and Generated Artifacts Viewer.
 * Securely streams generated PNGs via authenticated downloads,
 * provides multi-panel comparison tabs, and renders the 4-class categorical GIS legend.
 */

import React, { useEffect, useState } from 'react';
import {
  Image as ImageIcon,
  Download,
  Eye,
  Layers,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import type { ArtifactResponse } from '../types/api';
import { api, getAuthToken, API_BASE_URL } from '../services/api';

interface ArtifactsViewerProps {
  artifacts: ArtifactResponse[];
  analysisId?: string;
  isRealData?: boolean;
}

/**
 * Authenticated Image component that loads binary blobs using Bearer tokens.
 */
const AuthenticatedImage: React.FC<{
  url: string;
  alt: string;
  className?: string;
}> = ({ url, alt, className }) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL.replace(/\/api\/v1\/?$/, '')}${url}`;

    async function loadImage() {
      try {
        setLoading(true);
        setError(false);
        const token = getAuthToken();
        const headers = new Headers();
        if (token) headers.set('Authorization', `Bearer ${token}`);

        const res = await fetch(fullUrl, { headers });
        if (!res.ok) throw new Error('Image fetch failed');
        const blob = await res.blob();
        if (active) {
          const objUrl = URL.createObjectURL(blob);
          setBlobUrl(objUrl);
        }
      } catch {
        if (active) setError(true);
      } finally {
        if (active) setLoading(false);
      }
    }

    loadImage();

    return () => {
      active = false;
      setBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [url]);

  if (loading) {
    return (
      <div className="authenticated-image-loading flex-center flex-col gap-2 p-8 bg-slate rounded">
        <Sparkles size={20} className="spin text-forest" />
        <span className="mono text-xs text-muted">Streaming raster cartography...</span>
      </div>
    );
  }

  if (error || !blobUrl) {
    return (
      <div className="authenticated-image-error flex-center flex-col gap-2 p-8 bg-slate rounded text-muted">
        <ImageIcon size={24} />
        <span className="mono text-xs">Failed to stream raster image artifact</span>
      </div>
    );
  }

  return <img src={blobUrl} alt={alt} className={className} />;
};

export const ArtifactsViewer: React.FC<ArtifactsViewerProps> = ({
  artifacts,
  isRealData = true,
}) => {
  // Filter for visual image artifacts (excluding PDF/CSV reports)
  const visualArtifacts = artifacts.filter(
    (a) =>
      a.artifact_type === 'PANEL_PNG' ||
      a.artifact_type === 'MAP_PNG' ||
      a.artifact_type === 'THUMBNAIL_JPG'
  );

  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(
    visualArtifacts[0]?.id || null
  );

  useEffect(() => {
    if (!selectedArtifactId && visualArtifacts.length > 0) {
      setSelectedArtifactId(visualArtifacts[0].id);
    }
  }, [visualArtifacts, selectedArtifactId]);

  const activeArtifact = visualArtifacts.find((a) => a.id === selectedArtifactId) || visualArtifacts[0];

  const handleDownload = (art: ArtifactResponse) => {
    api.downloadArtifact(art.id, art.file_name);
  };

  return (
    <div className="artifacts-viewer-card card p-4 mb-4">
      {/* Synthetic Benchmark Warning Banner */}
      {!isRealData && (
        <div className="alert alert-warning text-xs mb-3 flex-start gap-2 border border-amber bg-amber-light">
          <AlertTriangle size={16} className="text-amber flex-shrink-0 mt-0.5" />
          <div>
            <strong className="text-amber block font-semibold">SYNTHETIC BENCHMARK CARTOGRAPHY</strong>
            <span className="text-muted">
              These cartographic layers and thumbnails are rendered from synthetic benchmark raster data.
              They are for offline calibration testing only and do NOT depict real satellite observations.
            </span>
          </div>
        </div>
      )}

      <div className="card-header mb-3 flex-between">
        <div className="flex-center gap-2">
          <Layers size={18} className="text-forest" />
          <h3 className="card-title">Cartographic Visualizations & Generated Maps</h3>
        </div>
        <span className="badge badge-neutral mono text-xs">
          {visualArtifacts.length} Visual Map Layers
        </span>
      </div>

      {/* 4-Class Categorical GIS Map Legend */}
      <div className="cartographic-legend-box p-2.5 mb-3 bg-slate rounded border border-subtle">
        <div className="mono text-2xs font-semibold text-muted mb-1.5 flex-center gap-1">
          <span>Standard 4-Class Categorical Water Dynamics Legend:</span>
        </div>
        <div className="grid grid-cols-4 gap-2 text-2xs mono">
          <div className="flex-center gap-1.5">
            <span className="legend-swatch bg-blue" />
            <span className="text-text-h">Persistent Water</span>
          </div>
          <div className="flex-center gap-1.5">
            <span className="legend-swatch bg-teal" />
            <span className="text-text-h">Apparent Gain (Inundation)</span>
          </div>
          <div className="flex-center gap-1.5">
            <span className="legend-swatch bg-amber" />
            <span className="text-text-h">Apparent Loss (Recession)</span>
          </div>
          <div className="flex-center gap-1.5">
            <span className="legend-swatch bg-slate-gray" />
            <span className="text-muted">Persistent Non-Water</span>
          </div>
        </div>
      </div>

      {/* Artifact Tabs Selector */}
      {visualArtifacts.length > 0 ? (
        <>
          <div className="artifact-tabs flex-start gap-1.5 mb-3 overflow-x-auto pb-1 border-b border-subtle">
            {visualArtifacts.map((art) => {
              const isSelected = art.id === activeArtifact?.id;
              const label = art.file_name
                .replace(/^dharascope_/, '')
                .replace(/\.(png|jpg)$/, '')
                .replace(/_/g, ' ');
              return (
                <button
                  key={art.id}
                  onClick={() => setSelectedArtifactId(art.id)}
                  className={`btn btn-xs ${
                    isSelected ? 'btn-primary' : 'btn-ghost'
                  } mono text-2xs truncate max-w-xs`}
                  title={art.file_name}
                >
                  <Eye size={11} className="mr-1 inline" />
                  {label}
                </button>
              );
            })}
          </div>

          {/* Active Artifact Display Stage */}
          {activeArtifact && (
            <div className="artifact-stage-container p-2 bg-canvas rounded border border-subtle">
              <div className="flex-between mb-2 px-1">
                <span className="mono text-xs text-text-h truncate font-semibold">
                  {activeArtifact.file_name}
                </span>
                <button
                  type="button"
                  onClick={() => handleDownload(activeArtifact)}
                  className="btn btn-xs btn-outline flex-center gap-1 mono text-2xs"
                  title="Download raw map image"
                >
                  <Download size={11} />
                  <span>Download Image</span>
                </button>
              </div>

              <div className="artifact-image-wrapper flex-center overflow-hidden rounded bg-black">
                <AuthenticatedImage
                  url={activeArtifact.download_url}
                  alt={activeArtifact.file_name}
                  className="artifact-main-img"
                />
              </div>

              <div className="mt-2 flex-between text-2xs mono text-muted px-1">
                <span>MIME: {activeArtifact.mime_type}</span>
                <span>
                  {activeArtifact.file_size_bytes
                    ? `${(activeArtifact.file_size_bytes / 1024).toFixed(1)} KB`
                    : ''}
                </span>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-muted text-xs p-6 text-center bg-slate rounded border border-subtle">
          No visual map artifacts registered for this run.
        </div>
      )}
    </div>
  );
};
