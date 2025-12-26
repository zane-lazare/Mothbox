import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CronExpressionErrorBoundary from '../CronExpressionErrorBoundary'

// Component that throws an error for testing
const ThrowingComponent = ({ shouldThrow }) => {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>Content rendered successfully</div>
}

describe('CronExpressionErrorBoundary', () => {
  let consoleErrorSpy

  beforeEach(() => {
    // Suppress console.error during tests since we expect errors
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
  })

  describe('Normal Rendering', () => {
    it('renders children when no error occurs', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={false} />
        </CronExpressionErrorBoundary>
      )

      expect(screen.getByText('Content rendered successfully')).toBeInTheDocument()
    })

    it('does not show error UI when children render successfully', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={false} />
        </CronExpressionErrorBoundary>
      )

      expect(screen.queryByText('Unable to load cron expression editor')).not.toBeInTheDocument()
      expect(screen.queryByText('Try Again')).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays fallback UI when child throws error', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      expect(screen.getByText('Unable to load cron expression editor')).toBeInTheDocument()
      expect(screen.getByText('Try Again')).toBeInTheDocument()
    })

    it('logs error to console', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      expect(consoleErrorSpy).toHaveBeenCalled()
      // Check that our error message was logged (may be among multiple calls due to React error handling)
      const allCalls = consoleErrorSpy.mock.calls.map((call) => call.join(' '))
      const hasOurError = allCalls.some((call) => call.includes('CronExpressionInput error:'))
      expect(hasOurError).toBe(true)
    })

    it('hides children content when error occurs', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      expect(screen.queryByText('Content rendered successfully')).not.toBeInTheDocument()
    })
  })

  describe('Recovery', () => {
    it('provides a retry button', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      const retryButton = screen.getByText('Try Again')
      expect(retryButton).toBeInTheDocument()
      expect(retryButton).toHaveAttribute('type', 'button')
    })

    it('clears error state when retry is clicked', () => {
      const { rerender } = render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      // Error state should be shown
      expect(screen.getByText('Unable to load cron expression editor')).toBeInTheDocument()

      // Rerender with non-throwing component and click retry
      rerender(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={false} />
        </CronExpressionErrorBoundary>
      )

      const retryButton = screen.getByText('Try Again')
      fireEvent.click(retryButton)

      // After retry, content should render
      expect(screen.getByText('Content rendered successfully')).toBeInTheDocument()
      expect(screen.queryByText('Unable to load cron expression editor')).not.toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies error styling classes', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      const errorContainer = screen.getByText('Unable to load cron expression editor').parentElement
      expect(errorContainer).toHaveClass('bg-red-50', 'border', 'border-red-200', 'rounded-md')
    })

    it('applies dark mode classes', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      const errorContainer = screen.getByText('Unable to load cron expression editor').parentElement
      expect(errorContainer).toHaveClass('dark:bg-red-900/20', 'dark:border-red-800')
    })

    it('applies correct styling to retry button', () => {
      render(
        <CronExpressionErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </CronExpressionErrorBoundary>
      )

      const retryButton = screen.getByText('Try Again')
      expect(retryButton).toHaveClass(
        'text-xs',
        'px-3',
        'py-1',
        'bg-red-100',
        'text-red-700',
        'rounded'
      )
    })
  })
})
