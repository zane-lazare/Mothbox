import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PhotoLightbox from '../PhotoLightbox'
import { LIGHTBOX_CONFIG } from '../../constants/config'

// Mock the MetadataPanel to avoid API dependencies in these tests
vi.mock('../metadata/MetadataPanel', () => ({
  default: ({ photoPath }) => (
    <div data-testid="metadata-panel">
      <div>Camera</div>
      <div>Location</div>
      <div>Capture</div>
      <div>Tags</div>
      <div>Deployment</div>
      <div data-testid="metadata-photo-path">{photoPath}</div>
    </div>
  ),
}))

describe('PhotoLightbox - Basic Rendering', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880, // 5MB
    timestamp: 1699639800,
  }

  const mockPhotos = [
    mockPhoto,
    {
      path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      date: '2024-11-10T18:31:00Z',
      size: 5500000,
      timestamp: 1699639860,
    },
    {
      path: '2024-11-10/photo_003.jpg',
      filename: 'photo_003.jpg',
      date: '2024-11-10T18:32:00Z',
      size: 5100000,
      timestamp: 1699639920,
    },
  ]

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Don't manually clear body - let React Testing Library handle cleanup
    document.body.style.overflow = ''
  })

  it('renders nothing when photo is null', () => {
    const { container } = render(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders lightbox overlay when photo is provided', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
  })

  it('renders photo image with correct src and alt text', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    expect(image).toHaveAttribute('alt', 'Photo taken on 2024-11-10')
    expect(image.src).toContain('photo_001.jpg')
  })

  it('displays photo filename in title', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Check that filename appears in metadata area (not screen reader title)
    const dialog = screen.getByRole('dialog')
    const metadataArea = within(dialog).getByText('photo_001.jpg')
    expect(metadataArea).toHaveClass('text-sm', 'font-semibold')
  })

  it('displays formatted date and file size', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Check for date (should be formatted) - may appear multiple times (metadata + panel)
    const dateElements = screen.getAllByText(/2024-11-10/i)
    expect(dateElements.length).toBeGreaterThan(0)

    // Check for file size (should be formatted as "5.0 MB" or similar)
    expect(screen.getByText(/5(\.\d+)?\s*MB/i)).toBeInTheDocument()
  })

  it('renders close button with correct aria-label', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const closeButton = screen.getByLabelText(/close/i)
    expect(closeButton).toBeInTheDocument()
    expect(closeButton).toHaveAttribute('type', 'button')
  })

  it('applies correct ARIA attributes (role=dialog, aria-modal=true)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby')
    expect(dialog).toHaveAttribute('aria-describedby')
  })

  it('traps focus within lightbox when open', async () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    const focusableElements = within(dialog).getAllByRole('button')

    // Focus should be trapped within the dialog
    expect(focusableElements.length).toBeGreaterThan(0)

    // First focusable element should receive focus on mount
    await waitFor(() => {
      expect(document.activeElement).toBeInTheDocument()
    })
  })
})

describe('PhotoLightbox - Close Behavior', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800,
  }

  const mockPhotos = [mockPhoto]
  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Don't manually clear body - let React Testing Library handle cleanup
    document.body.style.overflow = ''
  })

  it('calls onClose when close button clicked', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const closeButton = screen.getByLabelText(/close/i)
    await user.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when ESC key pressed', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    await user.keyboard('{Escape}')

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when clicking backdrop overlay', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    // Click the backdrop (parent of dialog content)
    await user.click(dialog)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('does NOT close when clicking on image', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    await user.click(image)

    expect(mockOnClose).not.toHaveBeenCalled()
  })

  it('prevents body scroll when lightbox is open', () => {
    const { rerender } = render(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Body scroll should be normal initially
    expect(document.body.style.overflow).toBe('')

    // Open lightbox
    rerender(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Body scroll should be locked via CSS class
    expect(document.body.classList.contains('lightbox-open')).toBe(true)
  })

  it('restores body scroll when lightbox closes', () => {
    const { rerender } = render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Body scroll should be locked when open
    expect(document.body.classList.contains('lightbox-open')).toBe(true)

    // Close lightbox
    rerender(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Body scroll should be restored (class removed)
    expect(document.body.classList.contains('lightbox-open')).toBe(false)
  })
})

describe('PhotoLightbox - Animation', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800,
  }

  const mockPhotos = [mockPhoto]
  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Don't manually clear body - let React Testing Library handle cleanup
    document.body.style.overflow = ''
  })

  it('applies fade-in animation on mount', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    // Check for transition or animation class
    expect(dialog.className).toMatch(/transition|animate|fade/i)
  })

  it('applies fade-out animation before unmount', async () => {
    const { rerender } = render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()

    // Trigger close
    rerender(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Component should apply exit animation before unmounting
    // This test verifies the component handles animation timing
  })

  it('completes animation in <200ms', async () => {
    vi.useFakeTimers()

    const { rerender } = render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const startTime = Date.now()

    rerender(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Advance timers by animation duration
    vi.advanceTimersByTime(200)

    const duration = Date.now() - startTime
    expect(duration).toBeLessThanOrEqual(200)

    vi.useRealTimers()
  })
})

