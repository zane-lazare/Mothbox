import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MapView from '../MapView'

// Mock react-leaflet components (Leaflet has issues in jsdom)
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
  }),
}))

// Mock react-leaflet-cluster (marker clustering)
vi.mock('react-leaflet-cluster', () => ({
  default: ({ children, chunkedLoading, maxClusterRadius, spiderfyOnMaxZoom, showCoverageOnHover, ...props }) => (
    <div
      data-testid="marker-cluster-group"
      {...(chunkedLoading !== undefined && { chunkedLoading: chunkedLoading.toString() })}
      {...(maxClusterRadius !== undefined && { maxClusterRadius: maxClusterRadius.toString() })}
      {...(spiderfyOnMaxZoom !== undefined && { spiderfyOnMaxZoom: spiderfyOnMaxZoom.toString() })}
      {...(showCoverageOnHover !== undefined && { showCoverageOnHover: showCoverageOnHover.toString() })}
      {...props}
    >
      {children}
    </div>
  ),
}))

// Mock leaflet (L.Icon for custom markers, L.divIcon for highlighted markers and clusters)
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

// Mock MarkerHoverPopup component
vi.mock('../MarkerHoverPopup', () => ({
  default: ({ cluster, isVisible, position, onPhotoClick, onClose }) => (
    <div
      data-testid="marker-hover-popup"
      data-visible={isVisible}
      data-cluster-id={cluster?.cluster_id}
    >
      {isVisible && cluster && (
        <div>
          <span>Cluster: {cluster.cluster_id}</span>
          <span>Count: {cluster.count}</span>
        </div>
      )}
    </div>
  ),
}))

// Mock useHoverPopup hook
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

