import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GPIO from '../GPIO'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getGpioStatus: vi.fn(),
  getGpioHealth: vi.fn(),
  controlGpio: vi.fn(),
  triggerFlash: vi.fn(),
}))

describe('GPIO', () => {
  let queryClient

  const mockGpioStatus = {
    Relay_Ch1: false,
    Relay_Ch2: true,
    Relay_Ch3: false,
  }

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
    api.getGpioStatus.mockResolvedValue({ data: mockGpioStatus })
    api.getGpioHealth.mockResolvedValue({
      data: { reachable: true, uptime_seconds: 8100, managed_lines: 3 },
    })
  })

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <GPIO />
      </QueryClientProvider>
    )
  }

  it('renders loading state initially', () => {
    // Use a never-resolving promise to keep loading state
    api.getGpioStatus.mockImplementation(() => new Promise(() => {}))
    renderComponent()
    expect(screen.getByText(/Loading GPIO status.../i)).toBeInTheDocument()
  })

  it('renders page heading after loading', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('GPIO Controls')).toBeInTheDocument()
    })
  })

  it('renders all three relay control cards', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Attract Lights')).toBeInTheDocument()
    })

    expect(screen.getByText('Photo Flash')).toBeInTheDocument()
    expect(screen.getByText('UV Light')).toBeInTheDocument()
  })

  it('displays relay channel labels', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Relay Ch1')).toBeInTheDocument()
    })

    expect(screen.getByText('Relay Ch2')).toBeInTheDocument()
    expect(screen.getByText('Relay Ch3')).toBeInTheDocument()
  })

  it('displays correct ON/OFF states from API data', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('GPIO Controls')).toBeInTheDocument()
    })

    // Relay_Ch1 is false -> OFF, Relay_Ch2 is true -> ON, Relay_Ch3 is false -> OFF
    const offButtons = screen.getAllByText('OFF')
    const onButtons = screen.getAllByText('ON')
    expect(offButtons).toHaveLength(2)
    expect(onButtons).toHaveLength(1)
  })

  it('renders the flash trigger button', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Trigger Flash/i)).toBeInTheDocument()
    })
  })

  it('displays the hardware note', async () => {
    renderComponent()

    await waitFor(() => {
      expect(
        screen.getByText(/GPIO controls interact directly with the Mothbox hardware/i)
      ).toBeInTheDocument()
    })
  })

  it('displays error state when GPIO returns an error', async () => {
    api.getGpioStatus.mockResolvedValue({
      data: { error: 'GPIO not available on this platform' },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('GPIO not available on this platform')).toBeInTheDocument()
    })

    expect(
      screen.getByText(/GPIO may not be available in this environment/i)
    ).toBeInTheDocument()
  })

  it('calls controlGpio when a relay toggle is clicked', async () => {
    const user = userEvent.setup()
    api.controlGpio.mockResolvedValue({ data: { success: true } })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Attract Lights')).toBeInTheDocument()
    })

    // Click the Relay_Ch1 OFF button (first OFF button in the grid)
    const offButtons = screen.getAllByText('OFF')
    await user.click(offButtons[0])

    expect(api.controlGpio).toHaveBeenCalledWith('Relay_Ch1', true)
  })

  it('calls triggerFlash when flash button is clicked', async () => {
    const user = userEvent.setup()
    api.triggerFlash.mockResolvedValue({ data: { success: true } })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Trigger Flash/i)).toBeInTheDocument()
    })

    const flashButton = screen.getByText(/Trigger Flash/i)
    await user.click(flashButton)

    expect(api.triggerFlash).toHaveBeenCalled()
  })

  it('does not show loading text after data has loaded', async () => {
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('GPIO Controls')).toBeInTheDocument()
    })

    expect(screen.queryByText(/Loading GPIO status.../i)).not.toBeInTheDocument()
  })

  it('shows daemon connected with uptime when health is reachable', async () => {
    api.getGpioHealth.mockResolvedValue({
      data: { reachable: true, uptime_seconds: 8100, managed_lines: 3 },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Daemon connected/i)).toBeInTheDocument()
    })

    // 8100 seconds = 2h 15m
    expect(screen.getByText(/uptime 2h 15m/i)).toBeInTheDocument()
  })

  it('shows daemon offline when health query fails', async () => {
    api.getGpioHealth.mockRejectedValue(new Error('Connection refused'))

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Daemon offline/i)).toBeInTheDocument()
    })
  })

  it('shows daemon offline when reachable is false', async () => {
    api.getGpioHealth.mockResolvedValue({
      data: { reachable: false },
    })

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText(/Daemon offline/i)).toBeInTheDocument()
    })
  })
})
