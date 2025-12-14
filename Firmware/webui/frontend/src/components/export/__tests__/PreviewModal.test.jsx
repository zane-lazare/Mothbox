import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PreviewModal from '../PreviewModal'

// Mock clipboard API
Object.defineProperty(navigator, 'clipboard', {
  writable: true,
  value: {
    writeText: vi.fn().mockResolvedValue(undefined)
  }
})

describe('PreviewModal', () => {
  const mockOnClose = vi.fn()

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    previewData: {
      format: 'json',
      data: [
        {
          filename: 'photo1.jpg',
          tags: ['moth', 'night'],
          latitude: 37.7749
        },
        {
          filename: 'photo2.jpg',
          tags: ['butterfly'],
          latitude: 37.7750
        }
      ]
    },
    format: 'json'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not render when isOpen is false', () => {
    render(<PreviewModal {...defaultProps} isOpen={false} />)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('renders modal when isOpen is true', () => {
    render(<PreviewModal {...defaultProps} />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('displays preview data in modal', () => {
    render(<PreviewModal {...defaultProps} />)

    // Should show modal content with data
    const modalContent = screen.getByTestId('modal-content')
    expect(modalContent).toBeInTheDocument()
    expect(modalContent.textContent).toContain('photo1.jpg')
  })

  it('calls onClose when close button is clicked', () => {
    render(<PreviewModal {...defaultProps} />)

    const closeButton = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('calls onClose when backdrop is clicked', () => {
    render(<PreviewModal {...defaultProps} />)

    const backdrop = screen.getByTestId('modal-backdrop')
    fireEvent.click(backdrop)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('does not close when modal content is clicked', () => {
    render(<PreviewModal {...defaultProps} />)

    const modalContent = screen.getByRole('dialog')
    fireEvent.click(modalContent)

    expect(mockOnClose).not.toHaveBeenCalled()
  })

  it('calls onClose when Escape key is pressed', () => {
    render(<PreviewModal {...defaultProps} />)

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('renders tab bar for format switching', () => {
    render(<PreviewModal {...defaultProps} />)

    expect(screen.getByRole('tab', { name: /json/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /csv/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /darwin core/i })).toBeInTheDocument()
  })

  it('switches between tabs', () => {
    render(<PreviewModal {...defaultProps} />)

    const jsonTab = screen.getByRole('tab', { name: /json/i })
    const csvTab = screen.getByRole('tab', { name: /csv/i })

    // Initially on JSON tab
    expect(jsonTab).toHaveAttribute('aria-selected', 'true')

    // Click CSV tab
    fireEvent.click(csvTab)

    expect(csvTab).toHaveAttribute('aria-selected', 'true')
    expect(jsonTab).toHaveAttribute('aria-selected', 'false')
  })

  it('displays CSV format correctly', () => {
    const csvPreviewData = {
      format: 'csv',
      headers: ['filename', 'tags', 'latitude'],
      data: [
        { filename: 'photo1.jpg', tags: ['moth'], latitude: 37.7749 }
      ]
    }

    render(<PreviewModal {...defaultProps} previewData={csvPreviewData} />)

    // Switch to CSV tab
    const csvTab = screen.getByRole('tab', { name: /csv/i })
    fireEvent.click(csvTab)

    // Should show CSV table
    expect(screen.getByText(/filename/)).toBeInTheDocument()
    expect(screen.getByText(/tags/)).toBeInTheDocument()
    expect(screen.getByText(/photo1.jpg/)).toBeInTheDocument()
  })

  it('copy button works', async () => {
    render(<PreviewModal {...defaultProps} />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    fireEvent.click(copyButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalled()

    // Should show success message
    const successMessage = await screen.findByText(/copied/i)
    expect(successMessage).toBeInTheDocument()
  })

  it('handles copy error gracefully', async () => {
    navigator.clipboard.writeText.mockRejectedValueOnce(new Error('Clipboard error'))

    render(<PreviewModal {...defaultProps} />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    fireEvent.click(copyButton)

    const errorMessage = await screen.findByText(/failed to copy/i)
    expect(errorMessage).toBeInTheDocument()
  })

  it('renders with full-screen layout', () => {
    render(<PreviewModal {...defaultProps} />)

    const modal = screen.getByRole('dialog')
    expect(modal).toHaveClass('max-w-6xl') // Large modal
  })

  it('has scrollable content area', () => {
    render(<PreviewModal {...defaultProps} />)

    const contentArea = screen.getByTestId('modal-content')
    expect(contentArea).toHaveClass('overflow-auto')
  })

  it('renders portal to document.body', () => {
    render(<PreviewModal {...defaultProps} />)

    // Modal should be rendered as direct child of body
    const modal = screen.getByRole('dialog')
    expect(modal.parentElement.parentElement).toBe(document.body)
  })

  it('prevents body scroll when open', () => {
    render(<PreviewModal {...defaultProps} />)

    // Should add overflow-hidden to body
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('restores body scroll when closed', () => {
    const { unmount } = render(<PreviewModal {...defaultProps} />)

    // Initially hidden
    expect(document.body.style.overflow).toBe('hidden')

    // Unmount modal
    unmount()

    // Should restore scroll
    expect(document.body.style.overflow).toBe('')
  })

  it('handles empty preview data', () => {
    render(
      <PreviewModal
        {...defaultProps}
        previewData={{ format: 'json', data: [] }}
      />
    )

    expect(screen.getByText(/no data/i)).toBeInTheDocument()
  })

  it('applies dark mode styles', () => {
    // Add dark class to html element
    document.documentElement.classList.add('dark')

    render(<PreviewModal {...defaultProps} />)

    const modal = screen.getByRole('dialog')
    expect(modal).toHaveClass('dark:bg-gray-800')

    // Cleanup
    document.documentElement.classList.remove('dark')
  })

  it('shows modal title', () => {
    render(<PreviewModal {...defaultProps} />)

    expect(screen.getByText(/export preview/i)).toBeInTheDocument()
  })

  it('X button is accessible', () => {
    render(<PreviewModal {...defaultProps} />)

    const closeButton = screen.getByLabelText(/close modal/i)
    expect(closeButton).toBeInTheDocument()
  })
})
