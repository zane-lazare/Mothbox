import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MapPage from '../MapPage'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(),
  getClusteredLocations: vi.fn(),
}))

// Mock react-leaflet (Leaflet has issues in happy-dom/jsdom)
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children, ...props }) => (
    <div data-testid="map-container" {...props}>
      {children}
    </div>
  ),
  TileLayer: (props) => <div data-testid="tile-layer" {...props} />,
  Marker: ({ children, ...props }) => (
    <div data-testid="marker" {...props}>
      {children}
    </div>
  ),
  Popup: ({ children, ...props }) => (
    <div data-testid="popup" {...props}>
      {children}
    </div>
  ),
  useMap: () => ({
    fitBounds: vi.fn(),
    getBounds: vi.fn(),
    setView: vi.fn(),
    getZoom: vi.fn(() => 13),
    flyTo: vi.fn(),
  }),
}))

// Mock react-leaflet-cluster
vi.mock('react-leaflet-cluster', () => ({
  default: ({ children, ...props }) => (
    <div data-testid="marker-cluster-group" {...props}>
      {children}
    </div>
  ),
}))

// Mock leaflet
vi.mock('leaflet', () => ({
  default: {
    Icon: class MockIcon {
      constructor(options) {
        this.options = options
      }
    },
    divIcon: vi.fn((options) => ({
      options,
      _type: 'divIcon',
      _getIconUrl: vi.fn(),
    })),
  },
}))

// Mock MapView component (already tested separately)
// vi.mock factories are hoisted and cannot reference top-level imports.
// Use a plain function component; the ref prop is simply ignored for smoke tests.
vi.mock('../../components/MapView', () => ({
  default: ({ isLoading, locations, clusters, className }) => (
    <div data-testid="map-view" className={className}>
      {isLoading ? (
        <div data-testid="map-loading">Loading map...</div>
      ) : (
        <div data-testid="map-content">
          Map with {(locations || []).length} locations and{' '}
          {(clusters || []).length} clusters
        </div>
      )}
    </div>
  ),
}))

