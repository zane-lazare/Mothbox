import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import React from 'react'
import ActiveFilterChips from '../ActiveFilterChips'
import { FilterProvider, useFilterContext } from '../../../contexts/FilterContext'

// Helper component that sets up filters synchronously before children render
function FilterSetup({ setupFilters, children }) {
  const ctx = useFilterContext()
  // Call setupFilters synchronously during render (not in useEffect)
  // This is safe because it only happens once during initial render
  const hasSetup = React.useRef(false)
  if (!hasSetup.current && setupFilters) {
    setupFilters(ctx)
    hasSetup.current = true
  }
  return children
}

// Helper to render with FilterProvider
function renderWithProvider(ui, { setupFilters } = {}) {
  return render(
    <FilterProvider>
      <FilterSetup setupFilters={setupFilters}>{ui}</FilterSetup>
    </FilterProvider>
  )
}

describe('ActiveFilterChips', () => {
  // Rendering tests
  describe('Rendering', () => {
    it('renders nothing when no active filters', () => {
      const { container } = renderWithProvider(<ActiveFilterChips />)
      expect(container.firstChild).toBeNull()
    })

    it('renders chip for date range preset filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
        expect(screen.getByText('Last 7 Days')).toBeInTheDocument()
      })
    })

    it('renders chip for custom date range filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange(null, '2024-01-01', '2024-01-31')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
        expect(screen.getByText('2024-01-01 to 2024-01-31')).toBeInTheDocument()
      })
    })

    it('renders chip for tags filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setTags(['moth', 'nocturnal'], 'any')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Tags:')).toBeInTheDocument()
        expect(screen.getByText('2 (any)')).toBeInTheDocument()
      })
    })

    it('renders chip for species filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setSpecies(['Actias luna', 'Hyalophora cecropia'], null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Species:')).toBeInTheDocument()
        expect(screen.getByText('2 selected')).toBeInTheDocument()
      })
    })

    it('renders chip for file types filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setFileTypes(['jpg', 'png'])
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('File Type:')).toBeInTheDocument()
        expect(screen.getByText('JPG, PNG')).toBeInTheDocument()
      })
    })

    it('renders chip for camera settings filter (ISO)', async () => {
      const setupFilters = (ctx) => {
        ctx.setCameraSettings({
          iso: { min: 100, max: 800 },
        })
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('ISO:')).toBeInTheDocument()
        expect(screen.getByText('100 - 800')).toBeInTheDocument()
      })
    })

    it('renders chip for notes has notes filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setNotes(true, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Notes:')).toBeInTheDocument()
        expect(screen.getByText('Has notes')).toBeInTheDocument()
      })
    })

    it('renders chip for notes keywords filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setNotes(null, 'specimen')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Notes:')).toBeInTheDocument()
        expect(screen.getByText('"specimen"')).toBeInTheDocument()
      })
    })

    it('renders chip for custom field filter', async () => {
      const setupFilters = (ctx) => {
        ctx.setCustomField('location', 'forest')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('location:')).toBeInTheDocument()
        expect(screen.getByText('forest')).toBeInTheDocument()
      })
    })

    it('renders multiple chips for multiple filters', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'any')
        ctx.setSpecies(['Actias luna'], null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
        expect(screen.getByText('Tags:')).toBeInTheDocument()
        expect(screen.getByText('Species:')).toBeInTheDocument()
      })
    })

    it('renders Clear all button when multiple filters active', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'any')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Clear all filters' })).toBeInTheDocument()
      })
    })

    it('does not render Clear all button when only one filter active', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: 'Clear all filters' })).not.toBeInTheDocument()
      })
    })

    it('renders with custom className', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      const { container } = renderWithProvider(
        <ActiveFilterChips className="custom-class" />,
        { setupFilters }
      )

      await waitFor(() => {
        expect(container.firstChild).toHaveClass('custom-class')
      })
    })
  })

  // Interaction tests
  describe('Interactions', () => {
    it('removes individual filter when X clicked', async () => {
      const user = userEvent.setup()
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'any')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
      })

      const removeButton = screen.getByRole('button', { name: 'Remove Date filter' })
      await user.click(removeButton)

      await waitFor(() => {
        expect(screen.queryByText('Date:')).not.toBeInTheDocument()
        expect(screen.getByText('Tags:')).toBeInTheDocument()
      })
    })

    it('removes all filters when Clear all clicked', async () => {
      const user = userEvent.setup()
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'any')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
      })

      const clearAllButton = screen.getByRole('button', { name: 'Clear all filters' })
      await user.click(clearAllButton)

      await waitFor(() => {
        expect(screen.queryByText('Date:')).not.toBeInTheDocument()
        expect(screen.queryByText('Tags:')).not.toBeInTheDocument()
      })
    })

    it('handles keyboard interaction on remove button (Enter)', async () => {
      const user = userEvent.setup()
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
      })

      const removeButton = screen.getByRole('button', { name: 'Remove Date filter' })
      removeButton.focus()
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.queryByText('Date:')).not.toBeInTheDocument()
      })
    })

    it('handles keyboard interaction on remove button (Space)', async () => {
      const user = userEvent.setup()
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
      })

      const removeButton = screen.getByRole('button', { name: 'Remove Date filter' })
      removeButton.focus()
      await user.keyboard(' ')

      await waitFor(() => {
        expect(screen.queryByText('Date:')).not.toBeInTheDocument()
      })
    })
  })

  // Truncation tests
  describe('Value Truncation', () => {
    it('truncates long values with ellipsis', async () => {
      const longValue = 'a'.repeat(50)
      const setupFilters = (ctx) => {
        ctx.setCustomField('field', longValue)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        const valueElement = screen.getByText(/aaa\.\.\./)
        expect(valueElement).toBeInTheDocument()
        expect(valueElement.textContent).toHaveLength(40) // 37 chars + '...'
      })
    })

    it('does not truncate short values', async () => {
      const setupFilters = (ctx) => {
        ctx.setCustomField('field', 'short')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('short')).toBeInTheDocument()
      })
    })

    it('shows full value in title attribute', async () => {
      const longValue = 'a'.repeat(50)
      const setupFilters = (ctx) => {
        ctx.setCustomField('field', longValue)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        const valueElement = screen.getByTitle(longValue)
        expect(valueElement).toBeInTheDocument()
      })
    })
  })

  // Accessibility tests
  describe('Accessibility', () => {
    it('has correct role for container', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByRole('group', { name: 'Active filters' })).toBeInTheDocument()
      })
    })

    it('has correct aria-label for filter chips', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByLabelText('Filter: Date: Last 7 Days')).toBeInTheDocument()
      })
    })

    it('has correct aria-label for remove buttons', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Remove Date filter' })).toBeInTheDocument()
      })
    })

    it('remove button is keyboard focusable', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        const removeButton = screen.getByRole('button', { name: 'Remove Date filter' })
        expect(removeButton).toHaveAttribute('tabIndex', '0')
      })
    })
  })

  // Dark mode tests
  describe('Dark Mode', () => {
    it('applies dark mode classes to chips', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        const chip = screen.getByLabelText('Filter: Date: Last 7 Days')
        expect(chip).toHaveClass('dark:bg-blue-900', 'dark:text-blue-200')
      })
    })

    it('applies dark mode classes to Clear all button', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'any')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        const clearAllButton = screen.getByRole('button', { name: 'Clear all filters' })
        expect(clearAllButton).toHaveClass('dark:text-gray-300', 'dark:hover:bg-gray-700')
      })
    })
  })

  // Edge cases
  describe('Edge Cases', () => {
    it('handles filter with special characters in value', async () => {
      const setupFilters = (ctx) => {
        ctx.setCustomField('field', 'value & <special>')
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('value & <special>')).toBeInTheDocument()
      })
    })

    it('handles empty string in custom field gracefully', async () => {
      const setupFilters = (ctx) => {
        ctx.setCustomField('field', '')
      }

      const { container } = renderWithProvider(<ActiveFilterChips />, { setupFilters })

      // Should not render chip for empty value
      expect(container.firstChild).toBeNull()
    })

    it('updates when filters change', async () => {
      const { rerender } = renderWithProvider(<ActiveFilterChips />, {
        setupFilters: (ctx) => ctx.setDateRange('7days', null, null),
      })

      await waitFor(() => {
        expect(screen.getByText('Last 7 Days')).toBeInTheDocument()
      })

      rerender(
        <FilterProvider>
          <FilterSetup setupFilters={(ctx) => ctx.setDateRange('30days', null, null)}>
            <ActiveFilterChips />
          </FilterSetup>
        </FilterProvider>
      )

      await waitFor(() => {
        expect(screen.getByText('Last 30 Days')).toBeInTheDocument()
      })
    })

    it('handles rapid filter changes', async () => {
      const user = userEvent.setup()
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'any')
        ctx.setSpecies(['Actias luna'], null)
      }

      renderWithProvider(<ActiveFilterChips />, { setupFilters })

      await waitFor(() => {
        expect(screen.getByText('Date:')).toBeInTheDocument()
      })

      // Rapidly click multiple remove buttons
      const dateRemove = screen.getByRole('button', { name: 'Remove Date filter' })
      const tagsRemove = screen.getByRole('button', { name: 'Remove Tags filter' })

      await user.click(dateRemove)
      await user.click(tagsRemove)

      await waitFor(() => {
        expect(screen.queryByText('Date:')).not.toBeInTheDocument()
        expect(screen.queryByText('Tags:')).not.toBeInTheDocument()
        expect(screen.getByText('Species:')).toBeInTheDocument()
      })
    })
  })
})
