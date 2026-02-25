import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CoordinateInput from '../CoordinateInput'

describe('CoordinateInput', () => {
  let onChange: ReturnType<typeof vi.fn<(coords: { latitude: number | null; longitude: number | null }) => void>>

  beforeEach(() => {
    onChange = vi.fn()
  })

  it('renders latitude and longitude inputs', () => {
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    expect(screen.getByLabelText(/latitude/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/longitude/i)).toBeInTheDocument()
  })

  it('displays current latitude and longitude values', () => {
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} />)

    expect(screen.getByLabelText(/latitude/i)).toHaveValue(37.7749)
    expect(screen.getByLabelText(/longitude/i)).toHaveValue(-122.4194)
  })

  it('calls onChange when latitude changes', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)
    await user.clear(latInput)
    await user.type(latInput, '37.7749')
    await user.tab()

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ latitude: 37.7749 }),
      )
    })
  })

  it('calls onChange when longitude changes', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const lonInput = screen.getByLabelText(/longitude/i)
    await user.clear(lonInput)
    await user.type(lonInput, '-122.4194')
    await user.tab()

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ longitude: -122.4194 }),
      )
    })
  })

  it('validates latitude range (-90 to 90)', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)

    await user.clear(latInput)
    await user.type(latInput, '91')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('Latitude must be between -90 and 90')).toBeInTheDocument()
    })

    await user.clear(latInput)
    await user.type(latInput, '-91')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('Latitude must be between -90 and 90')).toBeInTheDocument()
    })
  })

  it('validates longitude range (-180 to 180)', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const lonInput = screen.getByLabelText(/longitude/i)

    await user.clear(lonInput)
    await user.type(lonInput, '181')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('Longitude must be between -180 and 180')).toBeInTheDocument()
    })

    await user.clear(lonInput)
    await user.type(lonInput, '-181')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('Longitude must be between -180 and 180')).toBeInTheDocument()
    })
  })

  it('shows error with role="alert" for accessibility', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)
    await user.clear(latInput)
    await user.type(latInput, '100')
    await user.tab()

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Latitude must be between -90 and 90')
    })
  })

  it('clears error when value becomes valid', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)

    await user.clear(latInput)
    await user.type(latInput, '100')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('Latitude must be between -90 and 90')).toBeInTheDocument()
    })

    await user.clear(latInput)
    await user.type(latInput, '37.7749')
    await user.tab()

    await waitFor(() => {
      expect(screen.queryByText('Latitude must be between -90 and 90')).not.toBeInTheDocument()
    })
  })

  it('respects disabled prop on both inputs', () => {
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} disabled />)

    expect(screen.getByLabelText(/latitude/i)).toBeDisabled()
    expect(screen.getByLabelText(/longitude/i)).toBeDisabled()
  })

  it('displays external error prop with role="alert"', () => {
    render(
      <CoordinateInput
        latitude={null}
        longitude={null}
        onChange={onChange}
        error="GPS coordinates are required"
      />,
    )

    const errorEl = screen.getByText('GPS coordinates are required')
    expect(errorEl).toBeInTheDocument()
    expect(errorEl).toHaveAttribute('role', 'alert')
  })

  it('calls onChange with null when field cleared', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)
    await user.clear(latInput)
    await user.tab()

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ latitude: null }),
      )
    })
  })

  it('has correct input attributes', () => {
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)
    const lonInput = screen.getByLabelText(/longitude/i)

    expect(latInput).toHaveAttribute('type', 'number')
    expect(lonInput).toHaveAttribute('type', 'number')
    expect(latInput).toHaveAttribute('step', '0.000001')
    expect(lonInput).toHaveAttribute('step', '0.000001')
  })

  it('sets aria-invalid on fields with errors', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)
    await user.clear(latInput)
    await user.type(latInput, '100')
    await user.tab()

    await waitFor(() => {
      expect(latInput).toHaveAttribute('aria-invalid', 'true')
    })
  })

  it('does not call onChange with out-of-range values', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />)

    const latInput = screen.getByLabelText(/latitude/i)
    await user.clear(latInput)
    await user.type(latInput, '91')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('Latitude must be between -90 and 90')).toBeInTheDocument()
    })

    // onChange should not have been called with the invalid value
    const calls = onChange.mock.calls
    for (const call of calls) {
      const lat = call[0].latitude
      if (lat !== null) {
        expect(lat).toBeGreaterThanOrEqual(-90)
        expect(lat).toBeLessThanOrEqual(90)
      }
    }
  })

  it('accepts external prop updates after user edit', async () => {
    const user = userEvent.setup()
    const { rerender } = render(
      <CoordinateInput latitude={10} longitude={20} onChange={onChange} />,
    )

    // User edits latitude
    const latInput = screen.getByLabelText(/latitude/i)
    await user.clear(latInput)
    await user.type(latInput, '30')
    await user.tab()

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ latitude: 30 }),
      )
    })

    // External update (e.g., GPS auto-fill) passes new props
    onChange.mockClear()
    rerender(<CoordinateInput latitude={45} longitude={50} onChange={onChange} />)

    // Form should accept the external update
    await waitFor(() => {
      expect(screen.getByLabelText(/latitude/i)).toHaveValue(45)
      expect(screen.getByLabelText(/longitude/i)).toHaveValue(50)
    })
  })

  it('handles rapid successive external prop updates without loops', async () => {
    const { rerender } = render(
      <CoordinateInput latitude={10} longitude={20} onChange={onChange} />,
    )

    // Simulate rapid GPS updates
    rerender(<CoordinateInput latitude={11} longitude={21} onChange={onChange} />)
    rerender(<CoordinateInput latitude={12} longitude={22} onChange={onChange} />)
    rerender(<CoordinateInput latitude={13} longitude={23} onChange={onChange} />)

    // Form should settle on the last values
    await waitFor(() => {
      expect(screen.getByLabelText(/latitude/i)).toHaveValue(13)
      expect(screen.getByLabelText(/longitude/i)).toHaveValue(23)
    })

    // Should not have triggered an infinite loop — onChange calls should be bounded
    expect(onChange.mock.calls.length).toBeLessThan(10)
  })

  it('disables DMS toggle button when disabled prop is set', () => {
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} disabled />)

    const toggleButton = screen.getByRole('button', { name: /toggle format/i })
    expect(toggleButton).toBeDisabled()
  })

  it('displays DMS format when toggle is clicked', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} />)

    const toggleButton = screen.getByRole('button', { name: /toggle format/i })
    await user.click(toggleButton)

    expect(screen.getByText(/37°46'29.64"N/i)).toBeInTheDocument()
    expect(screen.getByText(/122°25'9.84"W/i)).toBeInTheDocument()
  })

  it('toggles between decimal and DMS display', async () => {
    const user = userEvent.setup()
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} />)

    const toggleButton = screen.getByRole('button', { name: /toggle format/i })

    await user.click(toggleButton)
    expect(screen.getByText(/37°46'29.64"N/i)).toBeInTheDocument()

    await user.click(toggleButton)
    expect(screen.queryByText(/37°46'29.64"N/i)).not.toBeInTheDocument()
  })
})
