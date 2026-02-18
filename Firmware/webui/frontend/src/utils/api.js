import axios from 'axios'
import { getCsrfToken, clearCsrfToken, fetchCsrfToken } from './csrf'
import { GALLERY_CONFIG } from '../constants/config'

// Use current window location for API calls, or fall back to env variable
// This ensures the UI works whether accessed via localhost, IP, or hostname
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  // Use current host and port
  const protocol = window.location.protocol
  const host = window.location.hostname
  const port = window.location.port
  return `${protocol}//${host}${port ? ':' + port : ''}/api`
}

const API_BASE_URL = getApiBaseUrl()

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Include cookies for session/CSRF
})

// Request interceptor to add CSRF token to state-changing requests
api.interceptors.request.use(
  async (config) => {
    // Add CSRF token to POST, PUT, DELETE, PATCH requests
    if (['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
      try {
        const token = await getCsrfToken()
        config.headers['X-CSRFToken'] = token
      } catch (error) {
        console.error('Failed to get CSRF token:', error)
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle CSRF errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If CSRF validation failed and we haven't retried yet
    if (error.response?.status === 400 &&
        error.response?.data?.error === 'CSRF validation failed' &&
        !originalRequest._retry) {

      originalRequest._retry = true

      // Clear cached token and fetch a new one
      clearCsrfToken()
      try {
        const newToken = await fetchCsrfToken()
        originalRequest.headers['X-CSRFToken'] = newToken
        return api(originalRequest)
      } catch (csrfError) {
        console.error('Failed to refresh CSRF token:', csrfError)
      }
    }

    return Promise.reject(error)
  }
)

// System APIs
export const getSystemStatus = () => api.get('/system/status')
export const getPowerStatus = () => api.get('/system/power')
export const getSystemInfo = () => api.get('/system/info')
export const getDiagnosticInfo = () => api.get('/system/diagnostic')

// Camera APIs
export const capturePhoto = () => api.post('/camera/capture')
export const getCameraSettings = () => api.get('/camera/settings')
export const updateCameraSettings = (settings) => api.post('/camera/settings', settings)
export const triggerAutofocus = () => api.post('/camera/autofocus')
export const autoCalibrate = (data) => api.post('/camera/calibrate', data)
export const freezeSettings = () => api.post('/camera/freeze-settings')
export const testCaptureLiveview = () => api.post('/camera/test-capture-liveview')
export const testCapturePhoto = () => api.post('/camera/test-capture-photo')
export const instantCapture = () => api.post('/camera/instant-capture')

// Gallery APIs
export const getPhotos = () => api.get('/gallery/photos')
export const getPhotosPaginated = (params) => api.get('/gallery/photos/paginated', { params })
export const getPhotoUrl = (path) => `${API_BASE_URL}/gallery/photo/${path}`
export const getThumbnailUrl = (path, size = GALLERY_CONFIG.THUMBNAIL.SIZE) => `${API_BASE_URL}/gallery/thumbnail/${path}?size=${size}`
export const getPhotoLocations = (params = {}) => api.get('/gallery/locations', { params }).then(res => res.data)
export const getClusteredLocations = (params = {}) => api.get('/gallery/locations/clustered', { params }).then(res => res.data)

// Series APIs (Photo Series - HDR, Focus Bracket)
export const getSeries = (params) => api.get('/gallery/series', { params })
export const getSeriesById = (seriesId) => api.get(`/gallery/series/${encodeURIComponent(seriesId)}`)

// Config APIs
export const getControls = () => api.get('/config/controls')
export const updateControls = (controls) => api.post('/config/controls', controls)
export const getScheduleSettings = () => api.get('/config/schedule')
export const updateScheduleSettings = (settings) => api.post('/config/schedule', settings)
export const getWebuiSettings = () => api.get('/config/webui')
export const updateWebuiSettings = (settings) => api.post('/config/webui', settings)
export const copySettings = (data) => api.post('/config/copy-settings', data)

// GPIO APIs
export const getGpioStatus = () => api.get('/gpio/status')
export const getGpioHealth = () => api.get('/gpio/health')
export const controlGpio = (relay, state) => api.post('/gpio/control', { relay, state })
export const triggerFlash = () => api.post('/gpio/flash')

// Scheduler APIs
export const getCronJobs = () => api.get('/scheduler/jobs')
export const addCronJob = (job) => api.post('/scheduler/job', job)
export const deleteCronJob = (command) => api.delete('/scheduler/job', { data: { command } })
export const getSchedulerStatus = () => api.get('/scheduler/status')

// Preset APIs
export const getPresets = () => api.get('/presets')
export const getPreset = (name) => api.get(`/presets/${name}`)
export const createPreset = (data) => api.post('/presets', data)
export const applyPreset = (name, applyTo) => api.post(`/presets/${name}/apply`, { apply_to: applyTo })
export const deletePreset = (name) => api.delete(`/presets/${name}`)

// User Preferences APIs
export const getPreferences = () => api.get('/preferences')
export const setPreference = (key, value) => api.post('/preferences', { key, value })

// GPS APIs
export const getGpsStatus = () => api.get('/gps/status')
export const syncGps = () => api.post('/gps/sync')
export const getGpsConfig = () => api.get('/gps/config')
export const updateGpsConfig = (config) => api.put('/gps/config', config)

// GPS EXIF Tagger APIs
export const getGpsExifStatus = () => api.get('/gps-exif/status')
export const getGpsExifConfig = () => api.get('/gps-exif/config')
export const updateGpsExifConfig = (config) => api.put('/gps-exif/config', config)
export const tagSinglePhoto = (data) => api.post('/gps-exif/tag-photo', data)
export const batchTagPhotos = (data) => api.post('/gps-exif/batch-tag', data)

// Sidecar Metadata APIs
export const getAllTags = (params = {}) => api.get('/sidecar/tags', { params })
export const getAllSpecies = (params = {}) => api.get('/sidecar/species', { params })
export const getPhotoSidecarMetadata = (filename) => api.get(`/sidecar/photos/${encodeURIComponent(filename)}`)
export const updatePhotoSidecarMetadata = (filename, updates) => api.patch(`/sidecar/photos/${encodeURIComponent(filename)}`, updates)
export const bulkUpdateSidecarMetadata = (filenames, updates) => api.post('/sidecar/bulk', { filenames, updates })
export const getBulkSidecarMetadata = (filenames, options = {}) => api.get('/sidecar/bulk', {
  params: { filenames: filenames.join(',') },
  timeout: options.timeout || 30000
})
export const getTagAutocomplete = (query, limit = 10) => api.get('/metadata/tags/autocomplete', { params: { q: query, limit } })

// Search APIs
/**
 * Search photos by query
 * @param {string} query - Search query
 * @param {Object} options - Search options
 * @param {number} options.limit - Results per page (default: 20)
 * @param {number} options.offset - Results offset (default: 0)
 * @returns {Promise<Object>} Search results
 */
export async function searchPhotos(query, { limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams({
    q: query,
    limit: limit.toString(),
    offset: offset.toString()
  })

  const response = await fetch(`/api/photos/search?${params}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Search failed' }))
    throw new Error(error.message || 'Search failed')
  }

  return response.json()
}
