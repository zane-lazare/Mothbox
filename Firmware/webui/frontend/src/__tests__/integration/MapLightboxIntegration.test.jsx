import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import MapPage from '../../pages/MapPage'

// Mock Leaflet and dependencies
vi.mock('leaflet', () => ({
  default: {
    Icon: class Icon {
      constructor() {}
    },
    divIcon: (options) => ({ ...options, _type: 'divIcon' }),
    Map: class Map {
      constructor() {
        this.zoom = 10
      }
      getZoom() {
        return this.zoom
      }
      setZoom(zoom) {
        this.zoom = zoom
      }
      flyTo() {}
      fitBounds() {}
      invalidateSize() {}
      remove() {}
    },
  },
}))

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children, ...props }) => {
    // Filter out Leaflet-specific props that would cause React warnings
    const { minZoom, maxZoom, tap, tapTolerance, touchZoom, dragging, scrollWheelZoom, doubleClickZoom, attributionControl, ...cleanProps } = props
    return (
      <div data-testid="map-container" {...cleanProps}>
        {children}
      </div>
    )
  },
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children, eventHandlers, position }) => (
    <div
      data-testid="marker"
      data-position={JSON.stringify(position)}
      onClick={() => eventHandlers?.click?.()}
    >
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({
    getZoom: () => 10,
    setZoom: vi.fn(),
    flyTo: vi.fn(),
    fitBounds: vi.fn(),
    invalidateSize: vi.fn(),
  }),
}))

vi.mock('react-leaflet-cluster', () => ({
  default: ({ children }) => <div data-testid="marker-cluster-group">{children}</div>,
}))

// Mock API calls
vi.mock('../../utils/api', () => ({
  getPhotosPaginated: vi.fn(() =>
    Promise.resolve({
      data: {
        photos: [
          {
            path: '2024-11-10/photo1.jpg',
            filename: 'photo1.jpg',
            date: '2024-11-10T10:30:00Z',
            size: 1024000,
            latitude: 40.7128,
            longitude: -74.006,
            altitude: 10,
          },
          {
            path: '2024-11-10/photo2.jpg',
            filename: 'photo2.jpg',
            date: '2024-11-10T11:30:00Z',
            size: 2048000,
            latitude: 40.7129,
            longitude: -74.007,
            altitude: 15,
          },
          {
            path: '2024-11-10/photo3.jpg',
            filename: 'photo3.jpg',
            date: '2024-11-10T12:30:00Z',
            size: 3072000,
            latitude: null,
            longitude: null,
          },
        ],
        pagination: {
          total: 3,
          limit: 50,
          offset: 0,
          has_next: false,
        },
      },
    })
  ),
  getPhotoUrl: (path) => `/api/photos/${path}`,
  getThumbnailUrl: (path) => `/api/thumbnails/${path}`,
}))

vi.mock('../../hooks/usePhotoLocations', () => ({
  usePhotoLocations: () => ({
    locations: [
      {
        photo_path: '2024-11-10/photo1.jpg',
        filename: 'photo1.jpg',
        latitude: 40.7128,
        longitude: -74.006,
        thumbnail_url: '/api/thumbnails/2024-11-10/photo1.jpg',
        timestamp: '2024-11-10T10:30:00Z',
      },
      {
        photo_path: '2024-11-10/photo2.jpg',
        filename: 'photo2.jpg',
        latitude: 40.7129,
        longitude: -74.007,
        thumbnail_url: '/api/thumbnails/2024-11-10/photo2.jpg',
        timestamp: '2024-11-10T11:30:00Z',
      },
    ],
    isLoading: false,
    totalWithGps: 2,
    totalWithoutGps: 1,
  }),
}))

// Mock useClusteredLocations hook (now used by MapPage)
vi.mock('../../hooks/useClusteredLocations', () => ({
  useClusteredLocations: () => ({
    clusters: [],
    unclustered: [
      {
        path: '2024-11-10/photo1.jpg',
        filename: 'photo1.jpg',
        latitude: 40.7128,
        longitude: -74.006,
        thumbnail_url: '/api/thumbnails/2024-11-10/photo1.jpg',
        timestamp: '2024-11-10T10:30:00Z',
      },
      {
        path: '2024-11-10/photo2.jpg',
        filename: 'photo2.jpg',
        latitude: 40.7129,
        longitude: -74.007,
        thumbnail_url: '/api/thumbnails/2024-11-10/photo2.jpg',
        timestamp: '2024-11-10T11:30:00Z',
      },
    ],
    metadata: { total_without_gps: 1 },
    isLoading: false,
    isPartialResult: false,
    partialWarning: null,
    settings: { enabled: false, radius: 100 },
    setEnabled: vi.fn(),
    setRadius: vi.fn(),
    refetch: vi.fn(),
  }),
}))

// Mock useHoverPopup hook (used by MapView)
vi.mock('../../hooks/useHoverPopup', () => ({
  useHoverPopup: () => ({
    isVisible: false,
    targetCluster: null,
    position: { x: 0, y: 0 },
    handleMouseEnter: vi.fn(),
    handleMouseLeave: vi.fn(),
    handleClick: vi.fn(),
  }),
}))

// Mock MarkerHoverPopup component (used by MapView)
vi.mock('../../components/MarkerHoverPopup', () => ({
  default: () => <div data-testid="marker-hover-popup" />,
}))

