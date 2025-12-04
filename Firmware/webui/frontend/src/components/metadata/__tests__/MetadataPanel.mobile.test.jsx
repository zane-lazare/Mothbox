import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataPanel from '../MetadataPanel'
import * as apiModule from '../../../utils/api'

// Mock the API module
vi.mock('../../../utils/api', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
  getPhotoSidecarMetadata: vi.fn(),
  updatePhotoSidecarMetadata: vi.fn(),
}))

const mockApiGet = vi.mocked(apiModule.api.get)
const mockGetPhotoSidecarMetadata = vi.mocked(apiModule.getPhotoSidecarMetadata)

// Mock child components
vi.mock('../AccordionSection', () => ({
  default: ({ title, children }) => (
    <div data-testid={`accordion-section-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div data-testid="accordion-content">{children}</div>
    </div>
  ),
}))

vi.mock('../SaveStatusIndicator', () => ({
  default: () => <div data-testid="save-status-indicator">Save Status</div>,
}))

vi.mock('../MetadataTags', () => ({
  default: () => <div data-testid="metadata-tags">Tags</div>,
}))

vi.mock('../MetadataSpecies', () => ({
  default: () => <div data-testid="metadata-species">Species</div>,
}))

vi.mock('../MetadataNotes', () => ({
  default: () => <div data-testid="metadata-notes">Notes</div>,
}))

vi.mock('../MetadataCustomFields', () => ({
  default: () => <div data-testid="metadata-custom-fields">Custom</div>,
}))

vi.mock('../MetadataEXIF', () => ({
  default: () => <div data-testid="metadata-exif">EXIF</div>,
}))

vi.mock('../MetadataSkeleton', () => ({
  default: () => <div data-testid="metadata-skeleton">Loading...</div>,
}))

const mockExifMetadata = {
  camera: { make: 'Arducam', model: 'OwlSight 64MP' },
  iso: 400,
}

const mockSidecarMetadata = {
  user_tags: ['moth'],
  species: 'Actias luna',
  notes: 'Test note',
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

function TestWrapper({ children }) {
  const queryClient = createTestQueryClient()
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

function mockSuccessfulDataLoad() {
  mockApiGet.mockResolvedValueOnce({ data: mockExifMetadata })
  mockGetPhotoSidecarMetadata.mockResolvedValueOnce({ data: mockSidecarMetadata })
}

describe('MetadataPanel - Mobile Drawer Behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Desktop Behavior', () => {
    it('panel is visible on desktop', async () => {
      mockSuccessfulDataLoad()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Panel should be visible
      const panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).toBeInTheDocument()
    })

    it('toggle button has md:hidden class for desktop', async () => {
      mockSuccessfulDataLoad()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Mobile toggle button should have md:hidden class (hidden on desktop)
      // Note: JSDOM doesn't apply media queries, so we check for the class instead
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      expect(toggleButton).toBeInTheDocument()
      expect(toggleButton).toHaveClass('md:hidden')
    })
  })

  describe('Mobile Behavior - Default State', () => {
    it('panel hidden on mobile by default', async () => {
      mockSuccessfulDataLoad()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Panel should have hidden class for mobile
      const panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).toHaveClass('hidden')
    })

    it('toggle button visible on mobile', async () => {
      mockSuccessfulDataLoad()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Mobile toggle button should be visible
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      expect(toggleButton).toBeInTheDocument()
      expect(toggleButton).toHaveAttribute('aria-label', 'Open metadata panel')
    })

    it('toggle button has floating action button styling', async () => {
      mockSuccessfulDataLoad()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      const toggleButton = screen.getByTestId('mobile-toggle-button')

      // Check for FAB-style classes
      expect(toggleButton).toHaveClass('fixed')
      expect(toggleButton).toHaveClass('bottom-4')
      expect(toggleButton).toHaveClass('right-4')
      expect(toggleButton).toHaveClass('rounded-full')
      expect(toggleButton).toHaveClass('z-40')
    })
  })

  describe('Mobile Behavior - Opening Drawer', () => {
    it('clicking toggle button shows drawer', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Initially hidden
      let panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).toHaveClass('hidden')

      // Click toggle button
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Panel should now be visible
      panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).not.toHaveClass('hidden')
    })

    it('drawer slides up from bottom with correct styles', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Check drawer has correct positioning classes
      const drawer = container.querySelector('[data-testid="metadata-panel"]')

      expect(drawer).toHaveClass('fixed')
      expect(drawer).toHaveClass('inset-x-0')
      expect(drawer).toHaveClass('bottom-0')
      expect(drawer).toHaveClass('z-50')
      expect(drawer.className).toContain('max-h-')
      expect(drawer).toHaveClass('rounded-t-2xl')
    })

    it('backdrop overlay appears when drawer opens', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // No overlay initially
      expect(screen.queryByTestId('mobile-overlay')).not.toBeInTheDocument()

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Overlay should appear
      const overlay = screen.getByTestId('mobile-overlay')
      expect(overlay).toBeInTheDocument()
      expect(overlay).toHaveClass('fixed')
      expect(overlay).toHaveClass('inset-0')
      expect(overlay.className).toContain('bg-black')
      expect(overlay).toHaveClass('z-40')
    })

    it('drawer shows close button when open', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // No close button when closed
      expect(screen.queryByTestId('drawer-close-button')).not.toBeInTheDocument()

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Close button should appear
      const closeButton = screen.getByTestId('drawer-close-button')
      expect(closeButton).toBeInTheDocument()
      expect(closeButton).toHaveAttribute('aria-label', 'Close metadata panel')
    })
  })

  describe('Mobile Behavior - Closing Drawer', () => {
    it('clicking close button hides drawer', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Verify it's open
      let panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).not.toHaveClass('hidden')

      // Close drawer
      const closeButton = screen.getByTestId('drawer-close-button')
      await user.click(closeButton)

      // Should be hidden again
      panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).toHaveClass('hidden')
    })

    it('clicking backdrop closes drawer', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Verify it's open
      let panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).not.toHaveClass('hidden')

      // Click backdrop
      const overlay = screen.getByTestId('mobile-overlay')
      await user.click(overlay)

      // Should be hidden again
      panelContainer = container.querySelector('[data-testid="metadata-panel"]')
      expect(panelContainer).toHaveClass('hidden')
    })

    it('overlay disappears when drawer closes', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Overlay present
      expect(screen.getByTestId('mobile-overlay')).toBeInTheDocument()

      // Close drawer
      const closeButton = screen.getByTestId('drawer-close-button')
      await user.click(closeButton)

      // Overlay should be gone
      expect(screen.queryByTestId('mobile-overlay')).not.toBeInTheDocument()
    })
  })

  describe('Mobile Behavior - Drawer Header', () => {
    it('drawer has mobile header with title and close button', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Check mobile header
      const mobileHeader = screen.getByTestId('drawer-mobile-header')
      expect(mobileHeader).toBeInTheDocument()
      expect(mobileHeader).toHaveTextContent('Photo Metadata')
    })
  })

  describe('Accessibility', () => {
    it('toggle button has accessible label', async () => {
      mockSuccessfulDataLoad()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      const toggleButton = screen.getByTestId('mobile-toggle-button')
      expect(toggleButton).toHaveAttribute('aria-label', 'Open metadata panel')
    })

    it('close button has accessible label', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      const closeButton = screen.getByTestId('drawer-close-button')
      expect(closeButton).toHaveAttribute('aria-label', 'Close metadata panel')
    })

    it('drawer has role and aria attributes', async () => {
      mockSuccessfulDataLoad()
      const user = userEvent.setup()

      const { container } = render(
        <TestWrapper>
          <MetadataPanel photoPath="/var/lib/mothbox/photos/test.jpg" />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.queryByTestId('metadata-skeleton')).not.toBeInTheDocument()
      })

      // Open drawer
      const toggleButton = screen.getByTestId('mobile-toggle-button')
      await user.click(toggleButton)

      // Check drawer has proper ARIA attributes
      const drawer = container.querySelector('[data-testid="metadata-panel"]')
      expect(drawer).toHaveAttribute('role', 'dialog')
      expect(drawer).toHaveAttribute('aria-label', 'Photo metadata')
    })
  })
})
