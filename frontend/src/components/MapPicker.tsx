/**
 * Interactive Leaflet Cartographic AOI Picker with Real Backend Validation.
 * Validates topology, ellipsoidal area, bounding box, and vertex limits via POST /api/v1/aois/validate.
 */

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  MapPin,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  Code,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { GeoJSONPolygon, AOIValidateResponse } from '../types/api';
import { api, APIError } from '../services/api';
import { useAuth } from '../context/AuthContext';

// Canonical Lucknow Gomti River urban reach baseline polygon
export const LUCKNOW_GOMTI_PRESET: GeoJSONPolygon = {
  type: 'Polygon',
  coordinates: [
    [
      [80.90, 26.84],
      [80.92, 26.84],
      [80.92, 26.86],
      [80.90, 26.86],
      [80.90, 26.84],
    ],
  ],
};

interface MapPickerProps {
  geometry: GeoJSONPolygon;
  onChangeGeometry: (geom: GeoJSONPolygon) => void;
  onValidationSuccess?: (result: AOIValidateResponse) => void;
}

export const MapPicker: React.FC<MapPickerProps> = ({
  geometry,
  onChangeGeometry,
  onValidationSuccess,
}) => {
  const { isAuthenticated } = useAuth();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const polygonLayerRef = useRef<L.Polygon | null>(null);

  const [validationResult, setValidationResult] = useState<AOIValidateResponse | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showJsonEditor, setShowJsonEditor] = useState(false);
  const [jsonText, setJsonText] = useState(JSON.stringify(geometry, null, 2));

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    // Default center on Lucknow, India (26.85°N, 80.91°E)
    const map = L.map(mapContainerRef.current, {
      center: [26.85, 80.91],
      zoom: 13,
      zoomControl: true,
      attributionControl: false,
    });

    // Dark GIS Basemap (CartoDB Dark Matter) with fallback to OSM
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
    }).addTo(map);

    // Custom attribution
    L.control
      .attribution({
        position: 'bottomright',
        prefix: 'Leaflet · CartoDB · Copernicus Sentinel-2',
      })
      .addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Leaflet polygon and pan bounds whenever geometry changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    try {
      const coords = geometry.coordinates[0];
      // Leaflet expects [lat, lon], while GeoJSON stores [lon, lat]
      const latLngs: L.LatLngExpression[] = coords.map(([lon, lat]) => [lat, lon]);

      if (polygonLayerRef.current) {
        polygonLayerRef.current.setLatLngs(latLngs);
      } else {
        const poly = L.polygon(latLngs, {
          color: '#2d6a4f',
          weight: 2.5,
          opacity: 0.9,
          fillColor: '#2d6a4f',
          fillOpacity: 0.25,
          dashArray: '4, 4',
        }).addTo(map);
        polygonLayerRef.current = poly;
      }

      const bounds = L.latLngBounds(latLngs);
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [25, 25], maxZoom: 14 });
      }
    } catch (e) {
      console.warn('Error updating Leaflet polygon layer:', e);
    }
  }, [geometry]);

  // Execute backend validation via POST /api/v1/aois/validate
  useEffect(() => {
    let active = true;

    async function runValidation() {
      if (!isAuthenticated) {
        setValidationError('Authentication required to validate geometry.');
        setValidationResult(null);
        return;
      }

      setIsValidating(true);
      setValidationError(null);

      try {
        const res = await api.validateAOI({ geometry });
        if (active) {
          setValidationResult(res);
          setValidationError(null);
          if (onValidationSuccess) {
            onValidationSuccess(res);
          }
        }
      } catch (err: any) {
        if (active) {
          setValidationResult(null);
          const detail = err instanceof APIError ? err.detail : err.message || 'Validation failed';
          setValidationError(detail);
        }
      } finally {
        if (active) setIsValidating(false);
      }
    }

    runValidation();

    return () => {
      active = false;
    };
  }, [geometry, isAuthenticated, onValidationSuccess]);

  const handleResetGomti = () => {
    onChangeGeometry(LUCKNOW_GOMTI_PRESET);
    setJsonText(JSON.stringify(LUCKNOW_GOMTI_PRESET, null, 2));
  };

  const handleApplyJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      if (!parsed || parsed.type !== 'Polygon' || !Array.isArray(parsed.coordinates)) {
        throw new Error('Must be a GeoJSON Polygon with coordinates array.');
      }
      onChangeGeometry(parsed);
      setShowJsonEditor(false);
    } catch (e: any) {
      setValidationError(`Invalid JSON syntax: ${e.message}`);
    }
  };

  return (
    <div className="map-picker-card card">
      {/* Card Header & Actions */}
      <div className="card-header flex-between">
        <div className="flex-center gap-2">
          <MapPin size={18} className="text-forest" />
          <h3 className="card-title">Geographical Area of Interest (AOI)</h3>
        </div>
        <div className="flex-center gap-2">
          <button
            type="button"
            onClick={handleResetGomti}
            className="btn btn-xs btn-outline flex-center gap-1"
            title="Reset to Lucknow Gomti River urban study reach"
          >
            <RotateCcw size={12} />
            <span>Gomti Reach (Lucknow)</span>
          </button>
          <button
            type="button"
            onClick={() => setShowJsonEditor(!showJsonEditor)}
            className="btn btn-xs btn-ghost flex-center gap-1"
            title="Edit GeoJSON Coordinates"
          >
            <Code size={12} />
            <span>{showJsonEditor ? 'Hide Editor' : 'GeoJSON Editor'}</span>
          </button>
        </div>
      </div>

      {/* Optional GeoJSON Raw Editor */}
      {showJsonEditor && (
        <div className="geojson-editor-box p-3 border-b border-subtle bg-slate">
          <label className="form-label mono text-xs mb-1">
            Raw GeoJSON Polygon Definition (EPSG:4326):
          </label>
          <textarea
            className="form-textarea mono text-xs mb-2"
            rows={5}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
          />
          <div className="flex-end gap-2">
            <button
              type="button"
              onClick={() => setShowJsonEditor(false)}
              className="btn btn-xs btn-secondary"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleApplyJson}
              className="btn btn-xs btn-primary"
            >
              Apply Coordinates
            </button>
          </div>
        </div>
      )}

      {/* Leaflet Map Canvas */}
      <div className="map-viewport-wrapper">
        <div ref={mapContainerRef} className="leaflet-map-canvas" />
        <div className="map-overlay-attribution">
          <Layers size={12} />
          <span>EPSG:4326 · WGS84</span>
        </div>
      </div>

      {/* Real-Time Backend Validation Report */}
      <div className="validation-report-panel p-3">
        {isValidating ? (
          <div className="flex-center gap-2 text-muted text-xs mono py-1">
            <Sparkles size={14} className="spin text-forest" />
            <span>Validating geometry against PostGIS constraints...</span>
          </div>
        ) : validationError ? (
          <div className="validation-status-box status-invalid flex-start gap-2">
            <AlertTriangle size={18} className="text-red flex-shrink-0 mt-0.5" />
            <div className="text-xs">
              <div className="font-semibold text-red">AOI Validation Failed</div>
              <div className="text-muted mt-0.5">{validationError}</div>
              <div className="text-muted-darker mt-1 font-mono">
                Constraint: Surface area must be between 0.10 km² and 100.00 km², max 500 vertices.
              </div>
            </div>
          </div>
        ) : validationResult ? (
          <div className="validation-status-box status-valid">
            <div className="flex-between mb-2">
              <div className="flex-center gap-1.5">
                <CheckCircle size={15} className="text-forest" />
                <span className="font-semibold text-forest text-xs">
                  Valid AOI Geometry (PostGIS Verified)
                </span>
              </div>
              <span className="badge badge-success mono text-xs">
                {validationResult.geometry_type}
              </span>
            </div>

            {/* Spatial Metrics Grid */}
            <div className="grid grid-cols-4 gap-2 text-center text-xs mono">
              <div className="metric-cell">
                <div className="metric-label">Area (km²)</div>
                <div className="metric-val text-forest">
                  {validationResult.area_km2.toFixed(4)}
                </div>
              </div>
              <div className="metric-cell">
                <div className="metric-label">Area (ha)</div>
                <div className="metric-val">
                  {validationResult.area_hectares.toFixed(2)}
                </div>
              </div>
              <div className="metric-cell">
                <div className="metric-label">Vertices</div>
                <div className="metric-val">{validationResult.vertex_count} / 500</div>
              </div>
              <div className="metric-cell">
                <div className="metric-label">Centroid [E, N]</div>
                <div className="metric-val text-muted text-2xs truncate" title={`[${validationResult.centroid.join(', ')}]`}>
                  {validationResult.centroid[0].toFixed(3)}°, {validationResult.centroid[1].toFixed(3)}°
                </div>
              </div>
            </div>

            <div className="bbox-row mono text-2xs text-muted mt-2 pt-2 border-t border-subtle flex-between">
              <span>BBox [W, S, E, N]:</span>
              <span>
                [{validationResult.bbox.map((v) => v.toFixed(3)).join(', ')}]
              </span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
