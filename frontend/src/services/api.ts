/**
 * DharaScope REST API Client.
 * Handles Bearer token injection, standardized error envelopes, and secure binary streaming.
 */

import type {
  AOICreateRequest,
  AOIListResponse,
  AOIResponse,
  AOIUpdateRequest,
  AOIValidateRequest,
  AOIValidateResponse,
  AnalysisCreateRequest,
  AnalysisListResponse,
  AnalysisResponse,
  ArtifactListResponse,
  HealthResponse,
  UserProfileResponse,
  UserProfileUpdateRequest,
  WaterMetricsResponse,
  APIErrorResponse,
} from '../types/api';

const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
export const API_BASE_URL = RAW_API_BASE.replace(/\/+$/, '');

export class APIError extends Error {
  status_code: number;
  errorType: string;
  detail: string;

  constructor(status_code: number, errorType: string, detail: string) {
    super(detail || errorType);
    this.name = 'APIError';
    this.status_code = status_code;
    this.errorType = errorType;
    this.detail = detail;
  }
}

// In-memory + localStorage token persistence
let inMemoryToken: string | null = localStorage.getItem('dharascope_token');

export function getAuthToken(): string | null {
  return inMemoryToken || localStorage.getItem('dharascope_token');
}

export function setAuthToken(token: string | null): void {
  inMemoryToken = token;
  if (token) {
    localStorage.setItem('dharascope_token', token);
  } else {
    localStorage.removeItem('dharascope_token');
  }
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers(options.headers || {});

  const token = getAuthToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: Partial<APIErrorResponse> = {};
    try {
      errorData = await response.json();
    } catch {
      // response body was not JSON
    }

    const status_code = response.status;
    const errorType = errorData.error || (status_code === 401 ? 'Unauthorized' : status_code === 403 ? 'Forbidden' : 'HTTPError');
    const detail = errorData.detail || response.statusText || `Request failed with status ${status_code}`;

    throw new APIError(status_code, errorType, detail);
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  return response.json() as Promise<T>;
}

/**
 * Downloads a file from an authenticated endpoint (e.g. PDF/CSV report or artifact).
 */
export async function downloadFile(endpoint: string, fallbackFilename: string): Promise<void> {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers();
  const token = getAuthToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorJson = await response.json();
      detail = errorJson.detail || detail;
    } catch {
      // ignore non-json
    }
    throw new APIError(response.status, 'DownloadError', `Failed to download file: ${detail}`);
  }

  // Extract filename from Content-Disposition if present
  let filename = fallbackFilename;
  const disposition = response.headers.get('content-disposition');
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (match && match[1]) {
      filename = match[1].replace(/['"]/g, '');
    }
  }

  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(objectUrl);
}

// ============================================================================
// API Endpoints Methods
// ============================================================================

export const api = {
  // System Health
  async getHealth(): Promise<HealthResponse> {
    // Health is accessible at /api/v1/health or /health
    return apiFetch<HealthResponse>('/health');
  },

  // Auth & Profile
  async getCurrentUser(): Promise<UserProfileResponse> {
    return apiFetch<UserProfileResponse>('/auth/me');
  },

  async updateProfile(data: UserProfileUpdateRequest): Promise<UserProfileResponse> {
    return apiFetch<UserProfileResponse>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  // Area of Interest (AOI)
  async validateAOI(data: AOIValidateRequest): Promise<AOIValidateResponse> {
    return apiFetch<AOIValidateResponse>('/aois/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createAOI(data: AOICreateRequest): Promise<AOIResponse> {
    return apiFetch<AOIResponse>('/aois', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async listAOIs(params: { limit?: number; offset?: number; public_only?: boolean } = {}): Promise<AOIListResponse> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    if (params.public_only !== undefined) query.set('public_only', String(params.public_only));
    const qs = query.toString();
    return apiFetch<AOIListResponse>(`/aois${qs ? `?${qs}` : ''}`);
  },

  async getAOI(aoiId: string): Promise<AOIResponse> {
    return apiFetch<AOIResponse>(`/aois/${aoiId}`);
  },

  async updateAOI(aoiId: string, data: AOIUpdateRequest): Promise<AOIResponse> {
    return apiFetch<AOIResponse>(`/aois/${aoiId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteAOI(aoiId: string): Promise<void> {
    return apiFetch<void>(`/aois/${aoiId}`, {
      method: 'DELETE',
    });
  },

  // Satellite Analyses
  async createAnalysis(data: AnalysisCreateRequest, sync = false): Promise<AnalysisResponse> {
    return apiFetch<AnalysisResponse>(`/analyses${sync ? '?sync=true' : ''}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async listAnalyses(params: { limit?: number; offset?: number } = {}): Promise<AnalysisListResponse> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch<AnalysisListResponse>(`/analyses${qs ? `?${qs}` : ''}`);
  },

  async getAnalysis(analysisId: string): Promise<AnalysisResponse> {
    return apiFetch<AnalysisResponse>(`/analyses/${analysisId}`);
  },

  async deleteAnalysis(analysisId: string): Promise<void> {
    return apiFetch<void>(`/analyses/${analysisId}`, {
      method: 'DELETE',
    });
  },

  async getAnalysisMetrics(analysisId: string): Promise<WaterMetricsResponse> {
    return apiFetch<WaterMetricsResponse>(`/analyses/${analysisId}/metrics`);
  },

  async getAnalysisArtifacts(analysisId: string): Promise<ArtifactListResponse> {
    return apiFetch<ArtifactListResponse>(`/analyses/${analysisId}/artifacts`);
  },

  // Report Downloads
  async downloadReport(analysisId: string, type: 'pdf' | 'csv'): Promise<void> {
    const endpoint = `/analyses/${analysisId}/reports/${type}`;
    const filename = `dharascope_analysis_${analysisId.slice(0, 8)}.${type}`;
    return downloadFile(endpoint, filename);
  },

  // Artifact Download
  getArtifactDownloadUrl(artifactId: string): string {
    return `${API_BASE_URL}/artifacts/${artifactId}/download`;
  },

  async downloadArtifact(artifactId: string, filename: string): Promise<void> {
    return downloadFile(`/artifacts/${artifactId}/download`, filename);
  },
};
