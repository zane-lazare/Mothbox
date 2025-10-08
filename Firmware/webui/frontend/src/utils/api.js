import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
})

// System APIs
export const getSystemStatus = () => api.get('/system/status')
export const getPowerStatus = () => api.get('/system/power')

// Camera APIs
export const capturePhoto = () => api.post('/camera/capture')
export const getCameraSettings = () => api.get('/camera/settings')
export const updateCameraSettings = (settings) => api.post('/camera/settings', settings)

// Gallery APIs
export const getPhotos = () => api.get('/gallery/photos')
export const getPhotoUrl = (path) => `${API_BASE_URL}/gallery/photo/${path}`
export const getThumbnailUrl = (path) => `${API_BASE_URL}/gallery/thumbnail/${path}`

// Config APIs
export const getControls = () => api.get('/config/controls')
export const updateControls = (controls) => api.post('/config/controls', controls)
export const getScheduleSettings = () => api.get('/config/schedule')
export const updateScheduleSettings = (settings) => api.post('/config/schedule', settings)

// GPIO APIs
export const getGpioStatus = () => api.get('/gpio/status')
export const controlGpio = (relay, state) => api.post('/gpio/control', { relay, state })
export const triggerFlash = () => api.post('/gpio/flash')

// Scheduler APIs
export const getCronJobs = () => api.get('/scheduler/jobs')
export const addCronJob = (job) => api.post('/scheduler/job', job)
export const deleteCronJob = (command) => api.delete('/scheduler/job', { data: { command } })
export const getSchedulerStatus = () => api.get('/scheduler/status')