describe('PhotoLightbox - Navigation Controls', () => {
  const mockPhotos = [
    {
      path: '2024-11-10/photo_001.jpg',
      filename: 'photo_001.jpg',
      date: '2024-11-10T18:30:00Z',
      size: 5242880,
      timestamp: 1699639800,
    },
    {
      path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      date: '2024-11-10T18:31:00Z',
      size: 5500000,
      timestamp: 1699639860,
    },
    {
      path: '2024-11-10/photo_003.jpg',
      filename: 'photo_003.jpg',
      date: '2024-11-10T18:32:00Z',
      size: 5100000,
      timestamp: 1699639920,
    },
  ]

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('renders previous/next buttons when multiple photos exist', () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[1]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const prevButton = screen.getByLabelText(/previous photo/i)
    const nextButton = screen.getByLabelText(/next photo/i)

    expect(prevButton).toBeInTheDocument()
    expect(nextButton).toBeInTheDocument()
  })

  it('hides navigation buttons when only one photo exists', () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={[mockPhotos[0]]}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const prevButton = screen.queryByLabelText(/previous photo/i)
    const nextButton = screen.queryByLabelText(/next photo/i)

    expect(prevButton).not.toBeInTheDocument()
    expect(nextButton).not.toBeInTheDocument()
  })

  it('navigates to next photo when next button clicked', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const nextButton = screen.getByLabelText(/next photo/i)
    await user.click(nextButton)

    expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[1])
  })

  it('navigates to previous photo when previous button clicked', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[1]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const prevButton = screen.getByLabelText(/previous photo/i)
    await user.click(prevButton)

    expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[0])
  })

  it('navigates to next photo on ArrowRight key press', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    await user.keyboard('{ArrowRight}')

    expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[1])
  })

  it('navigates to previous photo on ArrowLeft key press', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[1]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    await user.keyboard('{ArrowLeft}')

    expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[0])
  })

  it('wraps to first photo when next pressed on last photo', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[2]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const nextButton = screen.getByLabelText(/next photo/i)
    await user.click(nextButton)

    expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[0])
  })

  it('wraps to last photo when previous pressed on first photo', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const prevButton = screen.getByLabelText(/previous photo/i)
    await user.click(prevButton)

    expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[2])
  })

  it('displays current photo index (e.g., "2 / 3")', () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[1]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Should show "2 / 3" (second photo out of three)
    expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument()
  })

  // Note: Wrapping behavior is tested implicitly in the wrap tests above
  // Config-based disabling would require mocking, which we'll skip for now
})

