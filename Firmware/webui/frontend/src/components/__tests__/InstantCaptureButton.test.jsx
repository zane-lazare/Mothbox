import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InstantCaptureButton from '../InstantCaptureButton'
import * as api from '../../utils/api'
import toast from 'react-hot-toast'

// Mock the API module
vi.mock('../../utils/api', () => ({
  instantCapture: vi.fn(),
}))

// Mock toast notifications
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

describe('InstantCaptureButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Rendering', () => {
    it('renders button with camera icon', () => {
      render(<InstantCaptureButton />)

      const button = screen.getByRole('button', { name: /instant capture/i })
      expect(button).toBeInTheDocument()
    })

    it('displays default text "Instant Capture"', () => {
      render(<InstantCaptureButton />)

      expect(screen.getByText(/instant capture/i)).toBeInTheDocument()
    })

    it('has accessible button role', () => {
      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      expect(button).toHaveAccessibleName(/instant capture/i)
    })

    it('is enabled by default', () => {
      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      expect(button).not.toBeDisabled()
    })
  })

  describe('API Integration', () => {
    it('calls instantCapture API when clicked', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockResolvedValue({
        data: {
          success: true,
          photo_path: 'test_captures/instant_2025_01_15__14_30_45_ABC123.jpg',
          metadata: { exposure_time: 10000, analogue_gain: 8.0 },
          timestamp: 1737000000.123,
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(api.instantCapture).toHaveBeenCalledTimes(1)
      })
    })

    it('passes no parameters to instantCapture API', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockResolvedValue({
        data: {
          success: true,
          photo_path: 'test_captures/instant_2025_01_15__14_30_45_ABC123.jpg',
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(api.instantCapture).toHaveBeenCalledWith()
      })
    })
  })

  describe('Loading State', () => {
    it('shows "Capturing..." text during capture', async () => {
      const user = userEvent.setup()
      let resolveCapture
      api.instantCapture.mockReturnValue(
        new Promise((resolve) => {
          resolveCapture = resolve
        })
      )

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      // Should show loading text
      await waitFor(() => {
        expect(screen.getByText(/capturing/i)).toBeInTheDocument()
      })

      // Cleanup
      act(() => {
        resolveCapture({
          data: { success: true, photo_path: 'test.jpg' },
        })
      })
    })

    it('disables button during capture', async () => {
      const user = userEvent.setup()
      let resolveCapture
      api.instantCapture.mockReturnValue(
        new Promise((resolve) => {
          resolveCapture = resolve
        })
      )

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      // Button should be disabled
      await waitFor(() => {
        expect(button).toBeDisabled()
      })

      // Cleanup
      act(() => {
        resolveCapture({
          data: { success: true, photo_path: 'test.jpg' },
        })
      })
    })

    it('re-enables button after capture completes', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockResolvedValue({
        data: {
          success: true,
          photo_path: 'test_captures/instant_test.jpg',
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      // Wait for capture to complete
      await waitFor(() => {
        expect(api.instantCapture).toHaveBeenCalled()
      })

      // Button should be enabled again
      await waitFor(() => {
        expect(button).not.toBeDisabled()
      })
    })
  })

  describe('Success Handling', () => {
    it('shows success toast with filename on successful capture', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockResolvedValue({
        data: {
          success: true,
          photo_path: 'test_captures/instant_2025_01_15__14_30_45_ABC123.jpg',
          metadata: { exposure_time: 10000 },
          timestamp: 1737000000.123,
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringMatching(/instant.*captured/i)
        )
      })
    })

    it('includes photo filename in success message', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockResolvedValue({
        data: {
          success: true,
          photo_path: 'test_captures/instant_2025_01_15__14_30_45_ABC123.jpg',
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringMatching(/instant_2025_01_15__14_30_45_ABC123\.jpg/i)
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('shows error toast when API call fails', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockRejectedValue({
        response: {
          data: {
            error: 'Camera busy',
          },
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })

    it('displays API error message in toast', async () => {
      const user = userEvent.setup()
      const errorMessage = 'Camera not available'
      api.instantCapture.mockRejectedValue({
        response: {
          data: {
            error: errorMessage,
          },
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringMatching(new RegExp(errorMessage, 'i'))
        )
      })
    })

    it('shows fallback error message when API response has no error field', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockRejectedValue({
        response: {
          data: {},
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringMatching(/failed.*instant capture/i)
        )
      })
    })

    it('handles network errors gracefully', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockRejectedValue(new Error('Network error'))

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })

    it('re-enables button after error', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockRejectedValue({
        response: {
          data: { error: 'Failed' },
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      // Wait for error handling
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })

      // Button should be enabled again
      await waitFor(() => {
        expect(button).not.toBeDisabled()
      })
    })
  })

  describe('Concurrent Capture Prevention', () => {
    it('prevents multiple concurrent captures', async () => {
      const user = userEvent.setup()
      let resolveCapture
      api.instantCapture.mockReturnValue(
        new Promise((resolve) => {
          resolveCapture = resolve
        })
      )

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')

      // Click once
      await user.click(button)

      // Try to click again while capturing
      await user.click(button)
      await user.click(button)

      // API should only be called once
      expect(api.instantCapture).toHaveBeenCalledTimes(1)

      // Cleanup
      act(() => {
        resolveCapture({
          data: { success: true, photo_path: 'test.jpg' },
        })
      })
    })

    it('allows new capture after previous completes', async () => {
      const user = userEvent.setup()
      api.instantCapture.mockResolvedValue({
        data: {
          success: true,
          photo_path: 'test.jpg',
        },
      })

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')

      // First capture
      await user.click(button)
      await waitFor(() => {
        expect(api.instantCapture).toHaveBeenCalledTimes(1)
      })

      // Wait for button to be enabled
      await waitFor(() => {
        expect(button).not.toBeDisabled()
      })

      // Second capture should work
      await user.click(button)
      await waitFor(() => {
        expect(api.instantCapture).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Accessibility', () => {
    it('is keyboard accessible', () => {
      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      button.focus()

      expect(button).toHaveFocus()
    })

    it('has proper button type', () => {
      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'button')
    })

    it('maintains accessibility during loading state', async () => {
      const user = userEvent.setup()
      let resolveCapture
      api.instantCapture.mockReturnValue(
        new Promise((resolve) => {
          resolveCapture = resolve
        })
      )

      render(<InstantCaptureButton />)

      const button = screen.getByRole('button')
      await user.click(button)

      // Button should still have accessible name during loading
      await waitFor(() => {
        expect(button).toHaveAccessibleName(/capturing/i)
      })

      // Cleanup
      act(() => {
        resolveCapture({
          data: { success: true, photo_path: 'test.jpg' },
        })
      })
    })
  })

  describe('Custom Props', () => {
    it('accepts custom className', () => {
      const { container } = render(
        <InstantCaptureButton className="custom-class" />
      )

      const button = container.querySelector('.custom-class')
      expect(button).toBeInTheDocument()
    })

    it('merges custom className with default classes', () => {
      render(<InstantCaptureButton className="custom-class" />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('accepts disabled prop from parent', () => {
      render(<InstantCaptureButton disabled />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('does not call API when disabled by parent', async () => {
      const user = userEvent.setup()
      render(<InstantCaptureButton disabled />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(api.instantCapture).not.toHaveBeenCalled()
    })
  })
})