// Mock PhotoLightbox component
vi.mock('../../components/PhotoLightbox', () => ({
  default: ({ photo, onClose }) =>
    photo ? (
      <div data-testid="photo-lightbox">
        <span>{photo.filename}</span>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}))

// Mock ErrorBoundary component
vi.mock('../../components/ErrorBoundary', () => ({
  default: ({ children }) => <div data-testid="error-boundary">{children}</div>,
}))

// Mock LightboxErrorFallback component
vi.mock('../../components/LightboxErrorFallback', () => ({
  default: ({ error, onClose }) => (
    <div data-testid="lightbox-error-fallback">Error: {error?.message}</div>
  ),
}))

// Mock useClusteredLocations hook
vi.mock('../../hooks/useClusteredLocations', () => ({
  useClusteredLocations: vi.fn(),
  default: vi.fn(),
}))

// Mock useMapLightboxSync hook
vi.mock('../../hooks/useMapLightboxSync', () => ({
  default: vi.fn(),
}))

// Mock heroicons
vi.mock('@heroicons/react/24/outline', () => ({
  ArrowLeftIcon: (props) => <svg data-testid="arrow-left-icon" {...props} />,
  ExclamationTriangleIcon: (props) => (
    <svg data-testid="exclamation-icon" {...props} />
  ),
  ArrowPathIcon: (props) => <svg data-testid="arrow-path-icon" {...props} />,
}))

// Now import the mocked modules so we can control them
import { useClusteredLocations } from '../../hooks/useClusteredLocations'
import useMapLightboxSync from '../../hooks/useMapLightboxSync'

describe('MapPage', () => {
  let queryClient

  const defaultClusteredLocations = {
    clusters: [],
    unclustered: [],
    metadata: { total_without_gps: 0 },
    isLoading: false,
    isPartialResult: false,
    partialWarning: null,
    settings: { enabled: true, radius: 100 },
    setEnabled: vi.fn(),
    setRadius: vi.fn(),
    refetch: vi.fn(),
  }

  const defaultMapLightboxSync = {
    currentPhoto: null,
    highlightedPhotoPath: null,
    openLightbox: vi.fn(),
    closeLightbox: vi.fn(),
    onMarkerClick: vi.fn(),
    onClusterClick: vi.fn(),
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })

    vi.clearAllMocks()

    // Set default mock responses
    api.getPhotosPaginated.mockResolvedValue({
      data: {
        photos: [],
        pagination: { has_next: false, offset: 0, limit: 200 },
      },
    })

    useClusteredLocations.mockReturnValue(defaultClusteredLocations)
    useMapLightboxSync.mockReturnValue(defaultMapLightboxSync)
  })

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <MapPage />
        </QueryClientProvider>
      </MemoryRouter>
    )
  }

  it('renders without crashing', () => {
    renderComponent()
    expect(screen.getByText('Photo Locations')).toBeInTheDocument()
  })

  it('renders the page heading', () => {
    renderComponent()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Photo Locations'
    )
  })

  it('renders the back to gallery link', () => {
    renderComponent()
    const backLink = screen.getByLabelText('Back to gallery')
    expect(backLink).toBeInTheDocument()
    expect(backLink).toHaveAttribute('href', '/gallery')
  })

  it('renders MapView component', () => {
    renderComponent()
    expect(screen.getByTestId('map-view')).toBeInTheDocument()
  })

  it('renders ErrorBoundary wrapper for lightbox', () => {
    renderComponent()
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument()
  })

  it('displays photo count when locations are loaded', () => {
    useClusteredLocations.mockReturnValue({
      ...defaultClusteredLocations,
      unclustered: [
        {
          path: 'photo1.jpg',
          filename: 'photo1.jpg',
          latitude: 37.7749,
          longitude: -122.4194,
          lat: 37.7749,
          lon: -122.4194,
        },
      ],
    })

    renderComponent()

    expect(screen.getByText(/1 photo with GPS coordinates/)).toBeInTheDocument()
  })

  it('displays plural photo count for multiple locations', () => {
    useClusteredLocations.mockReturnValue({
      ...defaultClusteredLocations,
      unclustered: [
        {
          path: 'photo1.jpg',
          filename: 'photo1.jpg',
          latitude: 37.7749,
          longitude: -122.4194,
          lat: 37.7749,
          lon: -122.4194,
        },
        {
          path: 'photo2.jpg',
          filename: 'photo2.jpg',
          latitude: 34.0522,
          longitude: -118.2437,
          lat: 34.0522,
          lon: -118.2437,
        },
      ],
    })

    renderComponent()

    expect(screen.getByText(/2 photos with GPS coordinates/)).toBeInTheDocument()
  })

  it('shows count of photos without GPS when present', () => {
    useClusteredLocations.mockReturnValue({
      ...defaultClusteredLocations,
      unclustered: [
        {
          path: 'photo1.jpg',
          filename: 'photo1.jpg',
          latitude: 37.7749,
          longitude: -122.4194,
          lat: 37.7749,
          lon: -122.4194,
        },
      ],
      metadata: { total_without_gps: 5 },
    })

    renderComponent()

    expect(screen.getByText(/5 photos without GPS/)).toBeInTheDocument()
  })

  it('does not show photo count while loading', () => {
    useClusteredLocations.mockReturnValue({
      ...defaultClusteredLocations,
      isLoading: true,
    })

    renderComponent()

    expect(
      screen.queryByText(/photo.*with GPS coordinates/)
    ).not.toBeInTheDocument()
  })

  it('shows partial results warning when applicable', () => {
    useClusteredLocations.mockReturnValue({
      ...defaultClusteredLocations,
      isPartialResult: true,
      partialWarning: 'Clustering timed out, showing partial results',
    })

    renderComponent()

    expect(
      screen.getByText('Clustering timed out, showing partial results')
    ).toBeInTheDocument()
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('shows retry button when partial results are shown', () => {
    useClusteredLocations.mockReturnValue({
      ...defaultClusteredLocations,
      isPartialResult: true,
      partialWarning: 'Timeout',
    })

    renderComponent()

    expect(
      screen.getByLabelText('Retry loading all locations')
    ).toBeInTheDocument()
  })

  it('does not show partial warning when results are complete', () => {
    renderComponent()

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('does not render lightbox when no photo is selected', () => {
    renderComponent()

    expect(screen.queryByTestId('photo-lightbox')).not.toBeInTheDocument()
  })
})