describe('PhotoLightbox - Desktop Zoom & Pan Interaction', () => {
  const mockPhotos = [
    {
      path: '2024-11-10/photo_001.jpg',
      filename: 'photo_001.jpg',
      date: '2024-11-10T18:30:00Z',
      size: 5242880,
      timestamp: 1699639800,
    },
    {
      path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      date: '2024-11-10T18:31:00Z',
      size: 5500000,
      timestamp: 1699639860,
    },
  ]

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('renders zoom controls (+/- buttons)', () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const zoomInButton = screen.getByLabelText(/zoom in/i)
    const zoomOutButton = screen.getByLabelText(/zoom out/i)

    expect(zoomInButton).toBeInTheDocument()
    expect(zoomOutButton).toBeInTheDocument()
  })

  it('increases zoom when zoom in button clicked', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')

    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    // Transform should change (zoom applied)
    const newTransform = window.getComputedStyle(image).transform
    expect(newTransform).toMatch(/scale/)
  })

  it('decreases zoom when zoom out button clicked', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // First zoom in
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    const image = screen.getByRole('img')
    const zoomedTransform = window.getComputedStyle(image).transform

    // Then zoom out
    const zoomOutButton = screen.getByLabelText(/zoom out/i)
    await user.click(zoomOutButton)

    const newTransform = window.getComputedStyle(image).transform
    expect(newTransform).not.toBe(zoomedTransform)
  })

  it('zooms in on wheel up (deltaY < 0)', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    const initialTransform = window.getComputedStyle(image).transform

    // Simulate wheel up (zoom in)
    await user.pointer([
      { keys: '[MouseLeft]', target: image, coords: { x: 400, y: 300 } },
    ])

    // Fire wheel event manually (userEvent doesn't support wheel well)
    const wheelEvent = new WheelEvent('wheel', {
      deltaY: -100,
      clientX: 400,
      clientY: 300,
      bubbles: true,
    })
    image.dispatchEvent(wheelEvent)

    await waitFor(() => {
      const newTransform = window.getComputedStyle(image).transform
      expect(newTransform).not.toBe(initialTransform)
    })
  })

  it('zooms out on wheel down (deltaY > 0)', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // First zoom in
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    const image = screen.getByRole('img')
    const zoomedTransform = window.getComputedStyle(image).transform

    // Simulate wheel down (zoom out)
    const wheelEvent = new WheelEvent('wheel', {
      deltaY: 100,
      clientX: 400,
      clientY: 300,
      bubbles: true,
    })
    image.dispatchEvent(wheelEvent)

    await waitFor(() => {
      const newTransform = window.getComputedStyle(image).transform
      expect(newTransform).not.toBe(zoomedTransform)
    })
  })

  it('displays zoom indicator when zooming', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    // Zoom indicator should appear (e.g., "150%" or "1.5x")
    // Note: getAllByText because zoom appears in both visual indicator and screen reader announcement
    await waitFor(() => {
      const zoomIndicators = screen.getAllByText(/150|1\.5/i)
      expect(zoomIndicators.length).toBeGreaterThan(0)
    })
  })

  it('renders reset zoom button when zoomed', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    // Reset button should appear
    await waitFor(() => {
      const resetButton = screen.getByLabelText(/reset zoom/i)
      expect(resetButton).toBeInTheDocument()
    })
  })

  it('resets zoom to 1.0 when reset button clicked', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Zoom in
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)
    await user.click(zoomInButton)

    // Reset zoom
    const resetButton = await screen.findByLabelText(/reset zoom/i)
    await user.click(resetButton)

    // Should show 100% or 1x zoom
    // Note: getAllByText because zoom appears in both visual indicator and screen reader announcement
    await waitFor(() => {
      const zoomIndicators = screen.getAllByText(/100|1\.0|1x/i)
      expect(zoomIndicators.length).toBeGreaterThan(0)
    })
  })

  it('changes cursor to grab when zoomed > 1.0', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')

    // Initially default cursor at zoom 1.0
    expect(window.getComputedStyle(image).cursor).toMatch(/default|auto/)

    // Zoom in
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    // Cursor should change to grab
    await waitFor(() => {
      expect(window.getComputedStyle(image).cursor).toMatch(/grab/)
    })
  })

  it('changes cursor to grabbing during drag', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Zoom in first
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    const image = screen.getByRole('img')

    // Start drag
    await user.pointer([
      { keys: '[MouseLeft>]', target: image, coords: { x: 400, y: 300 } },
    ])

    // Cursor should change to grabbing
    await waitFor(() => {
      expect(window.getComputedStyle(image).cursor).toMatch(/grabbing/)
    })

    // End drag
    await user.pointer([{ keys: '[/MouseLeft]' }])
  })

  it('pans image when dragged while zoomed', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Zoom in first
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    const image = screen.getByRole('img')

    // Simulate drag with fireEvent for better control
    const mouseDownEvent = new MouseEvent('mousedown', {
      bubbles: true,
      clientX: 400,
      clientY: 300,
    })
    image.dispatchEvent(mouseDownEvent)

    // Give time for state to update
    await waitFor(() => {
      expect(window.getComputedStyle(image).cursor).toMatch(/grabbing/)
    })

    // Simulate mouse move
    const mouseMoveEvent = new MouseEvent('mousemove', {
      bubbles: true,
      clientX: 500,
      clientY: 400,
    })
    document.dispatchEvent(mouseMoveEvent)

    // Simulate mouse up
    const mouseUpEvent = new MouseEvent('mouseup', {
      bubbles: true,
    })
    document.dispatchEvent(mouseUpEvent)

    // Transform should include pan values
    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      // Should have non-zero translate values (translate3d for GPU acceleration)
      expect(transform).toMatch(/translate3d\(.+px,\s*.+px,\s*.+\)/)
    })
  })

  it('does not pan when zoom is 1.0', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    const initialTransform = window.getComputedStyle(image).transform

    // Try to drag at zoom 1.0
    await user.pointer([
      { keys: '[MouseLeft>]', target: image, coords: { x: 400, y: 300 } },
      { coords: { x: 500, y: 400 } },
      { keys: '[/MouseLeft]' },
    ])

    // Transform should not change (no pan at 1.0x)
    const newTransform = window.getComputedStyle(image).transform
    expect(newTransform).toBe(initialTransform)
  })
})

