import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PhotoMarker from '../PhotoMarker'
import { MAP_CONFIG } from '@/constants/config'

// Mock react-leaflet components
vi.mock('react-leaflet', () => ({
  Marker: ({ children, position, eventHandlers }) => (
    <div
      data-testid="marker"
      data-lat={position[0]}
      data-lng={position[1]}
      onClick={eventHandlers?.click}
    >
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
}))

// Mock leaflet to prevent icon loading issues in tests
vi.mock('leaflet', () => ({
  default: {
    icon: vi.fn(() => ({})),
    Marker: {
      prototype: {
        options: {},
      },
    },
  },
}))

describe('PhotoMarker', () => {
  const mockLocation = {
    photo_path: '2024-11-10/photo_001.jpg',
    filename: 'photo_001.jpg',
    latitude: 37.7749,
    longitude: -122.4194,
    thumbnail_url: '/api/gallery/thumbnail/2024-11-10/photo_001.jpg',
  }

  const mockOnClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders marker at correct coordinates', () => {
    render(<PhotoMarker location={mockLocation} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    expect(marker).toBeInTheDocument()
    expect(marker).toHaveAttribute('data-lat', '37.7749')
    expect(marker).toHaveAttribute('data-lng', '-122.4194')
  })

  it('shows popup with thumbnail on click', () => {
    render(<PhotoMarker location={mockLocation} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    fireEvent.click(marker)

    const popup = screen.getByTestId('popup')
    expect(popup).toBeInTheDocument()

    const thumbnail = screen.getByAltText('photo_001.jpg')
    expect(thumbnail).toBeInTheDocument()
    expect(thumbnail).toHaveAttribute('src', mockLocation.thumbnail_url)
    expect(thumbnail).toHaveStyle({
      width: `${MAP_CONFIG.POPUP.THUMBNAIL_SIZE}px`,
      height: 'auto',
    })
  })

  it('displays filename in popup', () => {
    render(<PhotoMarker location={mockLocation} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    fireEvent.click(marker)

    expect(screen.getByText('photo_001.jpg')).toBeInTheDocument()
  })

  it('calls onClick when marker clicked', () => {
    render(<PhotoMarker location={mockLocation} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    fireEvent.click(marker)

    expect(mockOnClick).toHaveBeenCalledWith(mockLocation)
  })

  it('calls onClick when View button clicked', () => {
    render(<PhotoMarker location={mockLocation} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    fireEvent.click(marker)

    const viewButton = screen.getByRole('button', { name: /view/i })
    fireEvent.click(viewButton)

    expect(mockOnClick).toHaveBeenCalledWith(mockLocation)
  })

  it('handles missing thumbnail gracefully', () => {
    const locationWithoutThumbnail = {
      ...mockLocation,
      thumbnail_url: null,
    }

    render(<PhotoMarker location={locationWithoutThumbnail} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    fireEvent.click(marker)

    const popup = screen.getByTestId('popup')
    expect(popup).toBeInTheDocument()

    // Filename should still be displayed
    expect(screen.getByText('photo_001.jpg')).toBeInTheDocument()

    // No thumbnail image should be rendered
    expect(screen.queryByAltText('photo_001.jpg')).not.toBeInTheDocument()

    // View button should still work
    const viewButton = screen.getByRole('button', { name: /view/i })
    fireEvent.click(viewButton)
    expect(mockOnClick).toHaveBeenCalledWith(locationWithoutThumbnail)
  })

  it('handles missing onClick prop gracefully', () => {
    render(<PhotoMarker location={mockLocation} />)

    const marker = screen.getByTestId('marker')

    // Should not throw when clicking without onClick prop
    expect(() => fireEvent.click(marker)).not.toThrow()

    fireEvent.click(marker)

    const viewButton = screen.getByRole('button', { name: /view/i })

    // Should not throw when clicking view button without onClick prop
    expect(() => fireEvent.click(viewButton)).not.toThrow()
  })

  it('uses default icon configuration', () => {
    const { container } = render(<PhotoMarker location={mockLocation} onClick={mockOnClick} />)

    // Verify component renders without icon loading errors
    expect(container.firstChild).toBeInTheDocument()
  })

  it('formats coordinates correctly for marker position', () => {
    const locationWithNegativeCoords = {
      ...mockLocation,
      latitude: -33.8688,
      longitude: 151.2093,
    }

    render(<PhotoMarker location={locationWithNegativeCoords} onClick={mockOnClick} />)

    const marker = screen.getByTestId('marker')
    expect(marker).toHaveAttribute('data-lat', '-33.8688')
    expect(marker).toHaveAttribute('data-lng', '151.2093')
  })
})
