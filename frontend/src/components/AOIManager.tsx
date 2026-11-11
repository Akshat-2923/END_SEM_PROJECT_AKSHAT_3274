/**
 * AOI Persistence and Catalog Management Component.
 * Enables saving validated polygons to the database (POST /api/v1/aois),
 * selecting saved reaches (GET /api/v1/aois), and managing visibility.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Bookmark, Plus, Trash2, Globe, Lock, Check } from 'lucide-react';
import type { AOIResponse, GeoJSONPolygon } from '../types/api';
import { api, APIError } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface AOIManagerProps {
  currentGeometry: GeoJSONPolygon;
  selectedAoiId: string | null;
  onSelectAoi: (aoi: AOIResponse | null) => void;
}

export const AOIManager: React.FC<AOIManagerProps> = ({
  currentGeometry,
  selectedAoiId,
  onSelectAoi,
}) => {
  const { isAuthenticated, user } = useAuth();
  const [aois, setAois] = useState<AOIResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [aoiName, setAoiName] = useState('Lucknow Gomti Urban Reach');
  const [aoiDesc, setAoiDesc] = useState('Sentinel-2 surface water monitoring reach');
  const [isPublic, setIsPublic] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAois = useCallback(async () => {
    if (!isAuthenticated) {
      setAois([]);
      return;
    }
    setLoading(true);
    try {
      const res = await api.listAOIs({ limit: 50 });
      setAois(res.items);
      setError(null);
    } catch (err: any) {
      console.warn('Failed to load AOIs:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchAois();
  }, [fetchAois]);

  const handleSaveAoi = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aoiName.trim()) return;
    setSaveLoading(true);
    setError(null);
    try {
      const saved = await api.createAOI({
        name: aoiName.trim(),
        description: aoiDesc.trim() || undefined,
        geometry: currentGeometry,
        is_public: isPublic,
      });
      setShowSaveDialog(false);
      onSelectAoi(saved);
      await fetchAois();
    } catch (err: any) {
      const detail = err instanceof APIError ? err.detail : err.message || 'Failed to save AOI';
      setError(detail);
    } finally {
      setSaveLoading(false);
    }
  };

  const handleDeleteAoi = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this AOI from the database?')) {
      return;
    }
    try {
      await api.deleteAOI(id);
      if (selectedAoiId === id) {
        onSelectAoi(null);
      }
      await fetchAois();
    } catch (err: any) {
      alert(err.detail || 'Failed to delete AOI');
    }
  };

  return (
    <div className="aoi-manager-box card p-3 mb-4">
      <div className="flex-between mb-3">
        <div className="flex-center gap-2">
          <Bookmark size={16} className="text-forest" />
          <h4 className="card-subtitle">Saved AOI Catalog</h4>
        </div>
        {isAuthenticated && (
          <button
            type="button"
            onClick={() => setShowSaveDialog(!showSaveDialog)}
            className="btn btn-xs btn-primary flex-center gap-1"
          >
            <Plus size={12} />
            <span>Save Active Reach</span>
          </button>
        )}
      </div>

      {/* Save Dialog Dropdown */}
      {showSaveDialog && (
        <form onSubmit={handleSaveAoi} className="save-aoi-form p-3 mb-3 border border-subtle bg-slate rounded">
          <h5 className="text-xs font-semibold mb-2">Persist Current Polygon to Database</h5>
          {error && <div className="alert alert-error text-xs mb-2">{error}</div>}
          <div className="form-group mb-2">
            <label className="form-label text-xs">Reach Name</label>
            <input
              type="text"
              className="form-input text-xs"
              value={aoiName}
              onChange={(e) => setAoiName(e.target.value)}
              placeholder="e.g. Lucknow Gomti Urban Reach"
              required
            />
          </div>
          <div className="form-group mb-2">
            <label className="form-label text-xs">Description (Optional)</label>
            <input
              type="text"
              className="form-input text-xs"
              value={aoiDesc}
              onChange={(e) => setAoiDesc(e.target.value)}
              placeholder="Monitoring notes, reach boundaries"
            />
          </div>
          <div className="flex-between mb-3">
            <label className="flex-center gap-2 text-xs text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
              />
              <span>Make Public to Other Users</span>
            </label>
          </div>
          <div className="flex-end gap-2">
            <button
              type="button"
              onClick={() => setShowSaveDialog(false)}
              className="btn btn-xs btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saveLoading}
              className="btn btn-xs btn-primary"
            >
              {saveLoading ? 'Saving...' : 'Save AOI'}
            </button>
          </div>
        </form>
      )}

      {/* AOI Selection List */}
      <div className="aoi-items-list">
        {loading ? (
          <div className="text-muted text-xs p-2 text-center">Loading catalog...</div>
        ) : aois.length === 0 ? (
          <div className="text-muted text-xs p-2 text-center border border-dashed border-subtle rounded">
            No saved reaches yet. Save current geometry or proceed with inline polygon.
          </div>
        ) : (
          <div className="flex-col gap-1.5 max-h-40 overflow-y-auto">
            {aois.map((aoi) => {
              const isSelected = aoi.id === selectedAoiId;
              const isOwner = user?.id === aoi.user_id || user?.role === 'admin';
              return (
                <div
                  key={aoi.id}
                  onClick={() => onSelectAoi(isSelected ? null : aoi)}
                  className={`aoi-item-row flex-between p-2 rounded cursor-pointer ${
                    isSelected ? 'bg-forest-light border-forest' : 'bg-slate border-subtle'
                  } border`}
                >
                  <div className="flex-center gap-2 text-xs">
                    {aoi.is_public ? (
                      <span title="Public reach">
                        <Globe size={13} className="text-muted" />
                      </span>
                    ) : (
                      <span title="Private reach">
                        <Lock size={13} className="text-muted" />
                      </span>
                    )}
                    <div>
                      <div className="font-semibold text-text-h">{aoi.name}</div>
                      <div className="mono text-2xs text-muted">
                        {aoi.area_km2.toFixed(2)} km² · {aoi.vertex_count} vertices
                      </div>
                    </div>
                  </div>

                  <div className="flex-center gap-2">
                    {isSelected && <Check size={14} className="text-forest" />}
                    {isOwner && (
                      <button
                        type="button"
                        onClick={(e) => handleDeleteAoi(aoi.id, e)}
                        className="btn btn-icon btn-ghost btn-xs text-muted hover-text-red"
                        title="Delete AOI"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