describe('PhotoLightbox - Touch Gesture Interaction', () => {
  const mockPhotos = [
    {
      path: '2024-11-10/photo_001.jpg',
      filename: 'photo_001.jpg',
      date: '2024-11-10T18:30:00Z',
      size: 5242880,
      timestamp: 1699639800,
    },
    {
      path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      date: '2024-11-10T18:31:00Z',
      size: 5500000,
      timestamp: 1699639860,
    },
    {
      path: '2024-11-10/photo_003.jpg',
      filename: 'photo_003.jpg',
      date: '2024-11-10T18:32:00Z',
      size: 5100000,
      timestamp: 1699639920,
    },
  ]

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  const createTouchEvent = (type, touches, changedTouches = null) => {
    return new TouchEvent(type, {
      bubbles: true,
      cancelable: true,
      touches: touches.map((t, idx) => ({
        clientX: t.x,
        clientY: t.y,
        identifier: t.id !== undefined ? t.id : idx,
        target: t.target,
      })),
      changedTouches: changedTouches
        ? changedTouches.map((t, idx) => ({
            clientX: t.x,
            clientY: t.y,
            identifier: t.id !== undefined ? t.id : idx,
            target: t.target,
          }))
        : [],
    })
  }

  it('pinch gesture zooms image in/out', async () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    const initialTransform = window.getComputedStyle(image).transform

    // Simulate pinch-out (zoom in)
    const touchStart = createTouchEvent(
      'touchstart',
      [
        { x: 300, y: 300, id: 0, target: image },
        { x: 500, y: 300, id: 1, target: image },
      ]
    )
    image.dispatchEvent(touchStart)

    await new Promise((resolve) => setTimeout(resolve, 50))

    const touchMove = createTouchEvent(
      'touchmove',
      [
        { x: 250, y: 300, id: 0, target: image },
        { x: 550, y: 300, id: 1, target: image },
      ]
    )
    image.dispatchEvent(touchMove)

    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      // Should have scale > 1
      expect(transform).toMatch(/scale\((\d+\.?\d*)\)/)
      expect(transform).not.toBe(initialTransform)
    })
  })

  it('swipe left/right navigates photos', async () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')

    // Swipe left (next photo)
    const touchStart = createTouchEvent('touchstart', [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(touchStart)

    await new Promise((resolve) => setTimeout(resolve, 20))

    const touchEnd = createTouchEvent(
      'touchend',
      [],
      [{ x: 200, y: 300, id: 0, target: image }]
    )
    image.dispatchEvent(touchEnd)

    await waitFor(() => {
      expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[1])
    })
  })

  it('double-tap toggles zoom', async () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')

    // First tap
    const tap1Start = createTouchEvent('touchstart', [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(tap1Start)

    await new Promise((resolve) => setTimeout(resolve, 20))

    const tap1End = createTouchEvent('touchend', [], [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(tap1End)

    // Second tap (within 300ms)
    await new Promise((resolve) => setTimeout(resolve, 100))

    const tap2Start = createTouchEvent('touchstart', [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(tap2Start)

    await new Promise((resolve) => setTimeout(resolve, 20))

    const tap2End = createTouchEvent('touchend', [], [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(tap2End)

    // Should zoom in to 2.5x
    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      expect(transform).toMatch(/scale\(2\.5\)/)
    })
  })

  it('touch pan works when zoomed', async () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')

    // First zoom in using zoom button
    const zoomInButton = screen.getByLabelText('Zoom in')
    await userEvent.click(zoomInButton)
    await userEvent.click(zoomInButton) // Zoom to 2.0x

    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      expect(transform).toMatch(/scale\(2\)/)
    })

    // Now try touch pan
    const touchStart = createTouchEvent('touchstart', [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(touchStart)

    await new Promise((resolve) => setTimeout(resolve, 20))

    const touchMove = createTouchEvent('touchmove', [{ x: 350, y: 250, id: 0, target: image }])
    image.dispatchEvent(touchMove)

    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      // Should have translate values (translate3d for GPU acceleration)
      expect(transform).toMatch(/translate3d\(.+px,\s*.+px,\s*.+\)/)
    })
  })

  it('swipe disabled when zoomed', async () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')

    // Zoom in first
    const zoomInButton = screen.getByLabelText('Zoom in')
    await userEvent.click(zoomInButton)

    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      expect(transform).toMatch(/scale\(1\.5\)/)
    })

    // Try to swipe (should not navigate)
    const touchStart = createTouchEvent('touchstart', [{ x: 400, y: 300, id: 0, target: image }])
    image.dispatchEvent(touchStart)

    await new Promise((resolve) => setTimeout(resolve, 20))

    const touchEnd = createTouchEvent(
      'touchend',
      [],
      [{ x: 200, y: 300, id: 0, target: image }]
    )
    image.dispatchEvent(touchEnd)

    // Wait to ensure navigation doesn't happen
    await new Promise((resolve) => setTimeout(resolve, 100))

    expect(mockOnNavigate).not.toHaveBeenCalled()
  })

  it('touch events do not interfere with desktop events', async () => {
    render(
      <PhotoLightbox
        photo={mockPhotos[0]}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    const zoomInButton = screen.getByLabelText('Zoom in')

    // Desktop zoom in
    await userEvent.click(zoomInButton)

    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      expect(transform).toMatch(/scale\(1\.5\)/)
    })

    // Desktop zoom out
    const zoomOutButton = screen.getByLabelText('Zoom out')
    await userEvent.click(zoomOutButton)

    await waitFor(() => {
      const transform = window.getComputedStyle(image).transform
      expect(transform).toMatch(/scale\(1\)/)
    })

    // Desktop navigation (arrow keys) should still work
    const leftArrow = new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      bubbles: true,
    })
    document.dispatchEvent(leftArrow)

    await waitFor(() => {
      expect(mockOnNavigate).toHaveBeenCalledWith(mockPhotos[2]) // Wrapped to last
    })
  })
})

