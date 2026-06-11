/**
 * Export API functions for Issue #125
 *
 * Provides API integration for export jobs and presets:
 * - Export Jobs: Async export queue with polling support
 * - Export Presets: Reusable export configurations
 *
 * All functions follow the pattern from utils/api.js:
 * - Use the global `api` axios instance for CSRF handling
 * - Return axios response objects (access data via .data)
 * - Let axios throw errors for React Query to handle
 */

import { api } from './api'
import type { AxiosResponse } from 'axios'

// ============================================================================
// Types
// ============================================================================

/**
 * Export formats
 */
export type ExportFormat = 'darwin_core' | 'inaturalist' | 'json' | 'csv'

/**
 * Export job statuses
 */
export type ExportJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'expired'

/**
 * Export filter criteria
 */
export interface ExportFilter {
  date_start?: string
  date_end?: string
  deployment?: string
  tags?: string[]
  series_type?: 'hdr' | 'focus_bracket'
  has_species?: boolean
  photo_paths?: string[]
}

/**
 * Export job progress
 */
export interface ExportJobProgress {
  current: number
  total: number
  percent: number
  phase: string
}

/**
 * Export job creation data
 */
export interface ExportJobCreateData {
  preset?: string
  format?: ExportFormat
  filter?: ExportFilter
  options?: Record<string, unknown>
  ttl_seconds?: number
}

/**
 * Export job response
 */
export interface ExportJob {
  job_id: string
  status: ExportJobStatus
  format: ExportFormat
  created_at: string
  updated_at?: string
  completed_at?: string
  progress?: ExportJobProgress
  error?: string
  result_path?: string
  filter?: ExportFilter
  options?: Record<string, unknown>
}

/**
 * Export jobs list response
 */
export interface ExportJobsListResponse {
  jobs: ExportJob[]
  total: number
  limit: number
  offset: number
}

/**
 * Export jobs list params
 */
export interface ExportJobsListParams {
  status?: ExportJobStatus
  limit?: number
  offset?: number
}

/**
 * Export job operation response
 */
export interface ExportJobOperationResponse {
  success: boolean
  message: string
}

/**
 * Export preset
 */
export interface ExportPreset {
  name: string
  display_name: string
  export_format: ExportFormat
  description?: string
  category: 'built-in' | 'user'
  filter?: ExportFilter
  options?: Record<string, unknown>
}

/**
 * Export presets list response
 */
export interface ExportPresetsListResponse {
  presets: ExportPreset[]
  counts: {
    'built-in': number
    user: number
  }
}

/**
 * Export preset creation data
 */
export interface ExportPresetCreateData {
  name: string
  display_name: string
  export_format: ExportFormat
  description?: string
  filter?: ExportFilter
  options?: Record<string, unknown>
}

/**
 * Export preset operation response
 */
export interface ExportPresetOperationResponse {
  success: boolean
  message: string
  name?: string
}

// ============================================================================
// Export Jobs API (Issue #122)
// ============================================================================

/**
 * Create a new export job
 *
 * @param {Object} data - Job configuration
 * @param {string} [data.preset] - Preset name to use as base configuration
 * @param {string} [data.format] - Export format (darwin_core, inaturalist, json, csv)
 * @param {Object} [data.filter] - Photo selection criteria
 * @param {string} [data.filter.date_start] - Start date (YYYY-MM-DD)
 * @param {string} [data.filter.date_end] - End date (YYYY-MM-DD)
 * @param {string} [data.filter.deployment] - Deployment directory path
 * @param {string[]} [data.filter.tags] - Tags to match (any)
 * @param {string} [data.filter.series_type] - Series type (hdr or focus_bracket)
 * @param {boolean} [data.filter.has_species] - Only photos with species ID
 * @param {string[]} [data.filter.photo_paths] - Explicit photo paths
 * @param {Object} [data.options] - Format-specific options
 * @param {number} [data.ttl_seconds] - Custom TTL in seconds (60-86400)
 * @returns {Promise<Object>} Axios response with job details
 *
 * Response: { job_id, status, format, created_at, ... }
 */
