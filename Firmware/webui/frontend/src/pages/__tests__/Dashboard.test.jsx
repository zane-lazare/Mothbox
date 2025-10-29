import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from '../Dashboard'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getSystemStatus: vi.fn(),
  getPowerStatus: vi.fn(),
  getPhotos: vi.fn(),
  capturePhoto: vi.fn(),
  syncGps: vi.fn(),
}))

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('Dashboard', () => {
  let queryClient

  const mockSystemStatus = {
    cpu_temp: 45.2,
    disk: {
      free_gb: 25.6,
      used_percent: 42.3,
    },
    photo_count: 123,
    hardware: {
      ina260_enabled: true,
      epaper_enabled: false,
    },
    gps: {
      enabled: true,
      has_fix: true,
      latitude: 37.7749,
      longitude: -122.4194,
      utc_offset: -8,
      last_sync: 1698768000,
    },
  }

  const mockPowerStatus = {
    enabled: true,
    power: 5.2,
  }

  const mockPhotos = [
    {
      filename: 'photo_2023_10_31_12_00_00.jpg',
      date: '2023-10-31T12:00:00Z',
    },
  ]

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })

    vi.clearAllMocks()

    // Set default mock responses
    api.getSystemStatus.mockResolvedValue({ data: mockSystemStatus })
    api.getPowerStatus.mockResolvedValue({ data: mockPowerStatus })
    api.getPhotos.mockResolvedValue({ data: { photos: mockPhotos } })
  })

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <Dashboard />
      </QueryClientProvider>
    )
  }

  it('renders loading state initially', () => {
    renderComponent()
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument()
  })

  it('renders dashboard content after loading', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })

    expect(screen.getByText(/Quick Actions/i)).toBeInTheDocument()
  })

  it('displays CPU temperature', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/45.2°C/)).toBeInTheDocument()
    })
  })

  it('displays disk space information', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/25.6 GB/)).toBeInTheDocument()
    })

    expect(screen.getByText(/42.3% used/)).toBeInTheDocument()
  })

  it('displays photo count', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('123')).toBeInTheDocument()
    })
  })

  it('displays hardware status', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Hardware Status/i)).toBeInTheDocument()
    })

    expect(screen.getByText('INA260')).toBeInTheDocument()
    expect(screen.getByText('E-Paper')).toBeInTheDocument()
  })

  it('displays power status when enabled', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/5.2W/)).toBeInTheDocument()
    })
  })

  it('renders GPS status card when GPS is enabled', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/GPS Status/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/GPS Fix Acquired/i)).toBeInTheDocument()
  })

  it('displays GPS coordinates when fix is acquired', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/37.7749/)).toBeInTheDocument()
    })

    expect(screen.getByText(/-122.4194/)).toBeInTheDocument()
    expect(screen.getByText(/-8h/)).toBeInTheDocument()
  })

  it('displays "No GPS Fix" when GPS has no fix', async () => {
    api.getSystemStatus.mockResolvedValue({
      data: {
        ...mockSystemStatus,
        gps: {
          ...mockSystemStatus.gps,
          has_fix: false,
        },
      },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/No GPS Fix/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/Click "Sync Now" to acquire GPS position/i)).toBeInTheDocument()
  })

  it('does not render GPS card when GPS is disabled', async () => {
    api.getSystemStatus.mockResolvedValue({
      data: {
        ...mockSystemStatus,
        gps: {
          ...mockSystemStatus.gps,
          enabled: false,
        },
      },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })

    expect(screen.queryByText(/GPS Status/i)).not.toBeInTheDocument()
  })

  it('syncs GPS when sync button is clicked', async () => {
    const user = userEvent.setup()
    api.syncGps.mockResolvedValue({ data: { success: true } })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Sync Now/i)).toBeInTheDocument()
    })

    const syncButton = screen.getByText(/Sync Now/i)
    await user.click(syncButton)

    // Button should show "Syncing..." while operation is in progress
    expect(screen.getByText(/Syncing.../i)).toBeInTheDocument()

    await waitFor(() => {
      expect(api.syncGps).toHaveBeenCalled()
    })
  })

  it('displays last GPS sync timestamp', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Last Sync/i)).toBeInTheDocument()
    })

    // formatTimestamp should format the timestamp
    expect(screen.getByText(/2023/)).toBeInTheDocument()
  })

  it('displays latest photo information', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Latest Photo/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/photo_2023_10_31_12_00_00.jpg/)).toBeInTheDocument()
  })

  it('handles capture photo button click', async () => {
    const user = userEvent.setup()
    api.capturePhoto.mockResolvedValue({ data: { success: true } })

    // Mock window.location.reload
    const originalLocation = window.location
    delete window.location
    window.location = { reload: vi.fn() }

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Capture Photo/i)).toBeInTheDocument()
    })

    const captureButton = screen.getByText(/Capture Photo/i)
    await user.click(captureButton)

    expect(screen.getByText(/Capturing.../i)).toBeInTheDocument()

    await waitFor(() => {
      expect(api.capturePhoto).toHaveBeenCalled()
    })

    // Restore original location
    window.location = originalLocation
  })

  it('disables capture button while capturing', async () => {
    const user = userEvent.setup()
    api.capturePhoto.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Capture Photo/i)).toBeInTheDocument()
    })

    const captureButton = screen.getByText(/Capture Photo/i)
    await user.click(captureButton)

    expect(captureButton).toBeDisabled()
  })

  it('disables sync button while syncing', async () => {
    const user = userEvent.setup()
    api.syncGps.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Sync Now/i)).toBeInTheDocument()
    })

    const syncButton = screen.getByText(/Sync Now/i)
    await user.click(syncButton)

    expect(syncButton).toBeDisabled()
  })
})