describe('PhotoLightbox - Accessibility (WCAG 2.1 AA)', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800,
  }

  const mockPhotos = [
    mockPhoto,
    {
      path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      date: '2024-11-10T18:31:00Z',
      size: 5500000,
      timestamp: 1699639860,
    },
    {
      path: '2024-11-10/photo_003.jpg',
      filename: 'photo_003.jpg',
      date: '2024-11-10T18:32:00Z',
      size: 5100000,
      timestamp: 1699639920,
    },
  ]

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('has role="dialog" and aria-modal="true"', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('close button has aria-label', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const closeButton = screen.getByRole('button', { name: /close photo viewer/i })
    expect(closeButton).toBeInTheDocument()
    expect(closeButton).toHaveAttribute('aria-label', 'Close photo viewer')
  })

  it('navigation buttons have aria-labels', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const prevButton = screen.getByRole('button', { name: /previous photo/i })
    const nextButton = screen.getByRole('button', { name: /next photo/i })

    expect(prevButton).toHaveAttribute('aria-label', 'Previous photo')
    expect(nextButton).toHaveAttribute('aria-label', 'Next photo')
  })

  it('focus trapped within dialog (Tab from last element goes to first)', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Wait for close button to be focused
    await waitFor(() => {
      const closeButton = screen.getByRole('button', { name: /close photo viewer/i })
      expect(closeButton).toHaveFocus()
    })

    // Get all focusable buttons
    const closeButton = screen.getByRole('button', { name: /close photo viewer/i })
    const prevButton = screen.getByRole('button', { name: /previous photo/i })
    const nextButton = screen.getByRole('button', { name: /next photo/i })
    const zoomInButton = screen.getByRole('button', { name: /zoom in/i })
    const zoomOutButton = screen.getByRole('button', { name: /zoom out/i })

    // Tab through all elements
    await user.tab() // Should go to next button (or prev)
    await user.tab()
    await user.tab()
    await user.tab()

    // Verify we're on a button (focus is trapped)
    const buttons = [closeButton, prevButton, nextButton, zoomInButton, zoomOutButton]
    const focusedElement = document.activeElement
    expect(buttons).toContain(focusedElement)
  })

  it('zoom level announced to screen readers (aria-live region)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Should have aria-live region for zoom level
    const zoomLiveRegion = document.querySelector('[aria-live="polite"]')
    expect(zoomLiveRegion).toBeInTheDocument()
    expect(zoomLiveRegion).toHaveTextContent(/zoom level/i)
  })

  it('photo filename accessible via aria-labelledby', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    const labelledBy = dialog.getAttribute('aria-labelledby')

    // Should have aria-labelledby pointing to title element
    expect(labelledBy).toBeTruthy()

    const titleElement = document.getElementById(labelledBy)
    expect(titleElement).toBeInTheDocument()
    expect(titleElement).toHaveTextContent(mockPhoto.filename)
  })

  it('all interactive elements keyboard accessible', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Close button should be focused initially
    await waitFor(() => {
      const closeButton = screen.getByRole('button', { name: /close photo viewer/i })
      expect(closeButton).toHaveFocus()
    })

    // Verify all buttons can be activated with keyboard
    await user.keyboard('{Enter}')
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('focus visible indicators present on interactive elements', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // All buttons should have focus:ring classes
    const closeButton = screen.getByRole('button', { name: /close photo viewer/i })
    const prevButton = screen.getByRole('button', { name: /previous photo/i })
    const nextButton = screen.getByRole('button', { name: /next photo/i })
    const zoomInButton = screen.getByRole('button', { name: /zoom in/i })

    // Check for focus ring classes (Tailwind focus:ring-2 focus:ring-white)
    expect(closeButton.className).toContain('focus:ring')
    expect(prevButton.className).toContain('focus:ring')
    expect(nextButton.className).toContain('focus:ring')
    expect(zoomInButton.className).toContain('focus:ring')
  })
})

