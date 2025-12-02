import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import QuickTagButton from '../QuickTagButton'
import useSidecarMetadata from '../../../hooks/useSidecarMetadata'

// Mock useSidecarMetadata
vi.mock('../../../hooks/useSidecarMetadata', () => ({
  default: vi.fn()
}))

// Mock QuickTagDropdown
vi.mock('../QuickTagDropdown', () => ({
  default: ({ isOpen, onClose, filename, anchorEl }) =>
    isOpen ? (
      <div
        data-testid="quick-tag-dropdown"
        data-filename={filename}
        data-has-anchor={!!anchorEl}
      >
        <button onClick={onClose}>Close Dropdown</button>
      </div>
    ) : null
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('QuickTagButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock: photo with 2 tags
    useSidecarMetadata.mockReturnValue({
      data: { tags: ['moth', 'nocturnal'] },
      isLoading: false,
    })
  })

  // === Rendering ===
  it('renders tag icon button', () => {
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button', { name: /add tags to photo/i })
    expect(button).toBeInTheDocument()

    // TagIcon should be present (heroicons renders as svg)
    const svg = button.querySelector('svg')
    expect(svg).toBeInTheDocument()
  })

  it('shows tag count badge when photo has tags', () => {
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const badge = screen.getByText('2')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-blue-500', 'text-white')
  })

  it('does not show badge when no tags', () => {
    useSidecarMetadata.mockReturnValue({
      data: { tags: [] },
      isLoading: false,
    })

    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    expect(button.textContent).toBe('') // No badge text
  })

  it('applies custom className', () => {
    render(
      <QuickTagButton filename="test.jpg" className="custom-class" />,
      { wrapper: createWrapper() }
    )

    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
  })

  // === Interactions ===
  it('opens dropdown on click', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    await user.click(button)

    const dropdown = screen.getByTestId('quick-tag-dropdown')
    expect(dropdown).toBeInTheDocument()
    expect(dropdown).toHaveAttribute('data-filename', 'test.jpg')
  })

  it('closes dropdown when onClose called', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    expect(screen.getByTestId('quick-tag-dropdown')).toBeInTheDocument()

    // Close dropdown via the dropdown's close button
    const closeButton = screen.getByText('Close Dropdown')
    await user.click(closeButton)

    await waitFor(() => {
      expect(screen.queryByTestId('quick-tag-dropdown')).not.toBeInTheDocument()
    })
  })

  it('stops event propagation on click', async () => {
    const parentClickHandler = vi.fn()
    const user = userEvent.setup()

    const { container } = render(
      <div onClick={parentClickHandler}>
        <QuickTagButton filename="test.jpg" />
      </div>,
      { wrapper: createWrapper() }
    )

    const button = screen.getByRole('button')
    await user.click(button)

    expect(parentClickHandler).not.toHaveBeenCalled()
  })

  it('calls onDropdownOpenChange when dropdown opens', async () => {
    const onDropdownOpenChange = vi.fn()
    const user = userEvent.setup()

    render(
      <QuickTagButton filename="test.jpg" onDropdownOpenChange={onDropdownOpenChange} />,
      { wrapper: createWrapper() }
    )

    const button = screen.getByRole('button')
    await user.click(button)

    expect(onDropdownOpenChange).toHaveBeenCalledWith(true)
  })

  it('calls onDropdownOpenChange when dropdown closes', async () => {
    const onDropdownOpenChange = vi.fn()
    const user = userEvent.setup()

    render(
      <QuickTagButton filename="test.jpg" onDropdownOpenChange={onDropdownOpenChange} />,
      { wrapper: createWrapper() }
    )

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    expect(onDropdownOpenChange).toHaveBeenCalledWith(true)
    onDropdownOpenChange.mockClear()

    // Close dropdown
    const closeButton = screen.getByText('Close Dropdown')
    await user.click(closeButton)

    await waitFor(() => {
      expect(onDropdownOpenChange).toHaveBeenCalledWith(false)
    })
  })

  // === Visual states ===
  it('shows active state when dropdown is open', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')

    // Initial state
    expect(button).toHaveClass('bg-white/90')
    expect(button).not.toHaveClass('bg-blue-500')

    // Open dropdown
    await user.click(button)

    expect(button).toHaveClass('bg-blue-500', 'text-white')
    expect(button).not.toHaveClass('bg-white/90')
  })

  it('changes icon color when active', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')

    // Initial: dark text
    expect(button).toHaveClass('text-gray-600')

    // Active: white text
    await user.click(button)
    expect(button).toHaveClass('text-white')
  })

  // === Accessibility ===
  it('has aria-label describing action', () => {
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Add tags to photo (2 tags)')
  })

  it('has aria-expanded when dropdown open', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')

    // Initially false
    expect(button).toHaveAttribute('aria-expanded', 'false')

    // True when open
    await user.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
  })

  it('has aria-haspopup attribute', () => {
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-haspopup', 'dialog')
  })

  // === Loading state ===
  it('shows loading indicator while fetching tags', () => {
    useSidecarMetadata.mockReturnValue({
      data: null,
      isLoading: true,
    })

    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')

    // Loading indicator should be present (look for animate-pulse)
    const loadingIndicator = button.querySelector('.animate-pulse')
    expect(loadingIndicator).toBeInTheDocument()

    // Badge should NOT be shown during loading
    expect(button.textContent).toBe('')
  })

  // === Edge cases ===
  it('handles zero tags gracefully', () => {
    useSidecarMetadata.mockReturnValue({
      data: { tags: [] },
      isLoading: false,
    })

    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Add tags to photo')

    // No badge
    expect(button.textContent).toBe('')
  })

  it('passes correct filename to dropdown', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="my-photo.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    await user.click(button)

    const dropdown = screen.getByTestId('quick-tag-dropdown')
    expect(dropdown).toHaveAttribute('data-filename', 'my-photo.jpg')
  })

  it('passes anchor element to dropdown', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    await user.click(button)

    const dropdown = screen.getByTestId('quick-tag-dropdown')
    expect(dropdown).toHaveAttribute('data-has-anchor', 'true')
  })

  it('handles null/undefined tags array', () => {
    useSidecarMetadata.mockReturnValue({
      data: null,
      isLoading: false,
    })

    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
    expect(button.textContent).toBe('') // No badge
  })

  it('toggles dropdown on repeated clicks', async () => {
    const user = userEvent.setup()
    render(<QuickTagButton filename="test.jpg" />, { wrapper: createWrapper() })

    const button = screen.getByRole('button')

    // Click 1: Open
    await user.click(button)
    expect(screen.getByTestId('quick-tag-dropdown')).toBeInTheDocument()

    // Click 2: Close
    await user.click(button)
    await waitFor(() => {
      expect(screen.queryByTestId('quick-tag-dropdown')).not.toBeInTheDocument()
    })

    // Click 3: Open again
    await user.click(button)
    expect(screen.getByTestId('quick-tag-dropdown')).toBeInTheDocument()
  })
})
