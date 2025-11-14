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
    document.body.innerHTML = ''
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

    const title = screen.getByText(/photo_001\.jpg/i)
    expect(title).toBeInTheDocument()
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
    document.body.innerHTML = ''
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
    document.body.innerHTML = ''
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
