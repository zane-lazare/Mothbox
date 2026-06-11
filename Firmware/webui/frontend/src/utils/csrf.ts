/**
 * CSRF Token Management
 * Handles fetching and caching CSRF tokens for API requests
 */

interface CsrfResponse {
  csrf_token: string
}

/**
 * Get the API base URL from environment or construct from window location
 */
function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  const protocol = window.location.protocol
  const host = window.location.hostname
  const port = window.location.port
  return `${protocol}//${host}${port ? ':' + port : ''}/api`
}

const API_URL = getApiBaseUrl()

// In-memory token storage (not localStorage to prevent XSS attacks)
let csrfToken: string | null = null

/**
 * Fetch CSRF token from the backend
 * @returns CSRF token
 */
export async function fetchCsrfToken(): Promise<string> {
  try {
    const response = await fetch(`${API_URL}/csrf-token`, {
      credentials: 'include', // Include cookies for session
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch CSRF token: ${response.statusText}`)
    }

    const data = (await response.json()) as CsrfResponse
    csrfToken = data.csrf_token
    return csrfToken
  } catch (error) {
    console.error('Error fetching CSRF token:', error)
    throw error
  }
}

/**
 * Get the current CSRF token, fetching if not already cached
 * @returns CSRF token
 */
export async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    await fetchCsrfToken()
  }
  return csrfToken as string
}

/**
 * Clear the cached CSRF token (useful after CSRF errors)
 */
export function clearCsrfToken(): void {
  csrfToken = null
}

/**
 * Initialize CSRF token on app load
 */
export async function initializeCsrf(): Promise<void> {
  try {
    await fetchCsrfToken()
  } catch (error) {
    console.error('Failed to initialize CSRF token:', error)
  }
}
