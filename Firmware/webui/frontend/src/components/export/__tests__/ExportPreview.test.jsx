import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExportPreview from '../ExportPreview'
import * as useExportPreviewModule from '../../../hooks/useExportPreview'

// Mock the useExportPreview hook
vi.mock('../../../hooks/useExportPreview')

// Mock clipboard API
Object.defineProperty(navigator, 'clipboard', {
  writable: true,
  value: {
    writeText: vi.fn().mockResolvedValue(undefined)
  }
})

describe('ExportPreview', () => {
  let queryClient

  const createWrapper = () => {
    queryClient = new QueryClient({
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

  const defaultProps = {
    format: 'json',
    filter: {},
    selectedFields: ['filename', 'tags', 'latitude', 'longitude']
  }

  const mockPreviewData = {
    format: 'json',
    data: [
      {
        filename: 'photo1.jpg',
        tags: ['moth', 'night'],
        latitude: 37.7749,
        longitude: -122.4194
      },
      {
        filename: 'photo2.jpg',
        tags: ['butterfly'],
        latitude: 37.7750,
        longitude: -122.4195
      }
    ]
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders tab bar with format options', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByRole('tab', { name: /json/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /csv/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /darwin core/i })).toBeInTheDocument()
  })

  it('shows loading state', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: undefined,
      isLoading: true,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/loading preview/i)).toBeInTheDocument()
  })

  it('shows error state', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Failed to load preview')
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    // Should show error message - can have multiple instances in the DOM
    const errorElements = screen.getAllByText(/failed to load preview/i)
    expect(errorElements.length).toBeGreaterThan(0)
  })

  it('displays JSON preview correctly', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    // Should show JSON preview container
    const jsonPreview = screen.getByTestId('json-preview')
    expect(jsonPreview).toBeInTheDocument()
    expect(jsonPreview.innerHTML).toContain('filename')
    expect(jsonPreview.innerHTML).toContain('photo1.jpg')
  })

  it('displays CSV preview correctly', () => {
    const csvPreviewData = {
      format: 'csv',
      headers: ['filename', 'tags', 'latitude'],
      data: [
        { filename: 'photo1.jpg', tags: ['moth'], latitude: 37.7749 }
      ]
    }

    useExportPreviewModule.default.mockReturnValue({
      previewData: csvPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} format="csv" />, { wrapper: createWrapper() })

    // Should show CSV headers
    expect(screen.getByText(/filename/)).toBeInTheDocument()
    expect(screen.getByText(/tags/)).toBeInTheDocument()
    expect(screen.getByText(/latitude/)).toBeInTheDocument()

    // Should show CSV data
    expect(screen.getByText(/photo1.jpg/)).toBeInTheDocument()
  })

  it('switches preview view when tab is clicked', async () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    // Initially on JSON tab
    const jsonTab = screen.getByRole('tab', { name: /json/i })
    expect(jsonTab).toHaveAttribute('aria-selected', 'true')

    // Click CSV tab
    const csvTab = screen.getByRole('tab', { name: /csv/i })
    fireEvent.click(csvTab)

    await waitFor(() => {
      expect(csvTab).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('copy to clipboard button works', async () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    const copyButton = screen.getByRole('button', { name: /copy/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled()
    })

    // Should show success message
    expect(screen.getByText(/copied/i)).toBeInTheDocument()
  })

  it('full preview button opens modal', () => {
    const mockOnOpenModal = vi.fn()
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(
      <ExportPreview {...defaultProps} onOpenModal={mockOnOpenModal} />,
      { wrapper: createWrapper() }
    )

    const fullPreviewButton = screen.getByRole('button', { name: /full preview/i })
    fireEvent.click(fullPreviewButton)

    expect(mockOnOpenModal).toHaveBeenCalled()
  })

  it('updates preview when format changes', () => {
    const { rerender } = render(
      <ExportPreview {...defaultProps} />,
      { wrapper: createWrapper() }
    )

    // Mock hook should be called with initial format
    expect(useExportPreviewModule.default).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'json' })
    )

    // Change format
    rerender(
      <QueryClientProvider client={queryClient}>
        <ExportPreview {...defaultProps} format="csv" />
      </QueryClientProvider>
    )

    // Mock hook should be called with new format
    expect(useExportPreviewModule.default).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'csv' })
    )
  })

  it('updates preview when filter changes', () => {
    const { rerender } = render(
      <ExportPreview {...defaultProps} />,
      { wrapper: createWrapper() }
    )

    const newFilter = { tags: ['moth'], date_start: '2024-01-01' }

    rerender(
      <QueryClientProvider client={queryClient}>
        <ExportPreview {...defaultProps} filter={newFilter} />
      </QueryClientProvider>
    )

    // Mock hook should be called with new filter
    expect(useExportPreviewModule.default).toHaveBeenCalledWith(
      expect.objectContaining({ filter: newFilter })
    )
  })

  it('updates preview when selected fields change', () => {
    const { rerender } = render(
      <ExportPreview {...defaultProps} />,
      { wrapper: createWrapper() }
    )

    const newFields = ['filename', 'species']

    rerender(
      <QueryClientProvider client={queryClient}>
        <ExportPreview {...defaultProps} selectedFields={newFields} />
      </QueryClientProvider>
    )

    // Mock hook should be called with new fields
    expect(useExportPreviewModule.default).toHaveBeenCalledWith(
      expect.objectContaining({ selectedFields: newFields })
    )
  })

  it('shows empty state when no photos match filter', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: { format: 'json', data: [] },
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/no photos found/i)).toBeInTheDocument()
  })

  it('applies syntax highlighting to JSON preview', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    // Check for syntax highlighting classes
    const previewElement = screen.getByTestId('json-preview')
    expect(previewElement).toBeInTheDocument()

    // Should have colored syntax elements in HTML
    expect(previewElement.innerHTML).toContain('json-key')
    expect(previewElement.innerHTML).toContain('json-string')
  })

  it('shows sample indicator (showing 3 of N photos)', () => {
    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    expect(screen.getByText(/showing 2 sample/i)).toBeInTheDocument()
  })

  it('handles copy error gracefully', async () => {
    navigator.clipboard.writeText.mockRejectedValueOnce(new Error('Clipboard error'))

    useExportPreviewModule.default.mockReturnValue({
      previewData: mockPreviewData,
      isLoading: false,
      isError: false,
      error: null
    })

    render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

    const copyButton = screen.getByRole('button', { name: /copy/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(screen.getByText(/failed to copy/i)).toBeInTheDocument()
    })
  })

  describe('XSS Prevention', () => {
    it('escapes script tags in metadata values', () => {
      const maliciousData = {
        format: 'json',
        data: [
          {
            filename: 'photo1.jpg',
            tags: ['<script>alert("xss")</script>'],
            notes: '<script>document.cookie</script>'
          }
        ]
      }

      useExportPreviewModule.default.mockReturnValue({
        previewData: maliciousData,
        isLoading: false,
        isError: false,
        error: null
      })

      render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

      const previewElement = screen.getByTestId('json-preview')
      // Should NOT contain actual script tags (they should be escaped)
      expect(previewElement.innerHTML).not.toContain('<script>')
      expect(previewElement.innerHTML).not.toContain('</script>')
      // Should contain escaped versions
      expect(previewElement.innerHTML).toContain('&lt;script&gt;')
      expect(previewElement.innerHTML).toContain('&lt;/script&gt;')
    })

    it('escapes img tag XSS payload in metadata', () => {
      const maliciousData = {
        format: 'json',
        data: [
          {
            filename: 'photo1.jpg',
            tags: ['<img src=x onerror=alert(1)>'],
            notes: '<img src="x" onerror="steal()">'
          }
        ]
      }

      useExportPreviewModule.default.mockReturnValue({
        previewData: maliciousData,
        isLoading: false,
        isError: false,
        error: null
      })

      render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

      const previewElement = screen.getByTestId('json-preview')
      // Should NOT contain actual img tags
      expect(previewElement.innerHTML).not.toContain('<img')
      // Should contain escaped versions
      expect(previewElement.innerHTML).toContain('&lt;img')
    })

    it('escapes SVG onload XSS payload', () => {
      const maliciousData = {
        format: 'json',
        data: [
          {
            filename: '<svg onload=alert(1)>.jpg',
            species: 'Moth<svg/onload=alert(1)>'
          }
        ]
      }

      useExportPreviewModule.default.mockReturnValue({
        previewData: maliciousData,
        isLoading: false,
        isError: false,
        error: null
      })

      render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

      const previewElement = screen.getByTestId('json-preview')
      // Should NOT contain actual svg tags
      expect(previewElement.innerHTML).not.toContain('<svg')
      // Should contain escaped versions
      expect(previewElement.innerHTML).toContain('&lt;svg')
    })

    it('preserves normal angle brackets display after escaping', () => {
      const normalData = {
        format: 'json',
        data: [
          {
            filename: 'photo1.jpg',
            notes: 'Temperature was > 20°C and < 30°C'
          }
        ]
      }

      useExportPreviewModule.default.mockReturnValue({
        previewData: normalData,
        isLoading: false,
        isError: false,
        error: null
      })

      render(<ExportPreview {...defaultProps} />, { wrapper: createWrapper() })

      const previewElement = screen.getByTestId('json-preview')
      // The text content should show the comparison symbols correctly
      // (they are escaped in HTML but display correctly)
      expect(previewElement.textContent).toContain('>')
      expect(previewElement.textContent).toContain('<')
    })
  })
})
