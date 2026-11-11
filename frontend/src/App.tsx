/**
 * DharaScope Application Main Dashboard.
 * Enterprise GIS Workstation combining Leaflet AOI mapping, PostGIS geometry validation,
 * Sentinel-2 multi-temporal analysis execution, quantitative metrics, and publication reports.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/Header';
import { AuthModal } from './components/AuthModal';
import { MapPicker, LUCKNOW_GOMTI_PRESET } from './components/MapPicker';
import { AOIManager } from './components/AOIManager';
import { AnalysisForm } from './components/AnalysisForm';
import { AnalysisStatus } from './components/AnalysisStatus';
import { MetricsDisplay } from './components/MetricsDisplay';
import { ArtifactsViewer } from './components/ArtifactsViewer';
import { ReportActions } from './components/ReportActions';
import { AnalysisHistory } from './components/AnalysisHistory';
import type {
  GeoJSONPolygon,
  AOIResponse,
  AnalysisResponse,
  WaterMetricsResponse,
  ArtifactResponse,
} from './types/api';
import { api } from './services/api';
import { Satellite, Sparkles } from 'lucide-react';

const DashboardContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);

  // AOI State
  const [currentGeometry, setCurrentGeometry] = useState<GeoJSONPolygon>(LUCKNOW_GOMTI_PRESET);
  const [selectedAoi, setSelectedAoi] = useState<AOIResponse | null>(null);

  // Analysis State
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisResponse | null>(null);
  const [metrics, setMetrics] = useState<WaterMetricsResponse | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactResponse[]>([]);
  const [loadingResults, setLoadingResults] = useState(false);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  // Fetch metrics and artifacts when active analysis succeeds
  const loadAnalysisDetails = useCallback(async (analysisId: string) => {
    setLoadingResults(true);
    try {
      const [metricsData, artifactsData] = await Promise.all([
        api.getAnalysisMetrics(analysisId).catch((err) => {
          console.warn('Metrics fetch error:', err);
          return null;
        }),
        api.getAnalysisArtifacts(analysisId).catch((err) => {
          console.warn('Artifacts fetch error:', err);
          return { items: [], total: 0 };
        }),
      ]);
      setMetrics(metricsData);
      setArtifacts(artifactsData.items);
    } finally {
      setLoadingResults(false);
    }
  }, []);

  // Handle active analysis state transitions
  useEffect(() => {
    if (activeAnalysis?.status === 'SUCCESS') {
      loadAnalysisDetails(activeAnalysis.id);
    } else {
      setMetrics(null);
      setArtifacts([]);
    }
  }, [activeAnalysis?.status, activeAnalysis?.id, loadAnalysisDetails]);

  // When an AOI is selected from catalog
  const handleSelectAoi = (aoi: AOIResponse | null) => {
    setSelectedAoi(aoi);
    if (aoi && aoi.geometry && aoi.geometry.type === 'Polygon') {
      setCurrentGeometry(aoi.geometry as GeoJSONPolygon);
    }
  };

  // When a new analysis is launched
  const handleAnalysisCreated = (analysis: AnalysisResponse) => {
    setActiveAnalysis(analysis);
    setHistoryRefreshKey((prev) => prev + 1);
  };

  // When polling updates the active analysis
  const handleAnalysisUpdated = (updated: AnalysisResponse) => {
    setActiveAnalysis(updated);
    if (updated.status === 'SUCCESS' || updated.status === 'FAILED') {
      setHistoryRefreshKey((prev) => prev + 1);
    }
  };

  // When selecting a run from history drawer
  const handleSelectHistoricalRun = (run: AnalysisResponse) => {
    setActiveAnalysis(run);
  };

  const handleDeleteHistoricalRun = (deletedId: string) => {
    if (activeAnalysis?.id === deletedId) {
      setActiveAnalysis(null);
      setMetrics(null);
      setArtifacts([]);
    }
  };

  return (
    <div className="dharascope-app">
      <Header onOpenAuthModal={() => setAuthModalOpen(true)} />

      <main className="dashboard-layout grid grid-cols-12 gap-5 p-5">
        {/* Left Column: AOI Definition & Satellite Pipeline Controls (5 cols) */}
        <div className="col-span-12 lg:col-span-5 flex-col gap-4">
          <MapPicker
            geometry={currentGeometry}
            onChangeGeometry={(geom) => {
              setCurrentGeometry(geom);
              setSelectedAoi(null);
            }}
          />

          <AOIManager
            currentGeometry={currentGeometry}
            selectedAoiId={selectedAoi?.id || null}
            onSelectAoi={handleSelectAoi}
          />

          <AnalysisForm
            currentGeometry={currentGeometry}
            selectedAoiId={selectedAoi?.id || null}
            onAnalysisCreated={handleAnalysisCreated}
          />

          <AnalysisHistory
            selectedAnalysisId={activeAnalysis?.id || null}
            onSelectAnalysis={handleSelectHistoricalRun}
            onDeleteAnalysis={handleDeleteHistoricalRun}
            refreshTrigger={historyRefreshKey}
          />
        </div>

        {/* Right Column: Execution Status, Scientific Metrics, Cartography & Reports (7 cols) */}
        <div className="col-span-12 lg:col-span-7 flex-col gap-4">
          {activeAnalysis ? (
            <>
              <AnalysisStatus
                analysis={activeAnalysis}
                onAnalysisUpdated={handleAnalysisUpdated}
              />

              {loadingResults && (
                <div className="card p-8 flex-center flex-col gap-2 bg-slate text-center mb-4">
                  <Sparkles size={24} className="spin text-forest" />
                  <span className="mono text-sm text-text-h">
                    Aggregating water metrics and indexing cartographic artifacts...
                  </span>
                </div>
              )}

              {metrics && (
                <MetricsDisplay
                  metrics={metrics}
                  isRealData={activeAnalysis.is_real_data}
                />
              )}

              {artifacts.length > 0 && (
                <ArtifactsViewer
                  artifacts={artifacts}
                  analysisId={activeAnalysis.id}
                  isRealData={activeAnalysis.is_real_data}
                />
              )}

              {activeAnalysis.status === 'SUCCESS' && (
                <ReportActions analysisId={activeAnalysis.id} />
              )}
            </>
          ) : (
            <div className="empty-state-card card p-10 text-center flex-center flex-col gap-3">
              <div className="empty-icon-box p-4 bg-slate rounded-full border border-subtle">
                <Satellite size={40} className="text-forest" />
              </div>
              <h2 className="text-xl font-semibold text-text-h">
                Sentinel-2 Surface Water Dynamics Station
              </h2>
              <p className="text-sm text-muted max-w-md">
                Select an Area of Interest on the map or choose a saved reach from the catalog.
                Configure the NDWI segmentation cutoff threshold (τ) and launch a multi-temporal analysis
                to view surface water change metrics, cartographic maps, and download reports.
              </p>

              {!isAuthenticated && (
                <button
                  type="button"
                  onClick={() => setAuthModalOpen(true)}
                  className="btn btn-primary btn-sm mt-3"
                >
                  Connect Session to Begin
                </button>
              )}
            </div>
          )}
        </div>
      </main>

      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
      />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  );
}
