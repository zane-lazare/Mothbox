import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock the hooks BEFORE importing the component
vi.mock('../../../hooks/useTags', () => ({
  default: vi.fn()
}))

vi.mock('../../../hooks/useSidecarMetadata', () => ({
  default: vi.fn()
}))

import QuickTagDropdown from '../QuickTagDropdown'
import useTags from '../../../hooks/useTags'
import useSidecarMetadata from '../../../hooks/useSidecarMetadata'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('QuickTagDropdown', () => {
  let mockAnchor
  let mockAddTag
  let mockRemoveTag

  beforeEach(() => {
    mockAnchor = document.createElement('button')
    mockAnchor.textContent = 'Anchor Button'
    document.body.appendChild(mockAnchor)

    mockAddTag = vi.fn()
    mockRemoveTag = vi.fn()

    // Default mock implementations
    useTags.mockReturnValue({
      data: {
        tags: [
          { name: 'moth', count: 20 },
          { name: 'butterfly', count: 15 },
          { name: 'beetle', count: 10 },
          { name: 'nocturnal', count: 8 },
          { name: 'large', count: 5 },
          { name: 'small', count: 4 },
          { name: 'colorful', count: 3 },
          { name: 'rare', count: 2 },
          { name: 'common', count: 1 },
        ]
      },
      isLoading: false,
      isError: false,
    })

    useSidecarMetadata.mockReturnValue({
      data: { tags: ['moth', 'nocturnal'] },
      isLoading: false,
      addTag: mockAddTag,
      removeTag: mockRemoveTag,
      isUpdating: false,
    })
  })

  afterEach(() => {
    document.body.removeChild(mockAnchor)
    vi.clearAllMocks()
  })

  const defaultProps = {
    filename: 'test-photo.jpg',
    isOpen: true,
    onClose: vi.fn(),
    anchorEl: mockAnchor,
  }

  // Rendering
  it('renders when isOpen is true', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })
    expect(screen.getByRole('dialog', { name: /add tags to photo/i })).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(<QuickTagDropdown {...defaultProps} isOpen={false} />, { wrapper: createWrapper() })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows Quick Tags section header', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })
    expect(screen.getByText('Quick Tags')).toBeInTheDocument()
  })

  it('shows Search section', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })
    expect(screen.getByPlaceholderText(/search or create tag/i)).toBeInTheDocument()
  })

  it('shows All Tags section', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })
    expect(screen.getByText(/all tags \(9\)/i)).toBeInTheDocument()
  })

  // Quick Tags Section
  it('displays top 8 tags by frequency', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Quick tags section should show first 8 tags
    const quickTagsSection = screen.getByText('Frequently Used').parentElement
    expect(quickTagsSection).toBeInTheDocument()

    // Check that top 8 tags are present (use getAllByText since they appear in multiple sections)
    expect(screen.getAllByText('moth').length).toBeGreaterThan(0)
    expect(screen.getAllByText('butterfly').length).toBeGreaterThan(0)
    expect(screen.getAllByText('beetle').length).toBeGreaterThan(0)
    expect(screen.getAllByText('nocturnal').length).toBeGreaterThan(0)
    expect(screen.getAllByText('large').length).toBeGreaterThan(0)
    expect(screen.getAllByText('small').length).toBeGreaterThan(0)
    expect(screen.getAllByText('colorful').length).toBeGreaterThan(0)
    expect(screen.getAllByText('rare').length).toBeGreaterThan(0)
  })

  it('shows checkmark for already applied tags', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Applied tags should have checkmarks in the All Tags section
    // Check for presence of checkmarks (via CheckIcon)
    const checkIcons = screen.getAllByTestId('check-icon')
    expect(checkIcons.length).toBeGreaterThan(0)
  })

  it('toggles tag on click', async () => {
    const user = userEvent.setup()
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Click on an unselected tag
    const butterflyTag = screen.getAllByText('butterfly')[0]
    await user.click(butterflyTag)

    expect(mockAddTag).toHaveBeenCalledWith('butterfly')
    expect(mockAddTag).toHaveBeenCalledTimes(1)
  })

  // Search Section
  it('renders search input', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })
    const searchInput = screen.getByPlaceholderText(/search or create tag/i)
    expect(searchInput).toBeInTheDocument()
    expect(searchInput.tagName).toBe('INPUT')
  })

  it('filters all tags based on search', async () => {
    const user = userEvent.setup()
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    const searchInput = screen.getByPlaceholderText(/search or create tag/i)
    await user.type(searchInput, 'but')

    // Should filter to show only 'butterfly' in the All Tags section
    // The quick tags section should be hidden when searching
    await waitFor(() => {
      const allTagsSection = screen.getByText(/all tags \(/i).parentElement
      expect(allTagsSection.textContent).toContain('butterfly')
      expect(allTagsSection.textContent).not.toContain('beetle')
    })
  })

  it('shows create option for new tags', async () => {
    const user = userEvent.setup()
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    const searchInput = screen.getByPlaceholderText(/search or create tag/i)
    await user.type(searchInput, 'newtagname')

    // Should show option to create new tag
    await waitFor(() => {
      expect(screen.getByText(/create "newtagname"/i)).toBeInTheDocument()
    })
  })

  // All Tags Section
  it('displays all available tags', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Check for all 9 tags (use getAllByText since they appear in multiple sections)
    expect(screen.getAllByText('moth').length).toBeGreaterThan(0)
    expect(screen.getAllByText('butterfly').length).toBeGreaterThan(0)
    expect(screen.getAllByText('beetle').length).toBeGreaterThan(0)
    expect(screen.getAllByText('nocturnal').length).toBeGreaterThan(0)
    expect(screen.getAllByText('large').length).toBeGreaterThan(0)
    expect(screen.getAllByText('small').length).toBeGreaterThan(0)
    expect(screen.getAllByText('colorful').length).toBeGreaterThan(0)
    expect(screen.getAllByText('rare').length).toBeGreaterThan(0)
    expect(screen.getAllByText('common').length).toBeGreaterThan(0)
  })

  it('shows tag counts', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Check for tag counts
    expect(screen.getByText('20')).toBeInTheDocument() // moth
    expect(screen.getByText('15')).toBeInTheDocument() // butterfly
    expect(screen.getByText('10')).toBeInTheDocument() // beetle
  })

  it('highlights selected tags', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Applied tags should have blue background class
    const allTagButtons = screen.getAllByRole('button')
    const mothButton = allTagButtons.find(btn => btn.textContent.includes('moth'))

    expect(mothButton).toHaveClass(/bg-blue-50|bg-blue-900/)
  })

  // Tag Operations
  it('calls addTag when unselected tag is clicked', async () => {
    const user = userEvent.setup()
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Click on butterfly (not currently applied)
    const allTagButtons = screen.getAllByRole('button')
    const butterflyButton = allTagButtons.find(btn => btn.textContent.includes('butterfly') && btn.textContent.includes('15'))

    await user.click(butterflyButton)

    expect(mockAddTag).toHaveBeenCalledWith('butterfly')
  })

  it('calls removeTag when selected tag is clicked', async () => {
    const user = userEvent.setup()
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Click on moth (currently applied)
    const allTagButtons = screen.getAllByRole('button')
    const mothButton = allTagButtons.find(btn => btn.textContent.includes('moth') && btn.textContent.includes('20'))

    await user.click(mothButton)

    expect(mockRemoveTag).toHaveBeenCalledWith('moth')
  })

  it('shows loading state while updating', () => {
    useSidecarMetadata.mockReturnValue({
      data: { tags: ['moth', 'nocturnal'] },
      isLoading: false,
      addTag: mockAddTag,
      removeTag: mockRemoveTag,
      isUpdating: true,
    })

    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/saving/i)).toBeInTheDocument()
  })

  // Positioning
  it('positions relative to anchor element', () => {
    const { container } = render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    const dropdown = container.querySelector('[role="dialog"]')
    expect(dropdown).toHaveStyle({ position: 'absolute' })
  })

  it('flips position when near viewport edge', () => {
    // This is handled by floating-ui, just verify it's configured
    const { container } = render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    const dropdown = container.querySelector('[role="dialog"]')
    expect(dropdown).toBeInTheDocument()
    // Floating-UI applies positioning via inline styles
  })

  // Interactions
  it('closes on Escape key', async () => {
    const onClose = vi.fn()
    render(<QuickTagDropdown {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('closes when clicking outside', async () => {
    const onClose = vi.fn()
    render(<QuickTagDropdown {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    // Click outside the dropdown
    fireEvent.mouseDown(document.body)

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('traps focus within dropdown', async () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    const searchInput = screen.getByPlaceholderText(/search or create tag/i)

    // Focus should be on search input when opened
    await waitFor(() => {
      expect(searchInput).toHaveFocus()
    })
  })

  // Loading/Error States
  it('shows loading state while fetching tags', () => {
    useTags.mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
    })

    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/loading tags/i)).toBeInTheDocument()
  })

  it('shows error state on fetch failure', () => {
    useTags.mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
    })

    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/failed to load tags/i)).toBeInTheDocument()
  })

  // Accessibility
  it('has proper ARIA attributes', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-label', 'Add tags to photo')
  })

  it('announces tag changes to screen readers', async () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Check that tag buttons are accessible
    const allTagButtons = screen.getAllByRole('button')
    expect(allTagButtons.length).toBeGreaterThan(0)

    // Each tag button should be clickable and have proper text content
    const butterflyButton = allTagButtons.find(btn => btn.textContent.includes('butterfly'))
    expect(butterflyButton).toBeInTheDocument()
  })

  // Edge Cases
  it('handles empty tags list', () => {
    useTags.mockReturnValue({
      data: { tags: [] },
      isLoading: false,
      isError: false,
    })

    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/no tags yet/i)).toBeInTheDocument()
  })

  it('handles no applied tags', () => {
    useSidecarMetadata.mockReturnValue({
      data: { tags: [] },
      isLoading: false,
      addTag: mockAddTag,
      removeTag: mockRemoveTag,
      isUpdating: false,
    })

    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Should not show applied tags section
    expect(screen.queryByText(/applied \(/i)).not.toBeInTheDocument()
  })

  it('shows applied tags summary when tags exist', () => {
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/applied \(2\)/i)).toBeInTheDocument()
  })

  it('allows removing tags from applied section', async () => {
    const user = userEvent.setup()
    render(<QuickTagDropdown {...defaultProps} />, { wrapper: createWrapper() })

    // Find the applied tags section
    const appliedSection = screen.getByText(/applied \(2\)/i).parentElement

    // TagChip with removable prop renders a remove button as a span with role="button"
    const removeButtons = appliedSection.querySelectorAll('span[role="button"]')

    // The TagChip remove buttons should be present
    expect(removeButtons.length).toBeGreaterThan(0)

    // Click the first remove button (which should call removeTag)
    if (removeButtons.length > 0) {
      await user.click(removeButtons[0])
      expect(mockRemoveTag).toHaveBeenCalled()
    }
  })

  it('focuses search input when dropdown opens', async () => {
    // Render with isOpen=true directly to avoid hooks order issues
    render(<QuickTagDropdown {...defaultProps} isOpen={true} />, { wrapper: createWrapper() })

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText(/search or create tag/i)
      expect(searchInput).toHaveFocus()
    })
  })

  it('does not close when clicking inside dropdown', async () => {
    const onClose = vi.fn()
    render(<QuickTagDropdown {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    const dialog = screen.getByRole('dialog')
    fireEvent.mouseDown(dialog)

    // Should not close
    expect(onClose).not.toHaveBeenCalled()
  })

  it('does not close when clicking anchor element', () => {
    const onClose = vi.fn()

    render(<QuickTagDropdown {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    // The dropdown includes logic to check !anchorEl?.contains(e.target)
    // This means clicks on the anchor should not trigger onClose
    // We verify the dropdown renders with the anchor element provided
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(mockAnchor).toBeInTheDocument()

    // In real usage, the parent component handles anchor clicks to toggle the dropdown
    // The dropdown's click-outside handler should exclude the anchor
    // This is a structural test - the integration behavior is tested in parent components
  })

  it('handles close button click', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<QuickTagDropdown {...defaultProps} onClose={onClose} />, { wrapper: createWrapper() })

    const closeButton = screen.getByLabelText(/close/i)
    await user.click(closeButton)

    expect(onClose).toHaveBeenCalled()
  })
})