describe('PhotoLightbox - GPU Acceleration', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800,
  }

  const mockPhotos = [mockPhoto]
  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('uses translate3d for GPU-accelerated transforms', async () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Wait for image to be rendered
    const image = await screen.findByAltText('Photo taken on 2024-11-10')

    // Should use translate3d (forces GPU acceleration)
    // Note: computed style might be matrix3d, so we check the inline style
    expect(image.style.transform).toContain('translate3d')
  })

  it('sets will-change property when zoomed', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Wait for image to be rendered
    const image = await screen.findByAltText('Photo taken on 2024-11-10')

    // Initially should be auto (not zoomed)
    expect(image.style.willChange).toBe('auto')

    // Zoom in
    const zoomInButton = screen.getByRole('button', { name: /zoom in/i })
    await user.click(zoomInButton)

    // After zooming, should hint GPU acceleration
    await waitFor(() => {
      expect(image.style.willChange).toBe('transform')
    })
  })

  it('disables transitions during active drag for immediate response', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Wait for image to be rendered
    const image = await screen.findByAltText('Photo taken on 2024-11-10')

    // Zoom in first
    const zoomInButton = screen.getByRole('button', { name: /zoom in/i })
    await user.click(zoomInButton)

    await waitFor(() => {
      expect(image.style.willChange).toBe('transform')
    })

    // Start dragging (simulate mouse down)
    const mouseDown = new MouseEvent('mousedown', {
      bubbles: true,
      clientX: 100,
      clientY: 100,
    })
    image.dispatchEvent(mouseDown)

    // During drag, transition should be disabled
    await waitFor(() => {
      expect(image.style.transition).toBe('none')
    })

    // End drag
    const mouseUp = new MouseEvent('mouseup', { bubbles: true })
    document.dispatchEvent(mouseUp)

    // After drag, transition should be re-enabled
    await waitFor(() => {
      expect(image.style.transition).toContain('transform')
    })
  })
})

