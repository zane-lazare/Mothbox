import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SelectionProvider, useSelectionContext } from '../../../contexts/SelectionContext'
import BulkActionsToolbar from '../BulkActionsToolbar'
import React from 'react'

// Test harness to control selection state
function TestHarness({ children, selectPhotos = [] }) {
  const ctx = useSelectionContext()

  React.useEffect(() => {
    // Enter select mode first
    if (!ctx.isSelectMode) {
      ctx.toggleSelectMode()
    }
    // Then select the specified photos
    selectPhotos.forEach(photoPath => {
      ctx.selectPhoto(photoPath)
    })
  }, []) // Only run once on mount

  return <>{children}</>
}

const renderWithSelection = (props = {}, selectPhotos = []) => {
  return render(
    <SelectionProvider>
      <TestHarness selectPhotos={selectPhotos}>
        <BulkActionsToolbar {...props} />
      </TestHarness>
    </SelectionProvider>
  )
}

describe('BulkActionsToolbar', () => {
  describe('Visibility', () => {
    it('does NOT render when selectedCount === 0', () => {
      render(
        <SelectionProvider>
          <BulkActionsToolbar
            onTagClick={vi.fn()}
            onSpeciesClick={vi.fn()}
            onDeleteClick={vi.fn()}
          />
        </SelectionProvider>
      )

      // Toolbar should not be in the document
      expect(screen.queryByRole('toolbar')).not.toBeInTheDocument()
    })

    it('renders when selectedCount > 0', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      expect(screen.getByRole('toolbar')).toBeInTheDocument()
    })

    it('renders when multiple photos are selected', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']
      )

      expect(screen.getByRole('toolbar')).toBeInTheDocument()
    })
  })

  describe('Selection Count', () => {
    it('shows "1 photo selected" for single selection', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      expect(screen.getByText('1 photo selected')).toBeInTheDocument()
    })

    it('shows "X photos selected" for multiple selections', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']
      )

      expect(screen.getByText('3 photos selected')).toBeInTheDocument()
    })

    it('shows "2 photos selected" for exactly two selections', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg', 'photo2.jpg']
      )

      expect(screen.getByText('2 photos selected')).toBeInTheDocument()
    })

    it('uses aria-live for screen reader updates', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const countElement = screen.getByText('1 photo selected')
      expect(countElement).toHaveAttribute('aria-live', 'polite')
    })
  })

  describe('Action Buttons', () => {
    it('shows "Tag" button with TagIcon', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      expect(tagButton).toBeInTheDocument()
      expect(within(tagButton).getByText('Tag')).toBeInTheDocument()

      // Check for icon (SVG)
      const svg = tagButton.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('shows "Species" button with appropriate icon', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const speciesButton = screen.getByRole('button', { name: /set species for selected photos/i })
      expect(speciesButton).toBeInTheDocument()
      expect(within(speciesButton).getByText('Species')).toBeInTheDocument()

      // Check for icon (SVG)
      const svg = speciesButton.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('shows "Delete" button with TrashIcon (destructive styling)', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      expect(deleteButton).toBeInTheDocument()
      expect(within(deleteButton).getByText('Delete')).toBeInTheDocument()

      // Check for icon (SVG)
      const svg = deleteButton.querySelector('svg')
      expect(svg).toBeInTheDocument()

      // Check for destructive styling (red color)
      expect(deleteButton.className).toMatch(/red/)
    })

    it('shows "Deselect All" button', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const deselectButton = screen.getByRole('button', { name: /deselect all photos/i })
      expect(deselectButton).toBeInTheDocument()
      expect(within(deselectButton).getByText('Deselect All')).toBeInTheDocument()

      // Check for icon (SVG - XMarkIcon)
      const svg = deselectButton.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('all buttons are keyboard accessible', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      const speciesButton = screen.getByRole('button', { name: /set species for selected photos/i })
      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      const deselectButton = screen.getByRole('button', { name: /deselect all photos/i })

      // All buttons should be focusable
      tagButton.focus()
      expect(tagButton).toHaveFocus()

      speciesButton.focus()
      expect(speciesButton).toHaveFocus()

      deleteButton.focus()
      expect(deleteButton).toHaveFocus()

      deselectButton.focus()
      expect(deselectButton).toHaveFocus()
    })
  })

  describe('Button Callbacks', () => {
    it('Tag button calls onTagClick prop', async () => {
      const user = userEvent.setup()
      const onTagClick = vi.fn()

      renderWithSelection(
        {
          onTagClick,
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      await user.click(tagButton)

      expect(onTagClick).toHaveBeenCalledTimes(1)
    })

    it('Species button calls onSpeciesClick prop', async () => {
      const user = userEvent.setup()
      const onSpeciesClick = vi.fn()

      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick,
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const speciesButton = screen.getByRole('button', { name: /set species for selected photos/i })
      await user.click(speciesButton)

      expect(onSpeciesClick).toHaveBeenCalledTimes(1)
    })

    it('Delete button calls onDeleteClick prop', async () => {
      const user = userEvent.setup()
      const onDeleteClick = vi.fn()

      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick,
        },
        ['photo1.jpg']
      )

      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      await user.click(deleteButton)

      expect(onDeleteClick).toHaveBeenCalledTimes(1)
    })

    it('Deselect All button clears selection', async () => {
      const user = userEvent.setup()

      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg', 'photo2.jpg']
      )

      // Verify selection is shown
      expect(screen.getByText('2 photos selected')).toBeInTheDocument()

      const deselectButton = screen.getByRole('button', { name: /deselect all photos/i })
      await user.click(deselectButton)

      // Toolbar should disappear when selection is cleared
      expect(screen.queryByRole('toolbar')).not.toBeInTheDocument()
    })

    it('button callbacks work with keyboard interaction (Enter)', async () => {
      const user = userEvent.setup()
      const onTagClick = vi.fn()

      renderWithSelection(
        {
          onTagClick,
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      tagButton.focus()
      await user.keyboard('{Enter}')

      expect(onTagClick).toHaveBeenCalledTimes(1)
    })

    it('button callbacks work with keyboard interaction (Space)', async () => {
      const user = userEvent.setup()
      const onDeleteClick = vi.fn()

      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick,
        },
        ['photo1.jpg']
      )

      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      deleteButton.focus()
      await user.keyboard(' ')

      expect(onDeleteClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Styling', () => {
    it('toolbar is fixed at bottom of viewport', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/fixed/)
      expect(toolbar.className).toMatch(/bottom-/)
    })

    it('toolbar is horizontally centered', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/left-1\/2/)
      expect(toolbar.className).toMatch(/-translate-x-1\/2/)
    })

    it('toolbar has elevated z-index (z-40)', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/z-40/)
    })

    it('toolbar has backdrop/shadow for visibility', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      // Should have shadow and background
      expect(toolbar.className).toMatch(/shadow/)
      expect(toolbar.className).toMatch(/bg-/)
    })

    it('toolbar has rounded corners', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/rounded/)
    })

    it('toolbar has border', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/border/)
    })

    it('buttons have hover states', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      expect(tagButton.className).toMatch(/hover:/)
    })

    it('delete button has destructive (red) styling', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      expect(deleteButton.className).toMatch(/red/)
    })

    it('toolbar has proper spacing and padding', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/px-/)
      expect(toolbar.className).toMatch(/py-/)
      expect(toolbar.className).toMatch(/gap-/)
    })

    it('shows visual dividers between button groups', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      // Should have divider elements (div with bg-gray class)
      const dividers = toolbar.querySelectorAll('div[class*="bg-gray"]')
      expect(dividers.length).toBeGreaterThan(0)
    })
  })

  describe('Accessibility', () => {
    it('has role="toolbar"', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar).toHaveAttribute('role', 'toolbar')
    })

    it('has aria-label describing the toolbar', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar).toHaveAttribute('aria-label', 'Bulk actions for selected photos')
    })

    it('Tag button has aria-label', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      expect(tagButton).toHaveAttribute('aria-label', 'Add tags to selected photos')
    })

    it('Species button has aria-label', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const speciesButton = screen.getByRole('button', { name: /set species for selected photos/i })
      expect(speciesButton).toHaveAttribute('aria-label', 'Set species for selected photos')
    })

    it('Delete button has aria-label', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      expect(deleteButton).toHaveAttribute('aria-label', 'Delete selected photos')
    })

    it('Deselect All button has aria-label', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const deselectButton = screen.getByRole('button', { name: /deselect all photos/i })
      expect(deselectButton).toHaveAttribute('aria-label', 'Deselect all photos')
    })

    it('Delete button has aria-describedby for warning', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const deleteButton = screen.getByRole('button', { name: /delete selected photos/i })
      expect(deleteButton).toHaveAttribute('aria-describedby', 'delete-warning')

      // Check that the warning element exists (even if visually hidden)
      const warning = document.getElementById('delete-warning')
      expect(warning).toBeInTheDocument()
      expect(warning.textContent).toMatch(/cannot be undone/i)
    })

    it('selection count has aria-live for screen reader updates', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const countElement = screen.getByText('1 photo selected')
      expect(countElement).toHaveAttribute('aria-live', 'polite')
    })

    it('hidden warning has sr-only class', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const warning = document.getElementById('delete-warning')
      expect(warning.className).toMatch(/sr-only/)
    })
  })

  describe('Portal Rendering', () => {
    it('toolbar is rendered in document.body (not in component tree)', () => {
      const { container } = renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      // Toolbar should NOT be in the container (it's portaled to body)
      const toolbarInContainer = container.querySelector('[role="toolbar"]')
      expect(toolbarInContainer).toBeNull()

      // But it should be in the document (via portal)
      const toolbarInDocument = document.querySelector('[role="toolbar"]')
      expect(toolbarInDocument).toBeInTheDocument()
    })

    it('toolbar is child of document.body', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      // Parent should be body (or a React portal container in body)
      expect(document.body.contains(toolbar)).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('handles missing callback props gracefully', () => {
      // Should not crash if callbacks are undefined
      expect(() => {
        renderWithSelection({}, ['photo1.jpg'])
      }).not.toThrow()
    })

    it('updates count when selection changes', async () => {
      const user = userEvent.setup()

      const { rerender } = render(
        <SelectionProvider>
          <TestHarness selectPhotos={['photo1.jpg']}>
            <BulkActionsToolbar
              onTagClick={vi.fn()}
              onSpeciesClick={vi.fn()}
              onDeleteClick={vi.fn()}
            />
          </TestHarness>
        </SelectionProvider>
      )

      expect(screen.getByText('1 photo selected')).toBeInTheDocument()

      // Click deselect to clear
      const deselectButton = screen.getByRole('button', { name: /deselect all photos/i })
      await user.click(deselectButton)

      // Toolbar should be gone
      expect(screen.queryByRole('toolbar')).not.toBeInTheDocument()
    })

    it('handles very large selection counts', () => {
      const manyPhotos = Array.from({ length: 100 }, (_, i) => `photo${i}.jpg`)

      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        manyPhotos
      )

      expect(screen.getByText('100 photos selected')).toBeInTheDocument()
    })

    it('renders without crashing when SelectionProvider is present', () => {
      expect(() => {
        renderWithSelection(
          {
            onTagClick: vi.fn(),
            onSpeciesClick: vi.fn(),
            onDeleteClick: vi.fn(),
          },
          ['photo1.jpg']
        )
      }).not.toThrow()
    })
  })

  describe('Dark Mode Support', () => {
    it('has dark mode classes for background', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const toolbar = screen.getByRole('toolbar')
      expect(toolbar.className).toMatch(/dark:bg-/)
    })

    it('has dark mode classes for text', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const countElement = screen.getByText('1 photo selected')
      expect(countElement.className).toMatch(/dark:text-/)
    })

    it('buttons have dark mode hover states', () => {
      renderWithSelection(
        {
          onTagClick: vi.fn(),
          onSpeciesClick: vi.fn(),
          onDeleteClick: vi.fn(),
        },
        ['photo1.jpg']
      )

      const tagButton = screen.getByRole('button', { name: /add tags to selected photos/i })
      expect(tagButton.className).toMatch(/dark:/)
    })
  })
})
