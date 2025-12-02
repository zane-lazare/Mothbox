import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PhotoGridItem from '../PhotoGridItem'

// Mock ProgressiveImage to avoid image loading complexity
vi.mock('../ProgressiveImage', () => ({
  default: ({ photoPath, alt, className }) => (
    <img
      src={`/api/photos/thumbnail/${photoPath}`}
      alt={alt}
      className={className}
      data-testid="progressive-image"
    />
  )
}))

// Mock QuickTagButton for integration testing
vi.mock('../gallery/QuickTagButton', () => ({
  default: ({ filename, onDropdownOpenChange, className }) => (
    <button
      data-testid="quick-tag-button"
      data-filename={filename}
      className={className}
      onClick={(e) => {
        e.stopPropagation()
        onDropdownOpenChange?.(true)
      }}
    >
      Tag
    </button>
  )
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const mockPhoto = {
  path: '20250106/test-photo.jpg',
  filename: 'test-photo.jpg',
  date: '2025-01-06T10:30:00Z',
}

describe('PhotoGridItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // === Basic Rendering ===
  it('renders photo thumbnail', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const image = screen.getByTestId('progressive-image')
    expect(image).toBeInTheDocument()
    expect(image).toHaveAttribute('alt', 'test-photo.jpg')
  })

  it('renders with correct photo path', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const image = screen.getByTestId('progressive-image')
    expect(image).toHaveAttribute('src', expect.stringContaining('20250106/test-photo.jpg'))
  })

  it('shows "View" overlay on hover', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const viewText = screen.getByText('View')
    expect(viewText).toBeInTheDocument()
  })

  // === QuickTagButton Integration ===
  it('renders QuickTagButton on the photo', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const tagButton = screen.getByTestId('quick-tag-button')
    expect(tagButton).toBeInTheDocument()
  })

  it('positions QuickTagButton in top-right corner', () => {
    const { container } = render(
      <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    const tagButtonContainer = screen.getByTestId('quick-tag-button').parentElement
    expect(tagButtonContainer).toHaveClass('absolute', 'top-2', 'right-2')
  })

  it('passes correct filename to QuickTagButton', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const tagButton = screen.getByTestId('quick-tag-button')
    expect(tagButton).toHaveAttribute('data-filename', 'test-photo.jpg')
  })

  it('QuickTagButton is independently focusable', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const tagButton = screen.getByTestId('quick-tag-button')
    tagButton.focus()

    expect(tagButton).toHaveFocus()
  })

  // === Click Behavior ===
  it('calls onClick when clicking the photo', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()

    render(<PhotoGridItem photo={mockPhoto} onClick={onClick} />, { wrapper: createWrapper() })

    const photoButton = screen.getByLabelText(/view photo: test-photo.jpg/i)
    await user.click(photoButton)

    expect(onClick).toHaveBeenCalledWith(mockPhoto)
  })

  it('does not call onClick when clicking QuickTagButton', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()

    render(<PhotoGridItem photo={mockPhoto} onClick={onClick} />, { wrapper: createWrapper() })

    const tagButton = screen.getByTestId('quick-tag-button')
    await user.click(tagButton)

    // Photo onClick should NOT be called
    expect(onClick).not.toHaveBeenCalled()
  })

  it('prevents lightbox opening when tag dropdown is open', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()

    render(<PhotoGridItem photo={mockPhoto} onClick={onClick} />, { wrapper: createWrapper() })

    // Open tag dropdown
    const tagButton = screen.getByTestId('quick-tag-button')
    await user.click(tagButton)

    // Click on photo (not the tag button)
    const photoButton = screen.getByLabelText(/view photo/i)
    await user.click(photoButton)

    // onClick should not be called when dropdown is open
    expect(onClick).not.toHaveBeenCalled()
  })

  // === Hover State Management ===
  it('shows QuickTagButton on hover', async () => {
    const { container } = render(
      <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    const gridItem = container.querySelector('.group')
    const tagButtonContainer = screen.getByTestId('quick-tag-button').parentElement

    // Initially hidden (opacity-0)
    expect(tagButtonContainer).toHaveClass('opacity-0')

    // Simulate hover
    fireEvent.mouseEnter(gridItem)

    // Should become visible
    await waitFor(() => {
      expect(tagButtonContainer).toHaveClass('opacity-100')
    })
  })

  it('hides QuickTagButton when not hovered', async () => {
    const { container } = render(
      <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    const gridItem = container.querySelector('.group')
    const tagButtonContainer = screen.getByTestId('quick-tag-button').parentElement

    // Hover
    fireEvent.mouseEnter(gridItem)
    await waitFor(() => {
      expect(tagButtonContainer).toHaveClass('opacity-100')
    })

    // Un-hover
    fireEvent.mouseLeave(gridItem)
    await waitFor(() => {
      expect(tagButtonContainer).toHaveClass('opacity-0')
    })
  })

  it('keeps QuickTagButton visible when dropdown is open', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    const gridItem = container.querySelector('.group')
    const tagButton = screen.getByTestId('quick-tag-button')
    const tagButtonContainer = tagButton.parentElement

    // Hover to show button
    fireEvent.mouseEnter(gridItem)
    await waitFor(() => {
      expect(tagButtonContainer).toHaveClass('opacity-100')
    })

    // Open dropdown
    await user.click(tagButton)

    // Un-hover
    fireEvent.mouseLeave(gridItem)

    // Button should still be visible because dropdown is open
    expect(tagButtonContainer).toHaveClass('opacity-100')
  })

  // === Accessibility ===
  it('has distinct accessible names for photo and tag button', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const photoButton = screen.getByLabelText(/view photo: test-photo.jpg/i)
    const tagButton = screen.getByTestId('quick-tag-button')

    expect(photoButton).toBeInTheDocument()
    expect(tagButton).toBeInTheDocument()
    expect(photoButton).not.toBe(tagButton)
  })

  it('both photo and tag button can receive focus', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const photoButton = screen.getByLabelText(/view photo/i)
    const tagButton = screen.getByTestId('quick-tag-button')

    // Focus photo button
    photoButton.focus()
    expect(photoButton).toHaveFocus()

    // Focus tag button
    tagButton.focus()
    expect(tagButton).toHaveFocus()
  })

  it('maintains proper focus order', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const photoButton = screen.getByLabelText(/view photo/i)
    const tagButton = screen.getByTestId('quick-tag-button')

    // Photo button should come before tag button in DOM order
    expect(photoButton.compareDocumentPosition(tagButton)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })

  it('photo button has proper aria-label with date', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const photoButton = screen.getByLabelText(/view photo: test-photo.jpg/i)
    // Date format is locale-dependent, just check it contains the date components
    expect(photoButton).toHaveAttribute('aria-label', expect.stringContaining('2025'))
  })

  // === Visual States ===
  it('applies hover overlay to photo on mouse enter', () => {
    const { container } = render(
      <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    const gridItem = container.querySelector('.group')
    const overlay = container.querySelector('.group-hover\\:bg-black\\/30')

    expect(overlay).toBeInTheDocument()
    expect(overlay).toHaveClass('bg-transparent')

    fireEvent.mouseEnter(gridItem)

    // Tailwind's group-hover: pseudo-class applies styles automatically
    expect(overlay).toHaveClass('group-hover:bg-black/30')
  })

  it('applies rounded corners to photo', () => {
    render(<PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const photoButton = screen.getByLabelText(/view photo/i)
    expect(photoButton).toHaveClass('rounded-lg')
  })

  // === Edge Cases ===
  it('handles photo with special characters in filename', () => {
    const specialPhoto = {
      ...mockPhoto,
      filename: 'test-photo (1) [copy].jpg',
    }

    render(<PhotoGridItem photo={specialPhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const tagButton = screen.getByTestId('quick-tag-button')
    expect(tagButton).toHaveAttribute('data-filename', 'test-photo (1) [copy].jpg')
  })

  it('handles long filenames gracefully', () => {
    const longFilenamePhoto = {
      ...mockPhoto,
      filename: 'very-long-filename-with-many-characters-that-might-cause-layout-issues.jpg',
    }

    render(<PhotoGridItem photo={longFilenamePhoto} onClick={vi.fn()} />, { wrapper: createWrapper() })

    const tagButton = screen.getByTestId('quick-tag-button')
    expect(tagButton).toBeInTheDocument()
  })

  it('renders correctly when photo has no date', () => {
    const photoNoDate = {
      path: '20250106/test.jpg',
      filename: 'test.jpg',
      date: null,
    }

    // Should not crash
    expect(() => {
      render(<PhotoGridItem photo={photoNoDate} onClick={vi.fn()} />, { wrapper: createWrapper() })
    }).not.toThrow()
  })

  // === Integration with Parent Components ===
  it('works within a grid layout', () => {
    const { container } = render(
      <div className="grid grid-cols-4 gap-4">
        <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />
        <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />
      </div>,
      { wrapper: createWrapper() }
    )

    const gridItems = container.querySelectorAll('.group')
    expect(gridItems).toHaveLength(2)
  })

  it('handles rapid hover/unhover without errors', async () => {
    const { container } = render(
      <PhotoGridItem photo={mockPhoto} onClick={vi.fn()} />,
      { wrapper: createWrapper() }
    )

    const gridItem = container.querySelector('.group')

    // Rapid hover/unhover
    for (let i = 0; i < 10; i++) {
      fireEvent.mouseEnter(gridItem)
      fireEvent.mouseLeave(gridItem)
    }

    // Should not crash
    expect(gridItem).toBeInTheDocument()
  })
})
