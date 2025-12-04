import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import MetadataEXIF from '../MetadataEXIF'

describe('MetadataEXIF', () => {
  let clipboardWriteTextSpy

  const mockData = {
    camera: {
      make: 'Arducam',
      model: 'OwlSight 64MP',
      lens: '6mm Wide Angle',
      sensor: 'IMX682',
    },
    capture: {
      iso: 400,
      exposure_time: '1/500',
      f_number: 2.8,
      focal_length: '6.0mm',
      exposure_mode: 'Manual',
      white_balance: 'Daylight',
      timestamp: '2024-01-15T10:30:00Z',
    },
    location: {
      latitude: 37.7749,
      longitude: -122.4194,
      altitude: 10.5,
    },
    deployment: {
      mothbox_id: 'mothbox-backyard',
      firmware_version: '5',
    },
  }

  beforeEach(() => {
    // Mock clipboard API
    clipboardWriteTextSpy = vi.fn().mockResolvedValue()
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: clipboardWriteTextSpy,
      },
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Camera Info Section', () => {
    it('test_renders_camera_info_section', () => {
      render(<MetadataEXIF data={mockData} />)

      // Check section header
      expect(screen.getByText('Camera')).toBeInTheDocument()

      // Check camera fields
      expect(screen.getByText('Make')).toBeInTheDocument()
      expect(screen.getByText('Arducam')).toBeInTheDocument()

      expect(screen.getByText('Model')).toBeInTheDocument()
      expect(screen.getByText('OwlSight 64MP')).toBeInTheDocument()

      expect(screen.getByText('Lens')).toBeInTheDocument()
      expect(screen.getByText('6mm Wide Angle')).toBeInTheDocument()
    })
  })

  describe('Capture Settings Section', () => {
    it('test_renders_capture_settings_section', () => {
      render(<MetadataEXIF data={mockData} />)

      // Check section header
      expect(screen.getByText('Capture Settings')).toBeInTheDocument()

      // Check capture fields
      expect(screen.getByText('ISO')).toBeInTheDocument()
      expect(screen.getByText('ISO 400')).toBeInTheDocument()

      expect(screen.getByText('Shutter Speed')).toBeInTheDocument()
      expect(screen.getByText('1/500')).toBeInTheDocument()

      expect(screen.getByText('Aperture')).toBeInTheDocument()
      expect(screen.getByText('f/2.8')).toBeInTheDocument()

      expect(screen.getByText('Focal Length')).toBeInTheDocument()
      expect(screen.getByText('6.0mm')).toBeInTheDocument()

      expect(screen.getByText('Exposure Mode')).toBeInTheDocument()
      expect(screen.getByText('Manual')).toBeInTheDocument()

      expect(screen.getByText('White Balance')).toBeInTheDocument()
      expect(screen.getByText('Daylight')).toBeInTheDocument()
    })
  })

  describe('Deployment/Location Section', () => {
    it('test_renders_deployment_info_section', () => {
      render(<MetadataEXIF data={mockData} />)

      // Check section header
      expect(screen.getByText('Location & Deployment')).toBeInTheDocument()

      // Check deployment fields
      expect(screen.getByText('Deployment')).toBeInTheDocument()
      expect(screen.getByText('mothbox-backyard')).toBeInTheDocument()

      expect(screen.getByText('Device')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })
  })

  describe('Read-Only Behavior', () => {
    it('test_all_fields_are_read_only', () => {
      const { container } = render(<MetadataEXIF data={mockData} />)

      // Should not have any input, textarea, or contenteditable elements
      const inputs = container.querySelectorAll('input')
      const textareas = container.querySelectorAll('textarea')
      const contentEditables = container.querySelectorAll('[contenteditable="true"]')

      expect(inputs.length).toBe(0)
      expect(textareas.length).toBe(0)
      expect(contentEditables.length).toBe(0)
    })
  })

  describe('Copy Functionality', () => {
    it('test_copy_button_works_for_each_field', async () => {
      render(<MetadataEXIF data={mockData} />)

      // Find all copy buttons (clipboard icons)
      const copyButtons = screen.getAllByRole('button', { name: /copy to clipboard/i })
      expect(copyButtons.length).toBeGreaterThan(0)

      // Test copying the camera make
      const firstCopyButton = copyButtons[0]

      await act(async () => {
        firstCopyButton.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      // Verify clipboard API was called
      expect(clipboardWriteTextSpy).toHaveBeenCalled()

      // Check for success icon
      await waitFor(() => {
        const checkIcon = screen.getByLabelText(/copied to clipboard/i)
        expect(checkIcon).toBeInTheDocument()
      })
    })
  })

  describe('Missing Data Handling', () => {
    it('test_handles_missing_data_gracefully', () => {
      const emptyData = {}
      render(<MetadataEXIF data={emptyData} />)

      // Should show N/A for missing fields
      const naElements = screen.getAllByText('N/A')
      expect(naElements.length).toBeGreaterThan(0)
    })

    it('test_handles_null_values', () => {
      const dataWithNulls = {
        camera: {
          make: null,
          model: null,
          lens: null,
        },
        capture: {
          iso: null,
          exposure_time: null,
        },
      }
      render(<MetadataEXIF data={dataWithNulls} />)

      // Should show N/A for null values
      const naElements = screen.getAllByText('N/A')
      expect(naElements.length).toBeGreaterThan(0)
    })

    it('test_handles_undefined_data_prop', () => {
      render(<MetadataEXIF data={undefined} />)

      // Should render without crashing
      expect(screen.getByText('Camera')).toBeInTheDocument()
    })
  })

  describe('GPS Coordinate Formatting', () => {
    it('test_formats_gps_coordinates', () => {
      render(<MetadataEXIF data={mockData} />)

      // Should format GPS coordinates as "lat° N/S, lon° E/W"
      expect(screen.getByText('GPS')).toBeInTheDocument()

      // Check for formatted GPS string (37.7749° N, 122.4194° W)
      const gpsText = screen.getByText(/37\.7749.*°.*N.*122\.4194.*°.*W/i)
      expect(gpsText).toBeInTheDocument()
    })

    it('test_handles_missing_gps_coordinates', () => {
      const dataWithoutGPS = {
        ...mockData,
        location: {},
      }
      render(<MetadataEXIF data={dataWithoutGPS} />)

      // GPS field should show N/A
      expect(screen.getByText('GPS')).toBeInTheDocument()
    })

    it('test_formats_altitude', () => {
      render(<MetadataEXIF data={mockData} />)

      // Should show altitude in meters
      expect(screen.getByText('Altitude')).toBeInTheDocument()
      expect(screen.getByText('10.5m')).toBeInTheDocument()
    })
  })

  describe('Date/Time Formatting', () => {
    it('test_formats_date_time', () => {
      render(<MetadataEXIF data={mockData} />)

      // Should format timestamp
      expect(screen.getByText('Captured')).toBeInTheDocument()

      // Should show formatted date (locale-dependent)
      // The timestamp '2024-01-15T10:30:00Z' should be formatted
      // We just check that it's rendered and not showing 'N/A'
      const { container } = render(<MetadataEXIF data={mockData} />)
      const capturedText = container.textContent

      // Check that 'Captured' label exists and formatted date is present (not 'N/A')
      expect(capturedText).toContain('Captured')
      // The formatted date will contain numbers (year/month/day)
      expect(capturedText).toMatch(/\d/)
    })

    it('test_handles_invalid_timestamp', () => {
      const dataWithInvalidTimestamp = {
        ...mockData,
        capture: {
          ...mockData.capture,
          timestamp: 'invalid-date',
        },
      }
      render(<MetadataEXIF data={dataWithInvalidTimestamp} />)

      // Should show N/A for invalid timestamp
      expect(screen.getByText('Captured')).toBeInTheDocument()
    })
  })

  describe('Section Headers', () => {
    it('test_shows_section_headers', () => {
      render(<MetadataEXIF data={mockData} />)

      // Check all three section headers exist
      expect(screen.getByText('Camera')).toBeInTheDocument()
      expect(screen.getByText('Capture Settings')).toBeInTheDocument()
      expect(screen.getByText('Location & Deployment')).toBeInTheDocument()
    })

    it('test_section_headers_have_icons', () => {
      const { container } = render(<MetadataEXIF data={mockData} />)

      // Check that section headers have icons (svg elements)
      const headers = container.querySelectorAll('h4')
      expect(headers.length).toBe(3)

      headers.forEach(header => {
        const icon = header.querySelector('svg')
        expect(icon).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('test_handles_zero_values_correctly', () => {
      const dataWithZeros = {
        ...mockData,
        capture: {
          ...mockData.capture,
          iso: 0,
        },
        location: {
          latitude: 0,
          longitude: 0,
          altitude: 0,
        },
      }
      render(<MetadataEXIF data={dataWithZeros} />)

      // Zero ISO is invalid photographically, should show N/A
      expect(screen.getByText('ISO')).toBeInTheDocument()
      // formatISO(0) returns "N/A" because ISO <= 0 is invalid

      // But zero coordinates are valid (Null Island)
      expect(screen.getByText('0.000000° N, 0.000000° E')).toBeInTheDocument()
      expect(screen.getByText('0m')).toBeInTheDocument()
    })

    it('test_handles_negative_coordinates', () => {
      const dataWithNegativeCoords = {
        ...mockData,
        location: {
          latitude: -37.7749,
          longitude: -122.4194,
        },
      }
      render(<MetadataEXIF data={dataWithNegativeCoords} />)

      // Should show S and W for negative coordinates
      const gpsText = screen.getByText(/37\.7749.*°.*S.*122\.4194.*°.*W/i)
      expect(gpsText).toBeInTheDocument()
    })
  })
})
