import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FieldSelector from '../FieldSelector'

describe('FieldSelector', () => {
  const mockOnChange = vi.fn()

  const defaultProps = {
    format: 'json',
    selectedFields: {
      json: ['filename', 'latitude', 'longitude'],
      darwin_core: ['filename', 'species'],
      csv: [],
      inaturalist: ['filename', 'tags']
    },
    onChange: mockOnChange,
    disabled: false
  }

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  it('renders all field categories', () => {
    render(<FieldSelector {...defaultProps} />)

    expect(screen.getByRole('heading', { name: /File Info/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^Location$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Species/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Deployment/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Tags & Notes/i })).toBeInTheDocument()
  })

  it('shows correct selected count for current format', () => {
    render(<FieldSelector {...defaultProps} />)

    // json format has 3 selected fields: filename, latitude, longitude
    expect(screen.getByText(/3 of \d+ fields selected/i)).toBeInTheDocument()
  })

  it('shows different selections when format changes', () => {
    const { rerender } = render(<FieldSelector {...defaultProps} />)

    // json has 3 selected
    expect(screen.getByText(/3 of \d+ fields selected/i)).toBeInTheDocument()

    // darwin_core has 2 selected
    rerender(<FieldSelector {...defaultProps} format="darwin_core" />)
    expect(screen.getByText(/2 of \d+ fields selected/i)).toBeInTheDocument()

    // csv has 0 selected
    rerender(<FieldSelector {...defaultProps} format="csv" />)
    expect(screen.getByText(/0 of \d+ fields selected/i)).toBeInTheDocument()
  })

  it('displays checkboxes with correct checked state for current format', () => {
    render(<FieldSelector {...defaultProps} />)

    // These should be checked for json format
    const filenameCheckbox = screen.getByLabelText(/filename/i)
    const latitudeCheckbox = screen.getByLabelText(/latitude/i)
    const longitudeCheckbox = screen.getByLabelText(/longitude/i)

    expect(filenameCheckbox).toBeChecked()
    expect(latitudeCheckbox).toBeChecked()
    expect(longitudeCheckbox).toBeChecked()

    // This should not be checked
    const altitudeCheckbox = screen.getByLabelText(/altitude/i)
    expect(altitudeCheckbox).not.toBeChecked()
  })

  it('calls onChange when individual field is toggled', () => {
    render(<FieldSelector {...defaultProps} />)

    const altitudeCheckbox = screen.getByLabelText(/altitude/i)
    fireEvent.click(altitudeCheckbox)

    expect(mockOnChange).toHaveBeenCalledWith('json', expect.arrayContaining(['filename', 'latitude', 'longitude', 'altitude']))
  })

  it('calls onChange when field is unchecked', () => {
    render(<FieldSelector {...defaultProps} />)

    const filenameCheckbox = screen.getByLabelText(/filename/i)
    fireEvent.click(filenameCheckbox)

    expect(mockOnChange).toHaveBeenCalledWith('json', expect.arrayContaining(['latitude', 'longitude']))
    expect(mockOnChange).toHaveBeenCalledWith('json', expect.not.arrayContaining(['filename']))
  })

  it('global "Select All" button selects all fields', () => {
    render(<FieldSelector {...defaultProps} />)

    const selectAllButtons = screen.getAllByRole('button', { name: /select all/i })
    // Global "Select All" button is the one with blue color
    const globalSelectAll = selectAllButtons.find(btn =>
      btn.className.includes('text-blue-600')
    )
    fireEvent.click(globalSelectAll)

    // Should call onChange with all available fields
    expect(mockOnChange).toHaveBeenCalledWith('json', expect.any(Array))
    const calledFields = mockOnChange.mock.calls[0][1]
    expect(calledFields.length).toBeGreaterThan(10) // Should have many fields
  })

  it('global "Deselect All" button deselects all fields', () => {
    render(<FieldSelector {...defaultProps} />)

    const deselectAllButtons = screen.getAllByRole('button', { name: /deselect all/i })
    // Global "Deselect All" button is the one with larger text size
    const globalDeselectAll = deselectAllButtons.find(btn =>
      btn.className.includes('text-gray-600') && btn.className.includes('px-3')
    )
    fireEvent.click(globalDeselectAll)

    expect(mockOnChange).toHaveBeenCalledWith('json', [])
  })

  it('category "Select All" selects all fields in that category', () => {
    render(<FieldSelector {...defaultProps} />)

    // Find Location category and its select all button
    const locationSection = screen.getByRole('heading', { name: /^Location$/i }).closest('div')
    const categorySelectAll = locationSection.querySelector('[data-testid="category-select-all"]')

    fireEvent.click(categorySelectAll)

    // Should call onChange with location fields added
    expect(mockOnChange).toHaveBeenCalled()
    const calledFields = mockOnChange.mock.calls[0][1]
    expect(calledFields).toContain('latitude')
    expect(calledFields).toContain('longitude')
    expect(calledFields).toContain('altitude')
    expect(calledFields).toContain('gps_accuracy')
  })

  it('category "Deselect All" deselects all fields in that category', () => {
    render(<FieldSelector {...defaultProps} />)

    // Find Location category and its deselect all button
    const locationSection = screen.getByRole('heading', { name: /^Location$/i }).closest('div')
    const categoryDeselectAll = locationSection.querySelector('[data-testid="category-deselect-all"]')

    fireEvent.click(categoryDeselectAll)

    // Should call onChange with location fields removed
    expect(mockOnChange).toHaveBeenCalled()
    const calledFields = mockOnChange.mock.calls[0][1]
    expect(calledFields).not.toContain('latitude')
    expect(calledFields).not.toContain('longitude')
  })

  it('respects disabled prop', () => {
    render(<FieldSelector {...defaultProps} disabled={true} />)

    const filenameCheckbox = screen.getByLabelText(/^filename$/i)
    expect(filenameCheckbox).toBeDisabled()

    const selectAllButtons = screen.getAllByRole('button', { name: /select all/i })
    // Global "Select All" button should be disabled
    const globalSelectAll = selectAllButtons.find(btn =>
      btn.className.includes('text-blue-600')
    )
    expect(globalSelectAll).toBeDisabled()
  })

  it('maintains per-format state correctly', () => {
    const { rerender } = render(<FieldSelector {...defaultProps} />)

    // Check json fields
    const filenameCheckbox = screen.getByLabelText(/filename/i)
    expect(filenameCheckbox).toBeChecked()

    // Switch to darwin_core
    rerender(<FieldSelector {...defaultProps} format="darwin_core" />)

    // filename should be checked for darwin_core too
    expect(screen.getByLabelText(/filename/i)).toBeChecked()

    // latitude should NOT be checked (not in darwin_core selected fields)
    expect(screen.getByLabelText(/latitude/i)).not.toBeChecked()

    // Switch back to json
    rerender(<FieldSelector {...defaultProps} format="json" />)

    // latitude should be checked again (back to json selections)
    expect(screen.getByLabelText(/latitude/i)).toBeChecked()
  })

  it('shows field count correctly after selection changes', () => {
    const { rerender } = render(<FieldSelector {...defaultProps} />)

    expect(screen.getByText(/3 of \d+ fields selected/i)).toBeInTheDocument()

    // Update selected fields
    const updatedProps = {
      ...defaultProps,
      selectedFields: {
        ...defaultProps.selectedFields,
        json: ['filename', 'latitude', 'longitude', 'altitude', 'tags']
      }
    }

    rerender(<FieldSelector {...updatedProps} />)
    expect(screen.getByText(/5 of \d+ fields selected/i)).toBeInTheDocument()
  })

  it('displays field tooltips', () => {
    render(<FieldSelector {...defaultProps} />)

    const filenameCheckbox = screen.getByLabelText(/filename/i)
    const filenameLabel = filenameCheckbox.closest('label')

    // Check if tooltip exists (title attribute or aria-label)
    expect(filenameLabel).toHaveAttribute('title')
  })
})
