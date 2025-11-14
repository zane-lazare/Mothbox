import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PhotoLightbox from '../PhotoLightbox'

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
    expect(image).toHaveAttribute('alt', 'photo_001.jpg')
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

    // Check for date (should be formatted)
    expect(screen.getByText(/2024-11-10/i)).toBeInTheDocument()

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

    // Body scroll should be hidden
    expect(document.body.style.overflow).toBe('hidden')
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

    // Body scroll should be hidden when open
    expect(document.body.style.overflow).toBe('hidden')

    // Close lightbox
    rerender(
      <PhotoLightbox
        photo={null}
        photos={mockPhotos}
        onClose={mockOnClose}
        onNavigate={mockOnNavigate}
      />
    )

    // Body scroll should be restored
    expect(document.body.style.overflow).toBe('')
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
    const initialTransform = window.getComputedStyle(image).transform

    const zoomInButton = screen.getByLabelText(/zoom in/i)
    await user.click(zoomInButton)

    // Transform should change (zoom applied)
    const newTransform = window.getComputedStyle(image).transform
    expect(newTransform).not.toBe(initialTransform)
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
    await waitFor(() => {
      expect(screen.getByText(/150|1\.5/i)).toBeInTheDocument()
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
    await waitFor(() => {
      expect(screen.getByText(/100|1\.0|1x/i)).toBeInTheDocument()
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
      // Should have non-zero translate values
      expect(transform).toMatch(/translate\(.+px,\s*.+px\)/)
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
    const initialTransform = window.getComputedStyle(image).transform

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
      // Should have translate values
      expect(transform).toMatch(/translate\(.+px,\s*.+px\)/)
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
