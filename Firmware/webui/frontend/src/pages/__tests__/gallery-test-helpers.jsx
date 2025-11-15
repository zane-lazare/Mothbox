import { vi } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Gallery from '../Gallery'
import { GALLERY_CONFIG } from '../../constants/config'

// Mock navigation function (shared across all Gallery tests)
export const mockNavigate = vi.fn()

// Mock react-router-dom globally for all Gallery tests
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

/**
 * Creates mock photo data for testing
 * @param {number} start - Starting index for photo numbering
 * @param {number} count - Number of photos to generate
 * @returns {Array} Array of mock photo objects
 */
export const createMockPhotos = (start, count) => {
  return Array.from({ length: count }, (_, i) => ({
    path: `photo_${start + i}.jpg`,
    filename: `photo_${start + i}.jpg`,
    date: new Date(2023, 10, start + i).toISOString(),
    size: 1024 * 1024 * (start + i),
  }))
}

/**
 * Creates a QueryClient configured for testing
 * @returns {QueryClient} QueryClient instance with retry disabled
 */
export const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

/**
 * Sets up IntersectionObserver mock for testing
 * Returns mock functions and callback reference
 * @returns {Object} Mock functions and observer callback
 */
export const setupIntersectionObserver = () => {
  const observeMock = vi.fn()
  const unobserveMock = vi.fn()
  const disconnectMock = vi.fn()
  let observerCallback = null

  const IntersectionObserverMock = vi.fn((callback) => {
    observerCallback = callback
    return {
      observe: observeMock,
      unobserve: unobserveMock,
      disconnect: disconnectMock,
    }
  })

  globalThis.IntersectionObserver = IntersectionObserverMock

  return {
    observeMock,
    unobserveMock,
    disconnectMock,
    IntersectionObserverMock,
    getObserverCallback: () => observerCallback,
  }
}

/**
 * Renders Gallery component wrapped in QueryClientProvider and BrowserRouter
 * @param {QueryClient} queryClient - The QueryClient instance to use
 * @param {Object} props - Optional props to pass to Gallery component
 * @returns {Object} Render result from @testing-library/react
 */
export const renderGallery = (queryClient, props = {}) => {
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <Gallery {...props} />
      </QueryClientProvider>
    </BrowserRouter>
  )
}

/**
 * Creates a standard pagination response structure
 * @param {Array} photos - Array of photo objects
 * @param {Object} paginationOptions - Pagination metadata options
 * @returns {Object} Mock API response object
 */
export const createPaginationResponse = (photos, paginationOptions = {}) => {
  const {
    limit = GALLERY_CONFIG.PAGE_SIZE,
    offset = 0,
    total = photos.length,
    has_next = false,
    has_previous = false,
  } = paginationOptions

  return {
    data: {
      photos,
      pagination: {
        limit,
        offset,
        total,
        has_next,
        has_previous,
      },
    },
  }
}
