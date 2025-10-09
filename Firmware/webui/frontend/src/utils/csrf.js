/**
 * CSRF Token Management
 * Handles fetching and caching CSRF tokens for API requests
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

// In-memory token storage (not localStorage to prevent XSS attacks)
let csrfToken = null

/**
 * Fetch CSRF token from the backend
 * @returns {Promise<string>} CSRF token
 */
export async function fetchCsrfToken() {
  try {
    const response = await fetch(`${API_URL}/csrf-token`, {
      credentials: 'include', // Include cookies for session
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch CSRF token: ${response.statusText}`)
    }

    const data = await response.json()
    csrfToken = data.csrf_token
    return csrfToken
  } catch (error) {
    console.error('Error fetching CSRF token:', error)
    throw error
  }
}

/**
 * Get the current CSRF token, fetching if not already cached
 * @returns {Promise<string>} CSRF token
 */
export async function getCsrfToken() {
  if (!csrfToken) {
    await fetchCsrfToken()
  }
  return csrfToken
}

/**
 * Clear the cached CSRF token (useful after CSRF errors)
 */
export function clearCsrfToken() {
  csrfToken = null
}

/**
 * Initialize CSRF token on app load
 */
export async function initializeCsrf() {
  try {
    await fetchCsrfToken()
    console.log('CSRF token initialized')
  } catch (error) {
    console.error('Failed to initialize CSRF token:', error)
  }
}
