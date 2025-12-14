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
export const createExportJob = (data) => api.post('/export/jobs', data)

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
export const listExportJobs = (params = {}) => api.get('/export/jobs', { params })

/**
 * Get status and details of a specific export job
 *
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} Axios response with job details
 *
 * Response: { job_id, status, format, progress: { current, total, percent, phase }, ... }
 */
export const getExportJob = (jobId) => api.get(`/export/jobs/${jobId}`)

/**
 * Cancel a pending or running export job
 *
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: { success: true, message: "Job cancelled" }
 */
export const cancelExportJob = (jobId) => api.post(`/export/jobs/${jobId}/cancel`)

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
export const deleteExportJob = (jobId) => api.delete(`/export/jobs/${jobId}`)

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
export const getExportJobDownloadUrl = (jobId) => `/api/export/jobs/${jobId}/download`

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
export const listExportPresets = (formatFilter) => {
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
export const getExportPreset = (name) => api.get(`/export/presets/${name}`)

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
export const createExportPreset = (data) => api.post('/export/presets', data)

/**
 * Delete user export preset (built-in presets are protected)
 *
 * @param {string} name - Preset name to delete
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: { success: true, message: "Preset deleted" }
 */
export const deleteExportPreset = (name) => api.delete(`/export/presets/${name}`)