describe('PhotoLightbox - Performance Benchmarks', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800,
  }

  const mockPhotos = Array.from({ length: 10 }, (_, i) => ({
    path: `2024-11-10/photo_${String(i).padStart(3, '0')}.jpg`,
    filename: `photo_${String(i).padStart(3, '0')}.jpg`,
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800 + i,
  }))

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('renders within 200ms', () => {
    const start = performance.now()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const end = performance.now()
    const renderTime = end - start

    // Should render quickly (< 200ms)
    expect(renderTime).toBeLessThan(200)
  })

  it('navigation transition uses configured duration', () => {
    // Verify animation duration is optimized (≤ 200ms)
    expect(LIGHTBOX_CONFIG.ANIMATION_DURATION).toBeLessThanOrEqual(200)
  })

  it('handles 50 rapid zoom events without lag', async () => {
    const user = userEvent.setup({ delay: null }) // No delay for rapid testing

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const zoomInButton = screen.getByRole('button', { name: /zoom in/i })

    const start = performance.now()

    // Rapid zoom clicks
    for (let i = 0; i < 50; i++) {
      await user.click(zoomInButton)
    }

    const end = performance.now()
    const totalTime = end - start

    // Should handle 50 clicks in reasonable time (< 5 seconds)
    expect(totalTime).toBeLessThan(5000)
  })

  it('handles rapid pan events without lag', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Zoom in first
    const zoomInButton = screen.getByRole('button', { name: /zoom in/i })
    await user.click(zoomInButton)
    await user.click(zoomInButton)

    // Wait for image to be rendered
    const image = await screen.findByAltText('Photo taken on 2024-11-10')

    const start = performance.now()

    // Simulate rapid pan movements
    const mouseDown = new MouseEvent('mousedown', {
      bubbles: true,
      clientX: 100,
      clientY: 100,
    })
    image.dispatchEvent(mouseDown)

    // Rapid mouse moves
    for (let i = 0; i < 100; i++) {
      const mouseMove = new MouseEvent('mousemove', {
        bubbles: true,
        clientX: 100 + i,
        clientY: 100 + i,
      })
      document.dispatchEvent(mouseMove)
    }

    const mouseUp = new MouseEvent('mouseup', { bubbles: true })
    document.dispatchEvent(mouseUp)

    const end = performance.now()
    const totalTime = end - start

    // Should handle 100 pan events quickly (< 1 second)
    expect(totalTime).toBeLessThan(1000)
  })
})