export const createExportJob = (data: ExportJobCreateData): Promise<AxiosResponse<ExportJob>> =>
  api.post('/export/jobs', data)

/**
 * List all export jobs with optional filtering and pagination
 *
 * @param {Object} [params] - Query parameters
 * @param {string} [params.status] - Filter by status (pending, running, completed, failed, cancelled, expired)
 * @param {number} [params.limit=50] - Max results (max: 100)
 * @param {number} [params.offset=0] - Pagination offset
 * @returns {Promise<Object>} Axios response with jobs list
 *
 * Response: { jobs: [...], total, limit, offset }
 */
export const listExportJobs = (params: ExportJobsListParams = {}): Promise<AxiosResponse<ExportJobsListResponse>> =>
  api.get('/export/jobs', { params })

/**
 * Get status and details of a specific export job
 *
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} Axios response with job details
 *
 * Response: { job_id, status, format, progress: { current, total, percent, phase }, ... }
 */
export const getExportJob = (jobId: string): Promise<AxiosResponse<ExportJob>> =>
  api.get(`/export/jobs/${jobId}`)

/**
 * Cancel a pending or running export job
 *
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: { success: true, message: "Job cancelled" }
 */
export const cancelExportJob = (jobId: string): Promise<AxiosResponse<ExportJobOperationResponse>> =>
  api.post(`/export/jobs/${jobId}/cancel`)

/**
 * Delete an export job and its output files
 *
 * Cannot delete running jobs - must cancel first.
 *
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: { success: true, message: "Job deleted" }
 */
export const deleteExportJob = (jobId: string): Promise<AxiosResponse<ExportJobOperationResponse>> =>
  api.delete(`/export/jobs/${jobId}`)

/**
 * Get download URL for completed export job result
 *
 * This is a URL string, not an API call. Use it for direct download links.
 *
 * @param {string} jobId - Job ID
 * @returns {string} Download URL
 *
 * Example: /api/export/jobs/550e8400-e29b-41d4-a716-446655440000/download
 */
export const getExportJobDownloadUrl = (jobId: string): string =>
  `/api/export/jobs/${jobId}/download`

// ============================================================================
// Export Presets API (Issue #123)
// ============================================================================

/**
 * List all available export presets (built-in + user)
 *
 * @param {string} [formatFilter] - Filter by export format (darwin_core, inaturalist, json, csv)
 * @returns {Promise<Object>} Axios response with presets list
 *
 * Response: { presets: [...], counts: { 'built-in': 6, user: 1 } }
 */
export const listExportPresets = (formatFilter?: ExportFormat): Promise<AxiosResponse<ExportPresetsListResponse>> => {
  const params = formatFilter ? { format: formatFilter } : {}
  return api.get('/export/presets', { params })
}

/**
 * Get specific export preset by name
 *
 * @param {string} name - Preset name (without .json extension)
 * @returns {Promise<Object>} Axios response with preset details
 *
 * Response: { name, display_name, export_format, description, category, filter, options }
 */
export const getExportPreset = (name: string): Promise<AxiosResponse<ExportPreset>> =>
  api.get(`/export/presets/${name}`)

/**
 * Create new user export preset
 *
 * @param {Object} data - Preset configuration
 * @param {string} data.name - Preset name (unique)
 * @param {string} data.display_name - Display name
 * @param {string} data.export_format - Export format (darwin_core, inaturalist, json, csv)
 * @param {string} [data.description] - Description
 * @param {Object} [data.filter] - Photo selection criteria
 * @param {Object} [data.options] - Format-specific options
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: { success: true, message: "Preset created", name: "my_preset" }
 */
export const createExportPreset = (data: ExportPresetCreateData): Promise<AxiosResponse<ExportPresetOperationResponse>> =>
  api.post('/export/presets', data)

/**
 * Delete user export preset (built-in presets are protected)
 *
 * @param {string} name - Preset name to delete
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: { success: true, message: "Preset deleted" }
 */
export const deleteExportPreset = (name: string): Promise<AxiosResponse<ExportPresetOperationResponse>> =>
  api.delete(`/export/presets/${name}`)
