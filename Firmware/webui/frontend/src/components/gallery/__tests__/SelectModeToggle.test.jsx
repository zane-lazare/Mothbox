import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SelectionProvider } from '../../../contexts/SelectionContext'
import SelectModeToggle from '../SelectModeToggle'

// Render helper with SelectionProvider
const renderWithProvider = (ui) => {
  return render(
    <SelectionProvider>
      {ui}
    </SelectionProvider>
  )
}

describe('SelectModeToggle', () => {
  beforeEach(() => {
    // No mocks needed - using real SelectionContext
  })

  // Rendering
  describe('Rendering', () => {
    it('renders a button element', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })

    it('shows "Select" text when not in select mode', () => {
      renderWithProvider(<SelectModeToggle />)
      expect(screen.getByText('Select')).toBeInTheDocument()
    })

    it('shows CheckCircleIcon when not in select mode', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')
      // Heroicons renders SVG with specific path
      const svg = button.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('shows "Cancel" text when in select mode', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Enter select mode
      await user.click(button)

      expect(screen.getByText('Cancel')).toBeInTheDocument()
    })

    it('shows XMarkIcon when in select mode', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Enter select mode
      await user.click(button)

      const svg = button.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('has aria-pressed=false when not in select mode', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-pressed', 'false')
    })

    it('has aria-pressed=true when in select mode', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Enter select mode
      await user.click(button)

      expect(button).toHaveAttribute('aria-pressed', 'true')
    })
  })

  // Interaction
  describe('Interaction', () => {
    it('calls toggleSelectMode when clicked', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Initial state
      expect(button).toHaveAttribute('aria-pressed', 'false')

      // Click to toggle
      await user.click(button)

      // Should be in select mode now
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('toggles from Select to Cancel on click', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Initial: Select
      expect(screen.getByText('Select')).toBeInTheDocument()

      // Click to toggle
      await user.click(button)

      // Should show Cancel
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.queryByText('Select')).not.toBeInTheDocument()
    })

    it('toggles from Cancel back to Select on second click', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Enter select mode
      await user.click(button)
      expect(screen.getByText('Cancel')).toBeInTheDocument()

      // Exit select mode
      await user.click(button)

      // Should show Select again
      expect(screen.getByText('Select')).toBeInTheDocument()
      expect(screen.queryByText('Cancel')).not.toBeInTheDocument()
    })

    it('is keyboard accessible with Enter key', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      button.focus()
      expect(button).toHaveFocus()

      // Toggle with Enter
      await user.keyboard('{Enter}')

      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('is keyboard accessible with Space key', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      button.focus()

      // Toggle with Space
      await user.keyboard(' ')

      expect(button).toHaveAttribute('aria-pressed', 'true')
    })
  })

  // Styling
  describe('Styling', () => {
    it('has proper button styling classes', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Should have base button classes (matching ViewModeToggle pattern)
      expect(button.className).toMatch(/px-/)
      expect(button.className).toMatch(/py-/)
      expect(button.className).toMatch(/rounded/)
    })

    it('shows different visual state when active', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      const inactiveClasses = button.className

      // Toggle to active
      await user.click(button)

      const activeClasses = button.className

      // Classes should be different when active
      expect(activeClasses).not.toBe(inactiveClasses)
    })

    it('includes CheckCircleIcon from Heroicons', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')
      const svg = button.querySelector('svg')

      // Check SVG has icon size classes (use getAttribute for SVG className)
      const classes = svg.getAttribute('class')
      expect(classes).toMatch(/h-5/)
      expect(classes).toMatch(/w-5/)
    })

    it('includes XMarkIcon when in select mode', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      await user.click(button)

      const svg = button.querySelector('svg')
      const classes = svg.getAttribute('class')
      expect(classes).toMatch(/h-5/)
      expect(classes).toMatch(/w-5/)
    })
  })

  // Accessibility
  describe('Accessibility', () => {
    it('has aria-label for screen readers when not in select mode', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'Enter selection mode')
    })

    it('has aria-label for screen readers when in select mode', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      await user.click(button)

      expect(button).toHaveAttribute('aria-label', 'Exit selection mode')
    })

    it('has role="button"', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
    })

    it('supports focus states', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      button.focus()

      expect(button).toHaveFocus()
    })

    it('has focus ring classes', () => {
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Should have focus:outline-none and focus:ring-* classes (Tailwind pattern)
      expect(button.className).toMatch(/focus:/)
    })
  })

  // Integration with SelectionContext
  describe('Integration with SelectionContext', () => {
    it('reflects SelectionContext state correctly', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Initial: not in select mode
      expect(button).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByText('Select')).toBeInTheDocument()

      // Toggle
      await user.click(button)

      // Now in select mode
      expect(button).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByText('Cancel')).toBeInTheDocument()
    })

    it('multiple toggle components share same state', async () => {
      const user = userEvent.setup()
      const { container } = render(
        <SelectionProvider>
          <SelectModeToggle />
          <SelectModeToggle />
        </SelectionProvider>
      )

      const buttons = container.querySelectorAll('button')
      expect(buttons).toHaveLength(2)

      // Click first button
      await user.click(buttons[0])

      // Both should reflect select mode
      expect(buttons[0]).toHaveAttribute('aria-pressed', 'true')
      expect(buttons[1]).toHaveAttribute('aria-pressed', 'true')
    })
  })

  // Edge Cases
  describe('Edge Cases', () => {
    it('handles rapid clicking', async () => {
      const user = userEvent.setup()
      renderWithProvider(<SelectModeToggle />)
      const button = screen.getByRole('button')

      // Rapid clicks
      await user.click(button)
      await user.click(button)
      await user.click(button)
      await user.click(button)

      // Should end up with predictable state (even number of clicks = not selected)
      expect(button).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByText('Select')).toBeInTheDocument()
    })

    it('renders without crashing when SelectionProvider is present', () => {
      expect(() => {
        renderWithProvider(<SelectModeToggle />)
      }).not.toThrow()
    })
  })
})