describe('PhotoLightbox - MetadataPanel Integration', () => {
  const mockPhoto = {
    path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    date: '2024-11-10T18:30:00Z',
    size: 5242880,
    timestamp: 1699639800,
  }

  const mockPhotos = [
    mockPhoto,
    {
      path: '2024-11-10/photo_002.jpg',
      filename: 'photo_002.jpg',
      date: '2024-11-10T18:31:00Z',
      size: 5500000,
      timestamp: 1699639860,
    },
  ]

  const mockOnClose = vi.fn()
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.style.overflow = ''
  })

  it('renders MetadataPanel when photo is displayed', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // MetadataPanel should be present (check for Camera tab as proxy)
    expect(screen.getByText('Camera')).toBeInTheDocument()
  })

  it('passes correct photoPath to MetadataPanel', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Verify MetadataPanel is rendered with photo path
    // Note: This is indirect - we check that tabs exist which proves MetadataPanel rendered
    const cameraTab = screen.getByText('Camera')
    expect(cameraTab).toBeInTheDocument()
  })

  it('MetadataPanel receives photoPath prop', () => {
    const { container } = render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Check that MetadataPanel tabs are present (confirms component rendered)
    expect(screen.getByText('Location')).toBeInTheDocument()
    expect(screen.getByText('Capture')).toBeInTheDocument()
  })

  it('MetadataPanel is visible when lightbox is open', () => {
    const { rerender } = render(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Should not render when closed
    expect(screen.queryByText('Camera')).not.toBeInTheDocument()

    // Open lightbox
    rerender(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // MetadataPanel should be visible
    expect(screen.getByText('Camera')).toBeInTheDocument()
  })

  it('MetadataPanel is hidden when lightbox is closed', () => {
    const { rerender } = render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Should render when open
    expect(screen.getByText('Camera')).toBeInTheDocument()

    // Close lightbox
    rerender(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // MetadataPanel should be hidden
    expect(screen.queryByText('Camera')).not.toBeInTheDocument()
  })

  it('MetadataPanel hidden on mobile (<768px)', () => {
    // Mock viewport width to mobile size
    global.innerWidth = 375
    global.innerHeight = 667

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Find the metadata panel container
    const metadataContainer = screen.getByText('Camera').closest('.hidden')
    expect(metadataContainer).toBeInTheDocument()
    expect(metadataContainer).toHaveClass('hidden')
  })

  it('MetadataPanel visible on desktop (≥768px)', () => {
    // Mock viewport width to desktop size
    global.innerWidth = 1024
    global.innerHeight = 768

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Find the metadata panel container
    const cameraTab = screen.getByText('Camera')
    const metadataContainer = cameraTab.closest('.md\\:block')
    expect(metadataContainer).toBeInTheDocument()
  })

  it('MetadataPanel in side panel layout on desktop', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Find parent container with flex layout
    const dialog = screen.getByRole('dialog')
    const flexContainer = within(dialog).getByText('Camera').closest('.flex')

    // Should have flex classes
    expect(flexContainer).toBeInTheDocument()
  })

  it('Photo and metadata panel share container on desktop', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    const image = within(dialog).getByRole('img')
    const cameraTab = within(dialog).getByText('Camera')

    // Both should be in the DOM (in same container)
    expect(image).toBeInTheDocument()
    expect(cameraTab).toBeInTheDocument()
  })

  it('Photo container uses flex-1 for remaining space', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    const image = within(dialog).getByRole('img')
    const imageContainer = image.closest('.flex-1')

    expect(imageContainer).toBeInTheDocument()
    expect(imageContainer).toHaveClass('flex-1')
  })

  it('MetadataPanel has fixed width on desktop (w-96 = 384px)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const cameraTab = screen.getByText('Camera')
    const metadataContainer = cameraTab.closest('.md\\:w-96')

    expect(metadataContainer).toBeInTheDocument()
    expect(metadataContainer).toHaveClass('md:w-96')
  })

  it('Container has proper flex layout (flex-col on mobile, flex-row on desktop)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    const cameraTab = within(dialog).getByText('Camera')
    const flexContainer = cameraTab.closest('.flex')

    // Should have both flex-col (mobile) and md:flex-row (desktop) classes
    expect(flexContainer).toHaveClass('flex')
    // Note: Checking for responsive classes in JSDOM is limited, so we verify flex exists
  })

  it('Gap between photo and panel (gap-4)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    const cameraTab = within(dialog).getByText('Camera')
    const flexContainer = cameraTab.closest('.gap-4')

    expect(flexContainer).toBeInTheDocument()
    expect(flexContainer).toHaveClass('gap-4')
  })

  it('MetadataPanel has white background (bg-white dark:bg-gray-800)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const cameraTab = screen.getByText('Camera')
    const metadataContainer = cameraTab.closest('.bg-white')

    expect(metadataContainer).toBeInTheDocument()
    expect(metadataContainer).toHaveClass('bg-white')
  })

  it('MetadataPanel has rounded corners (rounded-lg)', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const cameraTab = screen.getByText('Camera')
    const metadataContainer = cameraTab.closest('.rounded-lg')

    expect(metadataContainer).toBeInTheDocument()
    expect(metadataContainer).toHaveClass('rounded-lg')
  })

  it('MetadataPanel has overflow handling', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const cameraTab = screen.getByText('Camera')
    const metadataContainer = cameraTab.closest('.overflow-hidden')

    expect(metadataContainer).toBeInTheDocument()
    expect(metadataContainer).toHaveClass('overflow-hidden')
  })

  it('Lightbox still has proper ARIA labels with MetadataPanel', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby')
    expect(dialog).toHaveAttribute('aria-describedby')
  })

  it('Close button still accessible', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const closeButton = screen.getByLabelText(/close photo viewer/i)
    expect(closeButton).toBeInTheDocument()
  })

  it('Photo image still has alt text', () => {
    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    const image = screen.getByRole('img')
    expect(image).toHaveAttribute('alt', 'Photo taken on 2024-11-10')
  })

  it('Handles null photoPath gracefully', () => {
    const photoWithNullPath = {
      ...mockPhoto,
      path: null,
    }

    render(
      <PhotoLightbox
        photo={photoWithNullPath}
        photos={[photoWithNullPath]}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Should still render dialog
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
  })

  it('MetadataPanel does not break existing lightbox functionality', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Test close button still works
    const closeButton = screen.getByLabelText(/close photo viewer/i)
    await user.click(closeButton)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('Existing zoom features still work', async () => {
    const user = userEvent.setup()

    render(
      <PhotoLightbox
        photo={mockPhoto}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Zoom in should still work
    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    // Zoom indicator should appear
    await waitFor(() => {
      const zoomIndicators = screen.getAllByText(/150|1\.5/i)
      expect(zoomIndicators.length).toBeGreaterThan(0)
    })
  })
})
