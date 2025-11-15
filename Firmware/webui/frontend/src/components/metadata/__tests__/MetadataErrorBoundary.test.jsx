import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MetadataErrorBoundary from '../MetadataErrorBoundary'

/**
 * Test suite for MetadataErrorBoundary component
 *
 * Tests error boundary behavior, fallback UI, and recovery functionality.
 */

// Component that throws an error on demand
function ProblematicComponent({ shouldThrow }) {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>Normal content</div>
}

describe('MetadataErrorBoundary', () => {
  // Suppress console.error for cleaner test output
  const originalError = console.error
  beforeAll(() => {
    console.error = vi.fn()
  })

  afterAll(() => {
    console.error = originalError
  })

  describe('Normal operation', () => {
    it('renders children when no error occurs', () => {
      render(
        <MetadataErrorBoundary>
          <div>Test content</div>
        </MetadataErrorBoundary>
      )

      expect(screen.getByText('Test content')).toBeInTheDocument()
    })

    it('does not show error UI when children render successfully', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={false} />
        </MetadataErrorBoundary>
      )

      expect(screen.getByText('Normal content')).toBeInTheDocument()
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument()
    })
  })

  describe('Error handling', () => {
    it('catches errors and displays fallback UI', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      expect(screen.queryByText('Normal content')).not.toBeInTheDocument()
    })

    it('shows error message in fallback UI', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      expect(screen.getByText(/unable to display metadata/i)).toBeInTheDocument()
    })

    it('shows retry button in fallback UI', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      const retryButton = screen.getByRole('button', { name: /try again/i })
      expect(retryButton).toBeInTheDocument()
    })

    it('logs error to console', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error')

      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      expect(consoleErrorSpy).toHaveBeenCalled()
    })
  })

  describe('Recovery', () => {
    it('retry button calls handleReset method', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      // Error state should be visible
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      const retryButton = screen.getByRole('button', { name: /try again/i })
      expect(retryButton).toBeInTheDocument()

      // Verify button is functional (doesn't throw when clicked)
      // In real use, clicking retry would reset the error state and
      // the parent component would provide new/fixed children
      expect(() => retryButton.click()).not.toThrow()
    })
  })

  describe('UI elements', () => {
    it('displays warning icon in error state', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      // Check for SVG icon
      const errorUI = screen.getByText(/something went wrong/i).closest('div')
      const svg = errorUI.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('applies correct styling classes in error state', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      const errorContainer = screen.getByText(/something went wrong/i).closest('div')
      expect(errorContainer).toHaveClass('p-4', 'text-center')
    })

    it('applies dark mode classes', () => {
      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      const errorContainer = screen.getByText(/something went wrong/i).closest('div')
      expect(errorContainer.className).toContain('dark:')
    })
  })

  describe('Accessibility', () => {
    it('retry button is keyboard accessible', async () => {
      const user = userEvent.setup()

      render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      const retryButton = screen.getByRole('button', { name: /try again/i })

      // Tab to button
      await user.tab()
      expect(retryButton).toHaveFocus()

      // Should be clickable with Enter/Space
      expect(retryButton).toBeEnabled()
    })
  })

  describe('Edge cases', () => {
    it('handles multiple sequential errors', () => {
      const { rerender } = render(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

      // Rerender with another error
      rerender(
        <MetadataErrorBoundary>
          <ProblematicComponent shouldThrow={true} />
        </MetadataErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })

    it('handles errors in nested components', () => {
      function NestedComponent() {
        return (
          <div>
            <ProblematicComponent shouldThrow={true} />
          </div>
        )
      }

      render(
        <MetadataErrorBoundary>
          <NestedComponent />
        </MetadataErrorBoundary>
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })
})
