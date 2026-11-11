/**
 * DharaScope TypeScript API Types & Service Contracts.
 * Strictly aligned with FastAPI Pydantic schemas (src/api/schemas/).
 */

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  app_name: string;
  version: string;
  environment: string;
  database: string;
  timestamp: string;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  full_name: string | null;
  role: 'user' | 'admin';
  quota_monthly_runs: number;
  created_at: string;
  updated_at: string;
}

export interface UserProfileUpdateRequest {
  full_name?: string;
}

export interface AdminUserUpdateRequest {
  role?: 'user' | 'admin';
  quota_monthly_runs?: number;
  full_name?: string;
}

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface GeoJSONMultiPolygon {
  type: 'MultiPolygon';
  coordinates: number[][][][];
}

export type GeoJSONGeometry = GeoJSONPolygon | GeoJSONMultiPolygon;

export interface AOIValidateRequest {
  geometry: GeoJSONGeometry | number[];
  min_area_km2?: number;
  max_area_km2?: number;
  max_vertices?: number;
}

export interface AOIValidateResponse {
  valid: boolean;
  geometry: GeoJSONGeometry;
  geometry_type: string;
  bbox: [number, number, number, number];
  centroid: [number, number];
  area_m2: number;
  area_km2: number;
  area_hectares: number;
  vertex_count: number;
}

export interface AOICreateRequest {
  name: string;
  description?: string;
  geometry: GeoJSONGeometry | number[];
  is_public?: boolean;
}

export interface AOIUpdateRequest {
  name?: string;
  description?: string;
  is_public?: boolean;
}

export interface AOIResponse {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  geometry: GeoJSONGeometry;
  area_km2: number;
  area_hectares: number;
  bbox: [number, number, number, number];
  centroid: [number, number];
  vertex_count: number;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface AOIListResponse {
  items: AOIResponse[];
  total: number;
}

export interface AnalysisCreateRequest {
  aoi_id?: string;
  aoi_geometry?: GeoJSONGeometry | number[];
  aoi_name?: string;
  ndwi_threshold?: number;
  max_cloud_cover?: number;
  datetime_range?: string;
  data_source?: 'auto' | 'cdse' | 'public' | 'synthetic';
}

export interface AnalysisResponse {
  id: string;
  user_id: string;
  aoi_id: string | null;
  status: 'QUEUED' | 'PROCESSING' | 'SUCCESS' | 'FAILED';
  data_provider: string;
  is_real_data: boolean;
  t1_scene_id: string;
  t1_date: string;
  t1_cloud_cover: number | null;
  t2_scene_id: string;
  t2_date: string;
  t2_cloud_cover: number | null;
  ndwi_threshold: number;
  error_message: string | null;
  execution_duration_sec: number | null;
  execution_timestamp: string;
  created_at: string;
  updated_at: string;
}

export interface AnalysisListResponse {
  items: AnalysisResponse[];
  total: number;
}

export interface WaterMetricsResponse {
  id: string;
  analysis_run_id: string;
  common_valid_pixels: number;
  common_valid_area_ha: number;
  pixel_size_m2: number;
  t1_water_pixels: number;
  t1_water_area_m2: number;
  t1_water_area_ha: number;
  t2_water_pixels: number;
  t2_water_area_m2: number;
  t2_water_area_ha: number;
  absolute_change_m2: number;
  absolute_change_ha: number;
  percentage_change: number | null;
  persistent_water_m2: number;
  persistent_water_ha: number;
  apparent_loss_m2: number;
  apparent_loss_ha: number;
  apparent_gain_m2: number;
  apparent_gain_ha: number;
  limitation_statement: string;
  created_at: string;
}

export type ArtifactType =
  | 'MAP_PNG'
  | 'PANEL_PNG'
  | 'REPORT_PDF'
  | 'REPORT_CSV'
  | 'THUMBNAIL_JPG'
  | 'RASTER_TIFF';

export interface ArtifactResponse {
  id: string;
  analysis_run_id: string;
  artifact_type: ArtifactType;
  storage_bucket: 'maps' | 'reports' | 'rasters';
  file_name: string;
  file_size_bytes: number | null;
  mime_type: string;
  download_url: string;
  created_at: string;
}

export interface ArtifactListResponse {
  items: ArtifactResponse[];
  total: number;
}

export interface APIErrorResponse {
  error: string;
  detail: string;
  status_code: number;
}