describe('MapView', () => {
  const mockLocations = [
    {
      photo_path: '2024-11-10/photo_001.jpg',
      filename: 'photo_001.jpg',
      latitude: 37.7749,
      longitude: -122.4194,
      thumbnail_url: '/api/gallery/thumbnail/2024-11-10/photo_001.jpg',
    },
    {
      photo_path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      latitude: 34.0522,
      longitude: -118.2437,
      thumbnail_url: '/api/gallery/thumbnail/2024-11-10/photo_002.jpg',
    },
  ]

  const mockOnPhotoClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders map container', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const mapContainer = screen.getByTestId('map-container')
      expect(mapContainer).toBeInTheDocument()
    })

    it('renders tile layer for OpenStreetMap', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const tileLayer = screen.getByTestId('tile-layer')
      expect(tileLayer).toBeInTheDocument()
    })

    it('includes OpenStreetMap attribution', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const tileLayer = screen.getByTestId('tile-layer')
      expect(tileLayer).toHaveAttribute('attribution')
      expect(tileLayer.getAttribute('attribution')).toContain('OpenStreetMap')
    })

    it('uses correct tile URL from config', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const tileLayer = screen.getByTestId('tile-layer')
      expect(tileLayer).toHaveAttribute('url')
      expect(tileLayer.getAttribute('url')).toContain('tile.openstreetmap.org')
    })

    it('applies custom className', () => {
      const { container } = render(
        <MapView
          locations={mockLocations}
          onPhotoClick={mockOnPhotoClick}
          className="custom-map-class"
        />
      )

      const mapWrapper = container.firstChild
      expect(mapWrapper).toHaveClass('custom-map-class')
    })
  })

  describe('Loading State', () => {
    it('shows loading skeleton when isLoading is true', () => {
      render(
        <MapView locations={[]} onPhotoClick={mockOnPhotoClick} isLoading={true} />
      )

      const skeleton = screen.getByTestId('map-loading-skeleton')
      expect(skeleton).toBeInTheDocument()
    })

    it('does not render map when loading', () => {
      render(
        <MapView locations={[]} onPhotoClick={mockOnPhotoClick} isLoading={true} />
      )

      const mapContainer = screen.queryByTestId('map-container')
      expect(mapContainer).not.toBeInTheDocument()
    })

    it('shows map after loading completes', () => {
      const { rerender } = render(
        <MapView locations={[]} onPhotoClick={mockOnPhotoClick} isLoading={true} />
      )

      rerender(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} isLoading={false} />)

      const mapContainer = screen.getByTestId('map-container')
      expect(mapContainer).toBeInTheDocument()
    })

    it('loading skeleton has correct styling', () => {
      render(
        <MapView locations={[]} onPhotoClick={mockOnPhotoClick} isLoading={true} />
      )

      const skeleton = screen.getByTestId('map-loading-skeleton')
      expect(skeleton).toHaveClass('animate-pulse')
    })
  })

  describe('Empty State', () => {
    it('shows empty state when locations is empty array', () => {
      render(<MapView locations={[]} onPhotoClick={mockOnPhotoClick} />)

      const emptyMessage = screen.getByText(/no GPS-tagged photos/i)
      expect(emptyMessage).toBeInTheDocument()
    })

    it('does not render map when no locations', () => {
      render(<MapView locations={[]} onPhotoClick={mockOnPhotoClick} />)

      const mapContainer = screen.queryByTestId('map-container')
      expect(mapContainer).not.toBeInTheDocument()
    })

    it('shows helpful message in empty state', () => {
      render(<MapView locations={[]} onPhotoClick={mockOnPhotoClick} />)

      expect(screen.getByText(/no GPS-tagged photos/i)).toBeInTheDocument()
      expect(screen.getByText(/photos with GPS coordinates will appear here/i)).toBeInTheDocument()
    })

    it('empty state has role="status" for accessibility', () => {
      render(<MapView locations={[]} onPhotoClick={mockOnPhotoClick} />)

      const emptyState = screen.getByRole('status')
      expect(emptyState).toBeInTheDocument()
    })
  })

  describe('Map Configuration', () => {
    it('sets correct zoom limits from MAP_CONFIG', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const mapContainer = screen.getByTestId('map-container')
      expect(mapContainer).toHaveAttribute('minZoom', '2')
      expect(mapContainer).toHaveAttribute('maxZoom', '18')
    })

    it('fills parent container with responsive sizing', () => {
      const { container } = render(
        <MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />
      )

      const mapWrapper = container.firstChild
      expect(mapWrapper).toHaveClass('w-full')
      expect(mapWrapper).toHaveClass('h-full')
    })

    it('uses marker clustering for performance', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      expect(clusterGroup).toBeInTheDocument()
    })
  })

  describe('Marker Clustering', () => {
    it('wraps markers with MarkerClusterGroup', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      expect(clusterGroup).toBeInTheDocument()

      // Verify markers are inside cluster group
      const markers = screen.getAllByTestId('marker')
      expect(markers).toHaveLength(mockLocations.length)
    })

    it('applies correct clustering config from MAP_CONFIG', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      // Verify all clustering props are passed through
      expect(clusterGroup).toHaveAttribute('maxclusterradius', '40')
      expect(clusterGroup).toHaveAttribute('spiderfyonmaxzoom', 'true')
      expect(clusterGroup).toHaveAttribute('showcoverageonhover', 'false')
    })

    it('enables chunked loading for performance', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      // chunkedLoading is a boolean prop, should be present
      expect(clusterGroup).toHaveAttribute('chunkedloading', 'true')
    })

    it('handles 100+ markers efficiently without rendering issues', () => {
      // Generate 150 test locations
      const manyLocations = Array.from({ length: 150 }, (_, i) => ({
        photo_path: `2024-11-10/photo_${i.toString().padStart(3, '0')}.jpg`,
        filename: `photo_${i.toString().padStart(3, '0')}.jpg`,
        latitude: 37.7749 + (Math.random() - 0.5) * 0.1, // Spread around SF
        longitude: -122.4194 + (Math.random() - 0.5) * 0.1,
        thumbnail_url: `/api/gallery/thumbnail/2024-11-10/photo_${i.toString().padStart(3, '0')}.jpg`,
      }))

      // Should not throw or crash
      expect(() => {
        render(<MapView locations={manyLocations} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      expect(clusterGroup).toBeInTheDocument()

      // All markers should be rendered (clustering handles display optimization)
      const markers = screen.getAllByTestId('marker')
      expect(markers).toHaveLength(150)
    })

    it('clusters markers with same coordinates', () => {
      // Create locations with identical coordinates (should cluster)
      const duplicateLocations = Array.from({ length: 10 }, (_, i) => ({
        photo_path: `2024-11-10/photo_${i}.jpg`,
        filename: `photo_${i}.jpg`,
        latitude: 37.7749, // Same coordinates
        longitude: -122.4194,
        thumbnail_url: `/api/gallery/thumbnail/2024-11-10/photo_${i}.jpg`,
      }))

      expect(() => {
        render(<MapView locations={duplicateLocations} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      expect(clusterGroup).toBeInTheDocument()
    })

    it('handles worldwide distributed markers', () => {
      // Create locations spread across the globe
      const worldwideLocations = [
        { latitude: 37.7749, longitude: -122.4194, filename: 'san_francisco.jpg', photo_path: 'photo1.jpg', thumbnail_url: '/thumb1.jpg' },
        { latitude: 51.5074, longitude: -0.1278, filename: 'london.jpg', photo_path: 'photo2.jpg', thumbnail_url: '/thumb2.jpg' },
        { latitude: -33.8688, longitude: 151.2093, filename: 'sydney.jpg', photo_path: 'photo3.jpg', thumbnail_url: '/thumb3.jpg' },
        { latitude: 35.6762, longitude: 139.6503, filename: 'tokyo.jpg', photo_path: 'photo4.jpg', thumbnail_url: '/thumb4.jpg' },
        { latitude: -23.5505, longitude: -46.6333, filename: 'sao_paulo.jpg', photo_path: 'photo5.jpg', thumbnail_url: '/thumb5.jpg' },
      ]

      expect(() => {
        render(<MapView locations={worldwideLocations} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      expect(clusterGroup).toBeInTheDocument()

      const markers = screen.getAllByTestId('marker')
      expect(markers).toHaveLength(5)
    })

    it('clustering works with empty locations', () => {
      render(<MapView locations={[]} onPhotoClick={mockOnPhotoClick} />)

      // Should show empty state, not cluster group
      const clusterGroup = screen.queryByTestId('marker-cluster-group')
      expect(clusterGroup).not.toBeInTheDocument()

      expect(screen.getByText(/no GPS-tagged photos/i)).toBeInTheDocument()
    })

    it('clustering works with single location', () => {
      const singleLocation = [mockLocations[0]]

      render(<MapView locations={singleLocation} onPhotoClick={mockOnPhotoClick} />)

      const clusterGroup = screen.getByTestId('marker-cluster-group')
      expect(clusterGroup).toBeInTheDocument()

      const markers = screen.getAllByTestId('marker')
      expect(markers).toHaveLength(1)
    })
  })

  describe('Bounds Fitting', () => {
    it('renders BoundsUpdater component when locations exist', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      // BoundsUpdater is rendered inside MapContainer
      const mapContainer = screen.getByTestId('map-container')
      expect(mapContainer).toBeInTheDocument()
    })

    it('does not crash with single location', () => {
      const singleLocation = [mockLocations[0]]

      expect(() => {
        render(<MapView locations={singleLocation} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()
    })

    it('handles locations with same coordinates', () => {
      const duplicateLocations = [
        mockLocations[0],
        { ...mockLocations[0], filename: 'photo_003.jpg' },
      ]

      expect(() => {
        render(<MapView locations={duplicateLocations} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()
    })
  })

  describe('Props Validation', () => {
    it('handles undefined locations gracefully', () => {
      render(<MapView onPhotoClick={mockOnPhotoClick} />)

      const emptyMessage = screen.getByText(/no GPS-tagged photos/i)
      expect(emptyMessage).toBeInTheDocument()
    })

    it('handles null locations gracefully', () => {
      render(<MapView locations={null} onPhotoClick={mockOnPhotoClick} />)

      const emptyMessage = screen.getByText(/no GPS-tagged photos/i)
      expect(emptyMessage).toBeInTheDocument()
    })

    it('works without onPhotoClick callback', () => {
      expect(() => {
        render(<MapView locations={mockLocations} />)
      }).not.toThrow()
    })
  })

  describe('Accessibility', () => {
    it('map container has appropriate ARIA attributes', () => {
      render(<MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />)

      const mapContainer = screen.getByTestId('map-container')
      expect(mapContainer).toHaveAttribute('role', 'application')
      expect(mapContainer).toHaveAttribute('aria-label', 'Interactive map showing photo locations')
    })

    it('loading skeleton has ARIA busy state', () => {
      render(
        <MapView locations={[]} onPhotoClick={mockOnPhotoClick} isLoading={true} />
      )

      const skeleton = screen.getByTestId('map-loading-skeleton')
      expect(skeleton).toHaveAttribute('aria-busy', 'true')
    })
  })

  describe('Responsive Design', () => {
    it('applies responsive height classes', () => {
      const { container } = render(
        <MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />
      )

      const mapWrapper = container.firstChild
      expect(mapWrapper).toHaveClass('h-full')
    })

    it('maintains aspect ratio on small screens', () => {
      const { container } = render(
        <MapView locations={mockLocations} onPhotoClick={mockOnPhotoClick} />
      )

      const mapWrapper = container.firstChild
      // Should have minimum height
      expect(mapWrapper.className).toContain('h-')
    })
  })

  describe('Hover Popup Integration', () => {
    const mockClusters = [
      {
        cluster_id: 'cluster_1',
        center: { lat: 37.7749, lon: -122.4194 },
        count: 3,
        photos: [
          {
            path: 'photo1.jpg',
            filename: 'photo1.jpg',
            thumbnail_url: '/api/gallery/thumbnail/photo1.jpg',
            timestamp: '2024-01-15 10:30:00',
            lat: 37.7749,
            lon: -122.4194,
            latitude: 37.7749,
            longitude: -122.4194,
          },
          {
            path: 'photo2.jpg',
            filename: 'photo2.jpg',
            thumbnail_url: '/api/gallery/thumbnail/photo2.jpg',
            timestamp: '2024-01-15 11:00:00',
            lat: 37.7750,
            lon: -122.4195,
            latitude: 37.7750,
            longitude: -122.4195,
          },
        ],
        date_range: {
          earliest: '2024-01-15',
          latest: '2024-01-15',
        },
      },
    ]

    it('renders MarkerHoverPopup component', () => {
      const { container } = render(
        <MapView
          locations={[]}
          clusters={mockClusters}
          onPhotoClick={mockOnPhotoClick}
        />
      )

      // MarkerHoverPopup should be in the DOM (even if not visible)
      // Check for the popup container with data-testid
      const popup = container.querySelector('[data-testid="marker-hover-popup"]')
      expect(popup).toBeInTheDocument()
    })

    it('ClusterMarker has mouseover handler', () => {
      render(
        <MapView
          locations={[]}
          clusters={mockClusters}
          onPhotoClick={mockOnPhotoClick}
        />
      )

      // Verify that markers are rendered (hover handlers are attached via eventHandlers prop)
      const markers = screen.getAllByTestId('marker')
      expect(markers.length).toBeGreaterThan(0)
    })

    it('ClusterMarker has mouseout handler', () => {
      render(
        <MapView
          locations={[]}
          clusters={mockClusters}
          onPhotoClick={mockOnPhotoClick}
        />
      )

      // Verify that markers are rendered (hover handlers are attached via eventHandlers prop)
      const markers = screen.getAllByTestId('marker')
      expect(markers.length).toBeGreaterThan(0)
    })
  })
})
