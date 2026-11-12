import type { GeoJSONPolygon } from '../types/api';

/**
 * Canonical Lucknow Gomti River urban reach baseline polygon.
 * Coordinates: [80.90, 26.84] to [80.92, 26.86] in WGS84 (EPSG:4326).
 * Area: ~4.40 km² / 440.48 ha (PostGIS verified).
 */
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
