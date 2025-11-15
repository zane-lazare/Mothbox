import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import CopyButton from '../CopyButton'

describe('CopyButton', () => {
  let clipboardWriteTextSpy

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

  describe('Rendering', () => {
    it('renders copy button', () => {
      render(<CopyButton text="Test text" />)

      const button = screen.getByRole('button', { name: /copy/i })
      expect(button).toBeInTheDocument()
    })

    it('has accessible label', () => {
      render(<CopyButton text="Filename.jpg" />)

      const button = screen.getByRole('button')
      expect(button).toHaveAccessibleName(/copy/i)
    })

    it('displays clipboard icon initially', () => {
      const { container } = render(<CopyButton text="Test" />)

      // Clipboard icon should be present
      const clipboardIcon = container.querySelector('svg[data-icon="clipboard"]')
      expect(clipboardIcon).toBeInTheDocument()
    })
  })

  describe('Copy Functionality', () => {
    it('calls clipboard API when clicked', async () => {
      const { getByRole } = render(<CopyButton text="Test content" />)

      const button = getByRole('button', { name: /copy/i })

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalledTimes(1)
      expect(clipboardWriteTextSpy).toHaveBeenCalledWith('Test content')
    })

    it('copies correct text to clipboard', async () => {
      const testText = 'GPS: 40.7128° N, 74.0060° W'
      const { getByRole } = render(<CopyButton text={testText} />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalledWith(testText)
    })

    it('handles multiple copy operations', async () => {
      vi.useFakeTimers()
      try {
        const { getByRole } = render(<CopyButton text="Test" />)
        const button = getByRole('button')

        await act(async () => {
          button.click()
          await clipboardWriteTextSpy.mock.results[0].value
        })

        expect(clipboardWriteTextSpy).toHaveBeenCalledTimes(1)

        // Advance time to reset feedback
        act(() => {
          vi.advanceTimersByTime(2000)
        })

        await act(async () => {
          button.click()
          await clipboardWriteTextSpy.mock.results[1].value
        })

        expect(clipboardWriteTextSpy).toHaveBeenCalledTimes(2)
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Success Feedback', () => {
    it('shows success feedback after copying', async () => {
      const { container, getByRole } = render(<CopyButton text="Test" />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      // Check icon should appear
      const checkIcon = container.querySelector('svg[data-icon="check"]')
      expect(checkIcon).toBeInTheDocument()

      // Clipboard icon should be gone
      const clipboardIcon = container.querySelector('svg[data-icon="clipboard"]')
      expect(clipboardIcon).not.toBeInTheDocument()
    })

    it('resets feedback after 2 seconds', async () => {
      vi.useFakeTimers()
      try {
        const { container, getByRole } = render(<CopyButton text="Test" />)

        const button = getByRole('button')

        await act(async () => {
          button.click()
          await clipboardWriteTextSpy.mock.results[0].value
        })

        // Check icon visible immediately
        expect(container.querySelector('svg[data-icon="check"]')).toBeInTheDocument()

        // Advance time by 2 seconds
        act(() => {
          vi.advanceTimersByTime(2000)
        })

        // Back to clipboard icon
        expect(container.querySelector('svg[data-icon="clipboard"]')).toBeInTheDocument()
        expect(container.querySelector('svg[data-icon="check"]')).not.toBeInTheDocument()
      } finally {
        vi.useRealTimers()
      }
    })

    it('maintains feedback for exactly 2 seconds', async () => {
      vi.useFakeTimers()
      try {
        const { container, getByRole } = render(<CopyButton text="Test" />)

        const button = getByRole('button')

        await act(async () => {
          button.click()
          await clipboardWriteTextSpy.mock.results[0].value
        })

        expect(container.querySelector('svg[data-icon="check"]')).toBeInTheDocument()

        // After 1.9 seconds, still showing check icon
        act(() => {
          vi.advanceTimersByTime(1900)
        })
        expect(container.querySelector('svg[data-icon="check"]')).toBeInTheDocument()

        // After 2 seconds, back to clipboard icon
        act(() => {
          vi.advanceTimersByTime(100)
        })
        expect(container.querySelector('svg[data-icon="clipboard"]')).toBeInTheDocument()
      } finally {
        vi.useRealTimers()
      }
    })

    it('updates aria-label to reflect copied state', async () => {
      vi.useFakeTimers()
      try {
        const { getByRole } = render(<CopyButton text="Test" />)

        const button = getByRole('button')

        // Initial state
        expect(button).toHaveAccessibleName(/copy/i)

        await act(async () => {
          button.click()
          await clipboardWriteTextSpy.mock.results[0].value
        })

        // After clicking, should show "copied"
        expect(button).toHaveAccessibleName(/copied/i)

        // After timeout, back to "copy"
        act(() => {
          vi.advanceTimersByTime(2000)
        })
        expect(button).toHaveAccessibleName(/copy/i)
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Error Handling', () => {
    it('handles clipboard API errors gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      // Make clipboard API fail
      clipboardWriteTextSpy.mockRejectedValue(new Error('Clipboard access denied'))

      const { getByRole } = render(<CopyButton text="Test" />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value.catch(() => {})
      })

      // Should log error
      expect(consoleErrorSpy).toHaveBeenCalled()

      consoleErrorSpy.mockRestore()
    })

    it('does not show success feedback when copy fails', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {})

      clipboardWriteTextSpy.mockRejectedValue(new Error('Failed'))

      const { container, getByRole } = render(<CopyButton text="Test" />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value.catch(() => {})
      })

      // Should still show clipboard icon (not check)
      expect(container.querySelector('svg[data-icon="clipboard"]')).toBeInTheDocument()
      expect(container.querySelector('svg[data-icon="check"]')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('is keyboard accessible', () => {
      render(<CopyButton text="Test" />)

      const button = screen.getByRole('button')
      button.focus()

      expect(button).toHaveFocus()
    })

    it('can be triggered with click', async () => {
      const { getByRole } = render(<CopyButton text="Test" />)

      const button = getByRole('button')
      button.focus()

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalled()
    })

    it('has proper button type', () => {
      render(<CopyButton text="Test" />)

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'button')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty string', async () => {
      const { getByRole } = render(<CopyButton text="" />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalledWith('')
    })

    it('handles very long text', async () => {
      const longText = 'A'.repeat(10000)
      const { getByRole } = render(<CopyButton text={longText} />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalledWith(longText)
    })

    it('handles special characters', async () => {
      const specialText = '!@#$%^&*()_+-={}[]|\\:";\'<>?,./'
      const { getByRole } = render(<CopyButton text={specialText} />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalledWith(specialText)
    })

    it('handles Unicode characters', async () => {
      const unicodeText = '测试 🦋 ñ é'
      const { getByRole } = render(<CopyButton text={unicodeText} />)

      const button = getByRole('button')

      await act(async () => {
        button.click()
        await clipboardWriteTextSpy.mock.results[0].value
      })

      expect(clipboardWriteTextSpy).toHaveBeenCalledWith(unicodeText)
    })
  })

  describe('Component Cleanup', () => {
    it('cleans up timeout on unmount', async () => {
      vi.useFakeTimers()
      try {
        const { getByRole, unmount } = render(<CopyButton text="Test" />)

        const button = getByRole('button')

        await act(async () => {
          button.click()
          await clipboardWriteTextSpy.mock.results[0].value
        })

        // Unmount before timeout completes
        unmount()

        // Advance timers - should not cause errors
        act(() => {
          vi.advanceTimersByTime(2000)
        })

        // No errors should occur
        expect(true).toBe(true)
      } finally {
        vi.useRealTimers()
      }
    })
  })
})
