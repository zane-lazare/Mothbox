import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GPSSettings from '../GPSSettings'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getGpsConfig: vi.fn(),
  updateGpsConfig: vi.fn(),
  getGpsStatus: vi.fn(),
  syncGps: vi.fn(),
}))

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(() => 'toast-id'),
    dismiss: vi.fn(),
  },
}))

describe('GPSSettings', () => {
  let queryClient

  const mockGPSConfig = {
    enabled: true,
    device: '/dev/ttyAMA0',
    baudrate: 9600,
    timeout: 10,
    timeout_hot: 15,
    timeout_warm: 60,
    timeout_cold: 90,
    timeout_almanac: 1200,
  }

  const mockGPSStatus = {
    has_fix: true,
    latitude: 37.7749,
    longitude: -122.4194,
    gpstime: 1698768000,
    utc_offset: -8,
  }

  beforeEach(() => {
    // Create a new QueryClient for each test to ensure isolation
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries for tests
        },
      },
    })

    // Reset all mocks
    vi.clearAllMocks()

    // Set default mock responses
    api.getGpsConfig.mockResolvedValue({ data: mockGPSConfig })
    api.getGpsStatus.mockResolvedValue({ data: mockGPSStatus })
  })

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <GPSSettings />
      </QueryClientProvider>
    )
  }

  it('renders loading state initially', () => {
    renderComponent()
    expect(screen.getByText(/Loading GPS configuration/i)).toBeInTheDocument()
  })

  it('renders GPS configuration when loaded', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/GPS Module Configuration/i)).toBeInTheDocument()
    })

    // Check for enable toggle
    expect(screen.getByText(/Enable GPS Module/i)).toBeInTheDocument()
  })

  it('displays GPS status when enabled and has fix', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Current GPS Status/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/GPS Fix/i)).toBeInTheDocument()
    expect(screen.getByText(/37.7749/)).toBeInTheDocument()
    expect(screen.getByText(/-122.4194/)).toBeInTheDocument()
  })

  it('displays "No GPS Fix" when GPS has no fix', async () => {
    api.getGpsStatus.mockResolvedValue({
      data: { ...mockGPSStatus, has_fix: false },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/No GPS Fix/i)).toBeInTheDocument()
    })
  })

  it('shows configuration fields when GPS is enabled', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /GPS Device Path/i })).toBeInTheDocument()
    })

    expect(screen.getByRole('combobox', { name: /Baud Rate/i })).toBeInTheDocument()
    expect(screen.getByText(/Advanced Timeout Configuration/i)).toBeInTheDocument()
  })

  it('hides configuration fields when GPS is disabled', async () => {
    api.getGpsConfig.mockResolvedValue({
      data: { ...mockGPSConfig, enabled: false },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Enable GPS Module/i)).toBeInTheDocument()
    })

    // Configuration fields should not be present
    expect(screen.queryByRole('textbox', { name: /GPS Device Path/i })).not.toBeInTheDocument()
  })

  it('toggles GPS enabled state', async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByRole('checkbox')).toBeInTheDocument()
    })

    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeChecked()

    await user.click(checkbox)
    expect(checkbox).not.toBeChecked()
  })

  it('updates device path input', async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /GPS Device Path/i })).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox', { name: /GPS Device Path/i })
    expect(input).toHaveValue('/dev/ttyAMA0')

    await user.clear(input)
    await user.type(input, '/dev/ttyUSB0')
    expect(input).toHaveValue('/dev/ttyUSB0')
  })

  it('updates baudrate selection', async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /Baud Rate/i })).toBeInTheDocument()
    })

    const select = screen.getByRole('combobox', { name: /Baud Rate/i })
    expect(select).toHaveValue('9600')

    await user.selectOptions(select, '115200')
    expect(select).toHaveValue('115200')
  })

  it('saves configuration when save button clicked', async () => {
    const user = userEvent.setup()
    api.updateGpsConfig.mockResolvedValue({ data: { success: true } })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/💾 Save Configuration/i)).toBeInTheDocument()
    })

    const saveButton = screen.getByText(/💾 Save Configuration/i)
    await user.click(saveButton)

    await waitFor(() => {
      expect(api.updateGpsConfig).toHaveBeenCalled()
      const callArgs = api.updateGpsConfig.mock.calls[0][0]
      expect(callArgs).toEqual({
        gps_enabled: true,
        gps_device: '/dev/ttyAMA0',
        gps_baudrate: 9600,
        gps_timeout: 10,
        gps_timeout_hot: 15,
        gps_timeout_warm: 60,
        gps_timeout_cold: 90,
        gps_timeout_almanac: 1200,
      })
    })
  })

  it('syncs GPS when sync button clicked', async () => {
    const user = userEvent.setup()

    // Create a promise that won't resolve immediately to allow us to see the "Syncing..." state
    let resolveSyncGps
    api.syncGps.mockImplementation(() => new Promise((resolve) => {
      resolveSyncGps = () => resolve({
        data: {
          success: true,
          latitude: 37.7749,
          longitude: -122.4194,
        },
      })
    }))

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/🛰️ Sync GPS Now/i)).toBeInTheDocument()
    })

    const syncButton = screen.getByText(/🛰️ Sync GPS Now/i)
    await user.click(syncButton)

    // Button should show "Syncing..." while operation is in progress
    await waitFor(() => {
      expect(screen.getByText(/Syncing.../i)).toBeInTheDocument()
    })

    expect(api.syncGps).toHaveBeenCalled()

    // Resolve the promise to complete the sync
    resolveSyncGps()

    // Wait for sync to complete and button to return to normal state
    await waitFor(() => {
      expect(screen.getByText(/🛰️ Sync GPS Now/i)).toBeInTheDocument()
    })
  })

  it('displays hardware setup instructions', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Hardware Setup Required/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/Connect NEO-M8N TX → Pi GPIO15/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Install gpsd/i).length).toBeGreaterThan(0)
  })

  it('collapses and expands when title is clicked', async () => {
    const user = userEvent.setup()
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/GPS Module Configuration/i)).toBeInTheDocument()
    })

    // Find the title and click it
    const title = screen.getByText(/GPS Module Configuration/i)
    await user.click(title)

    // Configuration should be hidden
    expect(screen.queryByRole('textbox', { name: /GPS Device Path/i })).not.toBeInTheDocument()

    // Click again to expand
    await user.click(title)

    // Configuration should be visible again
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /GPS Device Path/i })).toBeInTheDocument()
    })
  })
})
