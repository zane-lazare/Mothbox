/**
 * Deployment Metadata API functions for Issue #125, Subtask 3
 *
 * Provides API integration for deployment metadata CRUD operations:
 * - List all deployments
 * - Get single deployment by directory
 * - Create new deployment
 * - Update existing deployment
 * - Delete deployment
 *
 * All functions follow the pattern from utils/api.js:
 * - Use the global `api` axios instance for CSRF handling
 * - Return axios response objects (access data via .data)
 * - Let axios throw errors for React Query to handle
 */

import { api } from './api'

/**
 * List all deployments
 *
 * @returns {Promise<Object>} Axios response with deployments list
 *
 * Response: {
 *   deployments: [
 *     { directory: "/photos/deployment1", name: "Oak Ridge Survey" },
 *     ...
 *   ],
 *   total: 10
 * }
 */
export const listDeployments = () => api.get('/deployment/list')

/**
 * Get deployment metadata by directory path
 *
 * @param {string} directory - Directory path (e.g., "/photos/deployment1")
 * @returns {Promise<Object>} Axios response with deployment metadata
 *
 * Response: {
 *   deployment_name: "Oak Ridge Survey",
 *   location_name: "Oak Ridge, TN",
 *   latitude: 35.9606,
 *   longitude: -83.9207,
 *   altitude: 350.5,
 *   start_date: "2024-06-01",
 *   end_date: "2024-08-31",
 *   environmental: { habitat: "deciduous forest" },
 *   mothbox_id: "mothbox-001",
 *   firmware_version: "5.2.1",
 *   custom: { project_code: "ORNL-2024-001" }
 * }
 */
export const getDeployment = (directory) => {
  // Encode directory path for URL
  const encodedPath = encodeURIComponent(directory)
  return api.get(`/deployment/metadata/${encodedPath}`)
}

/**
 * Create new deployment metadata
 *
 * @param {string} directory - Directory path
 * @param {Object} data - Deployment metadata
 * @param {string} data.deployment_name - Deployment name (required, max 200 chars)
 * @param {string} [data.location_name] - Location name (max 500 chars)
 * @param {number} [data.latitude] - Latitude (-90 to 90)
 * @param {number} [data.longitude] - Longitude (-180 to 180)
 * @param {number} [data.altitude] - Altitude in meters
 * @param {string} [data.start_date] - Start date (YYYY-MM-DD)
 * @param {string} [data.end_date] - End date (YYYY-MM-DD)
 * @param {Object} [data.environmental] - Environmental conditions (arbitrary key-value)
 * @param {string} [data.mothbox_id] - Mothbox ID
 * @param {string} [data.firmware_version] - Firmware version
 * @param {Object} [data.custom] - Custom fields (max 50 keys, max depth 5)
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: {
 *   message: "Deployment metadata created",
 *   directory: "/photos/deployment1"
 * }
 */
export const createDeployment = (directory, data) => {
  const encodedPath = encodeURIComponent(directory)
  return api.put(`/deployment/metadata/${encodedPath}`, data)
}

/**
 * Update existing deployment metadata (partial update)
 *
 * @param {string} directory - Directory path
 * @param {Object} data - Partial deployment metadata (only fields to update)
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: {
 *   message: "Deployment metadata updated",
 *   directory: "/photos/deployment1"
 * }
 */
export const updateDeployment = (directory, data) => {
  const encodedPath = encodeURIComponent(directory)
  return api.patch(`/deployment/metadata/${encodedPath}`, data)
}

/**
 * Delete deployment metadata
 *
 * @param {string} directory - Directory path
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: {
 *   message: "Deployment metadata deleted",
 *   directory: "/photos/deployment1"
 * }
 */
export const deleteDeployment = (directory) => {
  const encodedPath = encodeURIComponent(directory)
  return api.delete(`/deployment/metadata/${encodedPath}`)
}