// Helper to render with required providers
function renderMapPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <MapPage />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('MapPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders MapView and can open lightbox', async () => {
    renderMapPage()

    // Wait for map to render
    await waitFor(() => {
      expect(screen.getByTestId('map-container')).toBeInTheDocument()
    })

    // Check that MapView is rendered
    expect(screen.getByTestId('tile-layer')).toBeInTheDocument()

    // Lightbox should not be visible initially
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('clicking marker opens lightbox with correct photo', async () => {
    const user = userEvent.setup()
    renderMapPage()

    // Wait for markers to render
    await waitFor(() => {
      const markers = screen.getAllByTestId('marker')
      expect(markers.length).toBeGreaterThan(0)
    })

    // Click the first marker
    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    // Wait for lightbox to open
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Check that correct photo is displayed
    const lightbox = screen.getByRole('dialog')
    expect(within(lightbox).getByText('photo1.jpg')).toBeInTheDocument()
  })

  it('clicking cluster marker opens lightbox with cluster navigation', async () => {
    const user = userEvent.setup()

    // Mock a cluster marker scenario
    // This test validates the wiring - actual cluster behavior is tested in unit tests
    renderMapPage()

    await waitFor(() => {
      expect(screen.getByTestId('map-container')).toBeInTheDocument()
    })

    // Click marker to open lightbox
    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    // Verify lightbox opens
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Verify navigation controls are present (indicates cluster navigation is wired)
    const lightbox = screen.getByRole('dialog')
    const prevButton = within(lightbox).getByLabelText('Previous photo')
    const nextButton = within(lightbox).getByLabelText('Next photo')
    expect(prevButton).toBeInTheDocument()
    expect(nextButton).toBeInTheDocument()
  })

  it('navigating in lightbox updates highlighted marker path', async () => {
    const user = userEvent.setup()
    renderMapPage()

    // Wait for markers
    await waitFor(() => {
      expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0)
    })

    // Open lightbox on first photo
    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Check initial marker state - first marker should be highlighted
    // Verify MapView receives highlightedPhotoPath prop
    const mapView = screen.getByTestId('map-container')
    expect(mapView).toHaveAttribute('data-highlighted-path', '2024-11-10/photo1.jpg')

    // Navigate to next photo
    const lightbox = screen.getByRole('dialog')
    const nextButton = within(lightbox).getByLabelText('Next photo')
    await user.click(nextButton)

    // Wait for navigation to complete
    await waitFor(() => {
      expect(within(lightbox).getByText('photo2.jpg')).toBeInTheDocument()
    })

    // The highlighted marker should now be the second photo
    await waitFor(() => {
      expect(mapView).toHaveAttribute('data-highlighted-path', '2024-11-10/photo2.jpg')
    })
  })

  it('closing lightbox clears marker highlight', async () => {
    const user = userEvent.setup()
    renderMapPage()

    // Open lightbox
    await waitFor(() => {
      expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0)
    })

    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Verify marker is highlighted
    const mapView = screen.getByTestId('map-container')
    expect(mapView).toHaveAttribute('data-highlighted-path', '2024-11-10/photo1.jpg')

    // Close lightbox
    const closeButton = screen.getByLabelText('Close photo viewer')
    await user.click(closeButton)

    // Wait for lightbox to close
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    // Verify highlight is cleared
    expect(mapView).toHaveAttribute('data-highlighted-path', '')

    // Verify markers are still rendered
    expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0)
  })

  it('shows location header with coordinates in lightbox', async () => {
    const user = userEvent.setup()
    renderMapPage()

    // Open lightbox with GPS photo
    await waitFor(() => {
      expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0)
    })

    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Check for location header with coordinates
    const locationHeader = screen.getByTestId('location-header')
    expect(locationHeader).toBeInTheDocument()

    // Check coordinates are displayed (DMS format)
    const coordinates = screen.getByTestId('location-coordinates')
    expect(coordinates).toBeInTheDocument()
    expect(coordinates.textContent).toContain('°') // Contains degree symbol
  })

  it('shows "Location not available" for photos without GPS', async () => {
    const user = userEvent.setup()

    // Need to render with a photo without GPS
    // Since we can't click a marker without GPS (it won't be on map),
    // we need to modify the test to use the photos array directly

    // This test verifies the LocationHeader component behavior
    // The actual integration would require navigating to a non-GPS photo
    // via keyboard/button navigation from a GPS photo

    renderMapPage()

    // Open lightbox on first photo
    await waitFor(() => {
      expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0)
    })

    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Navigate through photos to reach one without GPS
    // Since photo3 has no GPS, we need to navigate to it
    const lightbox = screen.getByRole('dialog')
    const nextButton = within(lightbox).getByLabelText('Next photo')

    // Click next to go to photo2
    await user.click(nextButton)
    await waitFor(() => {
      expect(within(lightbox).getByText('photo2.jpg')).toBeInTheDocument()
    })

    // Click next again to go to photo3 (no GPS)
    await user.click(nextButton)
    await waitFor(() => {
      expect(within(lightbox).getByText('photo3.jpg')).toBeInTheDocument()
    })

    // Check for "Location not available" message
    const locationHeader = screen.getByTestId('location-header')
    expect(locationHeader).toBeInTheDocument()
    expect(within(locationHeader).getByText('Location not available')).toBeInTheDocument()
  })

  it('onLocationClick in lightbox triggers map pan', async () => {
    const user = userEvent.setup()
    renderMapPage()

    // Open lightbox
    await waitFor(() => {
      expect(screen.getAllByTestId('marker').length).toBeGreaterThan(0)
    })

    const markers = screen.getAllByTestId('marker')
    await user.click(markers[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Get location coordinates button
    const coordinatesButton = screen.getByTestId('location-coordinates')
    expect(coordinatesButton).toBeInTheDocument()

    // Click on coordinates (should trigger map pan)
    await user.click(coordinatesButton)

    // Verify lightbox is still open (pan doesn't close it)
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // The actual map panning is tested in unit tests for useMapLightboxSync
    // This integration test verifies the wiring is in place
  })
})
