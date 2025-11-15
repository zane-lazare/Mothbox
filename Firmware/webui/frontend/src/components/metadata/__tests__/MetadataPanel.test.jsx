import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataPanel from '../MetadataPanel'
import { api } from '../../../utils/api'

// Mock the API module
vi.mock('../../../utils/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

// Mock the child components
vi.mock('../CameraTab', () => ({
  default: ({ data }) => (
    <div data-testid="camera-tab">
      Camera Tab: {data ? 'loaded' : 'no data'}
    </div>
  ),
}))

vi.mock('../LocationTab', () => ({
  default: ({ data }) => (
    <div data-testid="location-tab">
      Location Tab: {data ? 'loaded' : 'no data'}
    </div>
  ),
}))

vi.mock('../CaptureTab', () => ({
  default: ({ data }) => (
    <div data-testid="capture-tab">
      Capture Tab: {data ? 'loaded' : 'no data'}
    </div>
  ),
}))

vi.mock('../TagsTab', () => ({
  default: ({ data }) => (
    <div data-testid="tags-tab">Tags Tab: {data ? 'loaded' : 'no data'}</div>
  ),
}))

vi.mock('../DeploymentTab', () => ({
  default: ({ data }) => (
    <div data-testid="deployment-tab">
      Deployment Tab: {data ? 'loaded' : 'no data'}
    </div>
  ),
}))

vi.mock('../MetadataSkeleton', () => ({
  default: ({ rows }) => (
    <div data-testid="metadata-skeleton" role="status">
      Loading skeleton with {rows} rows
    </div>
  ),
}))

/**
 * Complete mock metadata structure
 */
const mockMetadata = {
  camera: {
    camera: {
      make: 'Arducam',
      model: 'OwlSight 64MP',
      lens_make: 'Arducam',
      lens_model: '6mm Wide Angle',
    },
    iso: 400,
    aperture: 2.8,
    shutter_speed: 0.033333,
    focal_length: 6.0,
    exposure_mode: 'Manual',
    metering_mode: 'CenterWeighted',
  },
  location: {
    gps: {
      lat: 45.5231,
      lon: -122.6765,
      altitude: 50,
    },
    location: {
      city: 'Portland',
      state: 'Oregon',
      country: 'USA',
    },
  },
  capture: {
    datetime: '2024-01-15T22:30:45',
    timezone: 'America/Los_Angeles',
    flash: true,
    hdr: false,
    focus_bracket: true,
    focus_bracket_count: 5,
    focus_bracket_step: 0.5,
  },
  tags: {
    species: ['Actias luna', 'Antheraea polyphemus'],
    notes: 'Clear night, high moth activity',
    observer: 'Jane Doe',
    quality: 'excellent',
  },
  deployment: {
    device_id: 'mothbox-forest-01',
    location_name: 'Forest Grove Research Station',
    deployment_date: '2024-01-01',
    habitat: 'deciduous forest',
  },
}

/**
 * Create a fresh QueryClient for each test
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  })
}

/**
 * Wrapper component that provides QueryClient
 */
function TestWrapper({ children }) {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('MetadataPanel', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Clear all mocks after each test
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders all 5 tab triggers (Camera, Location, Capture, Tags, Deployment)', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Check all tab triggers are present
      expect(screen.getByRole('tab', { name: /camera/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /location/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /capture/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /tags/i })).toBeInTheDocument()
      expect(
        screen.getByRole('tab', { name: /deployment/i })
      ).toBeInTheDocument()
    })

    it('shows loading skeleton initially while fetching metadata', () => {
      api.get.mockImplementation(
        () =>
          new Promise((resolve) => {
            // Don't resolve immediately to keep loading state
            setTimeout(() => resolve({ ok: true, json: async () => mockMetadata }), 100)
          })
      )

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Should show skeleton immediately
      expect(screen.getByTestId('metadata-skeleton')).toBeInTheDocument()
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('displays Camera tab content by default after loading', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Camera tab should be visible
      expect(screen.getByTestId('camera-tab')).toBeVisible()

      // Other tabs should not be visible
      expect(screen.queryByTestId('location-tab')).not.toBeInTheDocument()
      expect(screen.queryByTestId('capture-tab')).not.toBeInTheDocument()
      expect(screen.queryByTestId('tags-tab')).not.toBeInTheDocument()
      expect(screen.queryByTestId('deployment-tab')).not.toBeInTheDocument()
    })

    it('hides tab content until metadata is loaded', () => {
      api.get.mockImplementation(
        () =>
          new Promise((resolve) => {
            // Keep loading indefinitely
            setTimeout(() => resolve({ ok: true, json: async () => mockMetadata }), 10000)
          })
      )

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Should only show skeleton, no tab content
      expect(screen.getByTestId('metadata-skeleton')).toBeInTheDocument()
      expect(screen.queryByTestId('camera-tab')).not.toBeInTheDocument()
      expect(screen.queryByTestId('location-tab')).not.toBeInTheDocument()
    })

    it('renders tab list with proper ARIA role', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      const tabList = screen.getByRole('tablist')
      expect(tabList).toBeInTheDocument()
      expect(tabList).toHaveAttribute('aria-label', 'Photo metadata tabs')
    })

    it('renders tab panels with proper ARIA role', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Should have at least one visible tab panel
      const tabPanels = screen.getAllByRole('tabpanel')
      expect(tabPanels.length).toBeGreaterThan(0)
    })
  })

  describe('Tab Switching', () => {
    it('switches to Location tab when clicked', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Click Location tab
      const locationTab = screen.getByRole('tab', { name: /location/i })
      await user.click(locationTab)

      // Location tab content should now be visible
      expect(screen.getByTestId('location-tab')).toBeVisible()
      expect(screen.queryByTestId('camera-tab')).not.toBeInTheDocument()
    })

    it('switches to Capture tab when clicked', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Click Capture tab
      const captureTab = screen.getByRole('tab', { name: /capture/i })
      await user.click(captureTab)

      // Capture tab content should now be visible
      expect(screen.getByTestId('capture-tab')).toBeVisible()
      expect(screen.queryByTestId('camera-tab')).not.toBeInTheDocument()
    })

    it('switches to Tags tab when clicked', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Click Tags tab
      const tagsTab = screen.getByRole('tab', { name: /tags/i })
      await user.click(tagsTab)

      // Tags tab content should now be visible
      expect(screen.getByTestId('tags-tab')).toBeVisible()
      expect(screen.queryByTestId('camera-tab')).not.toBeInTheDocument()
    })

    it('switches to Deployment tab when clicked', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Click Deployment tab
      const deploymentTab = screen.getByRole('tab', { name: /deployment/i })
      await user.click(deploymentTab)

      // Deployment tab content should now be visible
      expect(screen.getByTestId('deployment-tab')).toBeVisible()
      expect(screen.queryByTestId('camera-tab')).not.toBeInTheDocument()
    })

    it('tab switching completes within 100ms (performance requirement)', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Measure tab switch performance
      const locationTab = screen.getByRole('tab', { name: /location/i })
      const startTime = performance.now()
      await user.click(locationTab)
      const endTime = performance.now()

      const switchTime = endTime - startTime

      // Should complete within 100ms
      expect(switchTime).toBeLessThan(100)
    })

    it('active tab has proper aria-selected attribute', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Camera tab should be selected initially
      const cameraTab = screen.getByRole('tab', { name: /camera/i })
      expect(cameraTab).toHaveAttribute('aria-selected', 'true')

      // Location tab should not be selected
      const locationTab = screen.getByRole('tab', { name: /location/i })
      expect(locationTab).toHaveAttribute('aria-selected', 'false')

      // Click Location tab
      await user.click(locationTab)

      // Now Location tab should be selected
      expect(locationTab).toHaveAttribute('aria-selected', 'true')
      expect(cameraTab).toHaveAttribute('aria-selected', 'false')
    })
  })

  describe('Data Loading', () => {
    it('fetches metadata using usePhotoMetadata hook', async () => {
      const photoPath = '/var/lib/mothbox/photos/test.jpg'
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath={photoPath} />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          `/metadata/photo/${encodeURIComponent(photoPath)}/metadata`
        )
      })
    })

    it('passes photoPath to usePhotoMetadata correctly', async () => {
      const photoPath = '/var/lib/mothbox/photos/special-path/image.jpg'
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath={photoPath} />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          `/metadata/photo/${encodeURIComponent(photoPath)}/metadata`
        )
      })
    })

    it('loading state shows MetadataSkeleton', () => {
      api.get.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ ok: true, json: async () => mockMetadata }), 1000)
          })
      )

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Should show skeleton
      expect(screen.getByTestId('metadata-skeleton')).toBeInTheDocument()
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('success state shows tab content', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Should show tab content
      expect(screen.getByTestId('camera-tab')).toBeInTheDocument()
      expect(screen.getByRole('tablist')).toBeInTheDocument()
    })

    it('passes metadata to tabs correctly', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Check Camera tab receives data
      expect(screen.getByTestId('camera-tab')).toHaveTextContent('loaded')

      // Switch to Location tab
      await user.click(screen.getByRole('tab', { name: /location/i }))
      expect(screen.getByTestId('location-tab')).toHaveTextContent('loaded')

      // Switch to Capture tab
      await user.click(screen.getByRole('tab', { name: /capture/i }))
      expect(screen.getByTestId('capture-tab')).toHaveTextContent('loaded')

      // Switch to Tags tab
      await user.click(screen.getByRole('tab', { name: /tags/i }))
      expect(screen.getByTestId('tags-tab')).toHaveTextContent('loaded')

      // Switch to Deployment tab
      await user.click(screen.getByRole('tab', { name: /deployment/i }))
      expect(screen.getByTestId('deployment-tab')).toHaveTextContent('loaded')
    })
  })

  describe('Error Handling', () => {
    it('handles API 404 errors gracefully', async () => {
      const error = new Error('Request failed with status code 404')
      error.response = {
        status: 404,
        statusText: 'Not Found',
      }
      api.get.mockRejectedValueOnce(error)

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/missing.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })
    })

    it('handles API 500 errors gracefully', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = {
        status: 500,
        statusText: 'Internal Server Error',
      }
      api.get.mockRejectedValueOnce(error)

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })
    })

    it('shows "Failed to load metadata" message on error', async () => {
      api.get.mockRejectedValueOnce(new Error('Network error'))

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })
    })

    it('shows retry suggestion on error', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = {
        status: 500,
        statusText: 'Internal Server Error',
      }
      api.get.mockRejectedValueOnce(error)

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/try again/i)).toBeInTheDocument()
      })
    })

    it('error state shows error message instead of tabs', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = {
        status: 500,
        statusText: 'Internal Server Error',
      }
      api.get.mockRejectedValueOnce(error)

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })

      // Should not show tabs
      expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
      expect(screen.queryByTestId('camera-tab')).not.toBeInTheDocument()
    })

    it('shows retry button on error that triggers refetch', async () => {
      // First call fails
      api.get.mockRejectedValueOnce(new Error('Network error'))

      const { rerender } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText(/failed to load metadata/i)).toBeInTheDocument()
      })

      // Retry button should be visible
      const retryButton = screen.getByRole('button', { name: /retry/i })
      expect(retryButton).toBeInTheDocument()

      // Second call succeeds
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      // Click retry button
      await userEvent.click(retryButton)

      // Should eventually show the tabs after successful refetch
      await waitFor(() => {
        expect(screen.getByRole('tablist')).toBeInTheDocument()
      })

      // Error message should be gone
      expect(screen.queryByText(/failed to load metadata/i)).not.toBeInTheDocument()
    })
  })

  describe('Responsive Layout', () => {
    it('applies responsive layout classes', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Check for responsive flex classes
      const tabsRoot = container.querySelector('[role="tablist"]').parentElement
      expect(tabsRoot).toHaveClass('flex')
    })
  })

  describe('Accessibility', () => {
    it('all tabs have accessible labels', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // All tabs should have accessible names
      expect(screen.getByRole('tab', { name: /camera/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /location/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /capture/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /tags/i })).toBeInTheDocument()
      expect(
        screen.getByRole('tab', { name: /deployment/i })
      ).toBeInTheDocument()
    })

    it('tab list has proper ARIA attributes', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      const tabList = screen.getByRole('tablist')
      expect(tabList).toHaveAttribute('aria-label', 'Photo metadata tabs')
    })

    it('keyboard navigation works (test aria-selected changes)', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      const cameraTab = screen.getByRole('tab', { name: /camera/i })
      const locationTab = screen.getByRole('tab', { name: /location/i })

      // Initially Camera tab should be selected
      expect(cameraTab).toHaveAttribute('aria-selected', 'true')

      // Focus the location tab and press Space to activate it
      locationTab.focus()
      await user.keyboard('{Space}')

      // Location tab should now be selected
      await waitFor(() => {
        expect(locationTab).toHaveAttribute('aria-selected', 'true')
        expect(cameraTab).toHaveAttribute('aria-selected', 'false')
      })
    })

    it('each tab has proper aria-controls', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Each tab should have aria-controls attribute
      const tabs = screen.getAllByRole('tab')
      tabs.forEach((tab) => {
        expect(tab).toHaveAttribute('aria-controls')
        expect(tab.getAttribute('aria-controls')).toBeTruthy()
      })
    })
  })

  describe('State Management', () => {
    it('remembers selected tab when photoPath changes', async () => {
      api.get.mockResolvedValue({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      const { rerender } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/photo1.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Switch to Location tab
      await user.click(screen.getByRole('tab', { name: /location/i }))
      expect(screen.getByTestId('location-tab')).toBeVisible()

      // Change photo path (should remember Location tab)
      rerender(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/photo2.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Should still be on Location tab
      expect(screen.getByTestId('location-tab')).toBeVisible()
      expect(
        screen.getByRole('tab', { name: /location/i })
      ).toHaveAttribute('aria-selected', 'true')
    })

    it('defaults to camera tab on initial render', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Camera tab should be selected
      expect(screen.getByRole('tab', { name: /camera/i })).toHaveAttribute(
        'aria-selected',
        'true'
      )
      expect(screen.getByTestId('camera-tab')).toBeVisible()
    })

    it('tab state persists across re-renders', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const user = userEvent.setup()

      const { rerender } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Switch to Capture tab
      await user.click(screen.getByRole('tab', { name: /capture/i }))
      expect(screen.getByTestId('capture-tab')).toBeVisible()

      // Force re-render with same props
      rerender(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      // Should still be on Capture tab
      expect(screen.getByTestId('capture-tab')).toBeVisible()
      expect(screen.getByRole('tab', { name: /capture/i })).toHaveAttribute(
        'aria-selected',
        'true'
      )
    })
  })

  describe('Edge Cases', () => {
    it('handles null metadata gracefully', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,
        data: null,
      })

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Should still render tabs but with no data
      expect(screen.getByRole('tablist')).toBeInTheDocument()
      expect(screen.getByTestId('camera-tab')).toHaveTextContent('no data')
    })

    it('handles partial metadata gracefully', async () => {
      const partialMetadata = {
        camera: mockMetadata.camera,
        // Missing other sections
      }

      api.get.mockResolvedValueOnce({
        data: mockMetadata,
        data: partialMetadata,
      })

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Camera tab should have data
      expect(screen.getByTestId('camera-tab')).toHaveTextContent('loaded')

      // Location tab should have no data
      await user.click(screen.getByRole('tab', { name: /location/i }))
      expect(screen.getByTestId('location-tab')).toHaveTextContent('no data')
    })

    it('handles empty photoPath gracefully', () => {
      render(
        <TestWrapper>
          <MetadataPanel photoPath="" />
        </TestWrapper>
      )

      // Should not make API request
      expect(api.get).not.toHaveBeenCalled()

      // Should not show skeleton (query is disabled)
      expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
    })

    it('handles undefined photoPath gracefully', () => {
      render(
        <TestWrapper>
          <MetadataPanel photoPath={undefined} />
        </TestWrapper>
      )

      // Should not make API request
      expect(api.get).not.toHaveBeenCalled()

      // Should not show skeleton (query is disabled)
      expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
    })

    it('applies custom className prop', async () => {
      api.get.mockResolvedValueOnce({
        data: mockMetadata,

      })

      const { container } = render(
        <TestWrapper>
          <MetadataPanel
            photoPath="/var/lib/mothbox/photos/test.jpg"
            className="custom-class"
          />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Root element should have custom class
      expect(container.firstChild).toHaveClass('custom-class')
    })
  })
})
