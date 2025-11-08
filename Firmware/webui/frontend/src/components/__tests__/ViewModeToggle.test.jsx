import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ViewModeToggle from '../ViewModeToggle'

/**
 * Test suite for ViewModeToggle component
 *
 * Tests the view mode toggle UI component that allows users to switch
 * between grid and list gallery layouts.
 */
describe('ViewModeToggle', () => {
  describe('Rendering', () => {
    it('renders toggle with grid icon when in grid mode', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      const listButton = screen.getByRole('button', { name: /list view/i })

      expect(gridButton).toBeInTheDocument()
      expect(gridButton).toHaveAttribute('aria-pressed', 'true')
      expect(listButton).toHaveAttribute('aria-pressed', 'false')
    })

    it('renders toggle with list icon when in list mode', () => {
      render(<ViewModeToggle currentView="list" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      const listButton = screen.getByRole('button', { name: /list view/i })

      expect(listButton).toHaveAttribute('aria-pressed', 'true')
      expect(gridButton).toHaveAttribute('aria-pressed', 'false')
    })

    it('displays accessible labels', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const container = screen.getByRole('group', { name: /view mode/i })
      expect(container).toBeInTheDocument()
    })

    it('shows two buttons: Grid View and List View', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      expect(screen.getByRole('button', { name: /grid view/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /list view/i })).toBeInTheDocument()
    })

    it('applies active state styling to current mode', () => {
      const { rerender } = render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      const listButton = screen.getByRole('button', { name: /list view/i })

      // Grid should have active styling
      expect(gridButton).toHaveClass('bg-white')
      expect(listButton).not.toHaveClass('bg-white')

      // Switch to list mode
      rerender(<ViewModeToggle currentView="list" onViewChange={() => {}} />)

      // List should have active styling
      expect(listButton).toHaveClass('bg-white')
      expect(gridButton).not.toHaveClass('bg-white')
    })
  })

  describe('User Interactions', () => {
    it('clicking grid button calls onViewChange with grid', async () => {
      const user = userEvent.setup()
      const onViewChange = vi.fn()

      render(<ViewModeToggle currentView="list" onViewChange={onViewChange} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      await user.click(gridButton)

      expect(onViewChange).toHaveBeenCalledWith('grid')
      expect(onViewChange).toHaveBeenCalledTimes(1)
    })

    it('clicking list button calls onViewChange with list', async () => {
      const user = userEvent.setup()
      const onViewChange = vi.fn()

      render(<ViewModeToggle currentView="grid" onViewChange={onViewChange} />)

      const listButton = screen.getByRole('button', { name: /list view/i })
      await user.click(listButton)

      expect(onViewChange).toHaveBeenCalledWith('list')
      expect(onViewChange).toHaveBeenCalledTimes(1)
    })

    it('does not call onViewChange when clicking active mode', async () => {
      const user = userEvent.setup()
      const onViewChange = vi.fn()

      render(<ViewModeToggle currentView="grid" onViewChange={onViewChange} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      await user.click(gridButton)

      // Should not call callback when already in this mode
      expect(onViewChange).not.toHaveBeenCalled()
    })

    it('keyboard navigation works with Enter key', async () => {
      const user = userEvent.setup()
      const onViewChange = vi.fn()

      render(<ViewModeToggle currentView="grid" onViewChange={onViewChange} />)

      const listButton = screen.getByRole('button', { name: /list view/i })
      listButton.focus()
      await user.keyboard('{Enter}')

      expect(onViewChange).toHaveBeenCalledWith('list')
    })

    it('keyboard navigation works with Space key', async () => {
      const user = userEvent.setup()
      const onViewChange = vi.fn()

      render(<ViewModeToggle currentView="grid" onViewChange={onViewChange} />)

      const listButton = screen.getByRole('button', { name: /list view/i })
      listButton.focus()
      await user.keyboard(' ')

      expect(onViewChange).toHaveBeenCalledWith('list')
    })

    it('focus states are visually distinct', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })

      // Should have focus ring classes
      expect(gridButton).toHaveClass('focus:ring-2')
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      const listButton = screen.getByRole('button', { name: /list view/i })

      expect(gridButton).toHaveAttribute('aria-pressed')
      expect(gridButton).toHaveAttribute('aria-label')
      expect(listButton).toHaveAttribute('aria-pressed')
      expect(listButton).toHaveAttribute('aria-label')
    })

    it('screen reader announces current view mode', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })

      // aria-pressed="true" announces "pressed" state to screen readers
      expect(gridButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('has role group with proper semantics', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const group = screen.getByRole('group', { name: /view mode/i })
      expect(group).toBeInTheDocument()
    })

    it('buttons have sufficient color contrast', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })

      // Check for text color classes that ensure WCAG AA compliance
      expect(gridButton).toHaveClass('text-gray-900')
    })
  })

  describe('Edge Cases', () => {
    it('handles null currentView gracefully (defaults to grid)', () => {
      render(<ViewModeToggle currentView={null} onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      expect(gridButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('handles invalid viewMode prop (defaults to grid)', () => {
      render(<ViewModeToggle currentView="invalid" onViewChange={() => {}} />)

      const gridButton = screen.getByRole('button', { name: /grid view/i })
      expect(gridButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('disabled state prevents interaction', async () => {
      const user = userEvent.setup()
      const onViewChange = vi.fn()

      render(<ViewModeToggle currentView="grid" onViewChange={onViewChange} isLoading={true} />)

      const listButton = screen.getByRole('button', { name: /list view/i })
      expect(listButton).toBeDisabled()

      await user.click(listButton)
      expect(onViewChange).not.toHaveBeenCalled()
    })

    it('component is visually responsive', () => {
      render(<ViewModeToggle currentView="grid" onViewChange={() => {}} />)

      const container = screen.getByRole('group')

      // Should have responsive classes for mobile
      expect(container).toHaveClass('flex')
    })
  })
})
