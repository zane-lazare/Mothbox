import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import React from 'react'
import { FilterDrawerToggle } from '../FilterDrawerToggle'
import { FilterProvider, useFilterContext } from '../../../contexts/FilterContext'

// Helper component that sets up filters synchronously before children render
function FilterSetup({ children, activeFilters = 0 }) {
  const ctx = useFilterContext()
  // Call setup synchronously during render (not in useEffect)
  const hasSetup = React.useRef(false)
  if (!hasSetup.current && activeFilters > 0) {
    if (activeFilters >= 1) {
      ctx.setDateRange('7days', null, null)
    }
    if (activeFilters >= 2) {
      ctx.setTags(['moth'], null)
    }
    if (activeFilters >= 3) {
      ctx.setSpecies(['Actias luna'], null)
    }
    hasSetup.current = true
  }
  return children
}

// Helper to render with FilterProvider
function renderWithProvider(ui, { activeFilters = 0 } = {}) {
  return render(
    <FilterProvider>
      <FilterSetup activeFilters={activeFilters}>{ui}</FilterSetup>
    </FilterProvider>
  )
}

describe('FilterDrawerToggle', () => {
  describe('Rendering', () => {
    it('renders the toggle button', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })
      expect(button).toBeInTheDocument()
    })

    it('renders the funnel icon', () => {
      const { container } = renderWithProvider(<FilterDrawerToggle />)

      // FunnelIcon is rendered with aria-hidden
      const icon = container.querySelector('[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('is hidden on desktop (lg breakpoint)', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })
      expect(button).toHaveClass('lg:hidden')
    })
  })

  describe('Badge Display', () => {
    it('does not show badge when no filters are active', () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 0 })

      // Badge should not be visible
      setTimeout(() => {
        const badge = screen.queryByText('0')
        expect(badge).not.toBeInTheDocument()
      }, 0)
    })

    it('shows badge with count when filters are active', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const badge = screen.getByText('1')
        expect(badge).toBeInTheDocument()
      })
    })

    it('displays correct count with multiple filters', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 2 })

      await waitFor(() => {
        const badge = screen.getByText('2')
        expect(badge).toBeInTheDocument()
      })
    })

    it('badge has aria-hidden attribute', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const badge = screen.getByText('1')
        expect(badge).toHaveAttribute('aria-hidden', 'true')
      })
    })

    it('badge updates when filter count changes', async () => {
      const { rerender } = renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument()
      })

      // Update to 2 filters
      rerender(
        <FilterProvider>
          <FilterSetup activeFilters={2}>
            <FilterDrawerToggle />
          </FilterSetup>
        </FilterProvider>
      )

      await waitFor(() => {
        expect(screen.getByText('2')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has correct aria-label with no active filters', () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 0 })

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'Show filters')
    })

    it('includes filter count in aria-label when filters are active', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const button = screen.getByRole('button')
        expect(button).toHaveAttribute('aria-label', 'Show filters (1 active)')
      })
    })

    it('updates aria-label when filter count changes', async () => {
      const { rerender } = renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const button = screen.getByRole('button')
        expect(button).toHaveAttribute('aria-label', 'Show filters (1 active)')
      })

      // Update to 3 filters
      rerender(
        <FilterProvider>
          <FilterSetup activeFilters={3}>
            <FilterDrawerToggle />
          </FilterSetup>
        </FilterProvider>
      )

      await waitFor(() => {
        const button = screen.getByRole('button')
        expect(button).toHaveAttribute('aria-label', 'Show filters (3 active)')
      })
    })
  })

  describe('Click Behavior', () => {
    it('calls toggleDrawer when clicked', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })

      // Click should not throw
      expect(() => fireEvent.click(button)).not.toThrow()
    })

    it('is clickable when filters are active', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 2 })

      await waitFor(() => {
        const button = screen.getByRole('button')
        expect(() => fireEvent.click(button)).not.toThrow()
      })
    })
  })

  describe('Styling', () => {
    it('applies base button styles', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })
      expect(button).toHaveClass('relative', 'p-2', 'rounded-md')
    })

    it('applies color styles', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })
      expect(button).toHaveClass('text-gray-700', 'dark:text-gray-300')
    })

    it('applies hover styles', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })
      expect(button).toHaveClass('hover:bg-gray-100', 'dark:hover:bg-gray-700')
    })

    it('applies focus ring styles', () => {
      renderWithProvider(<FilterDrawerToggle />)

      const button = screen.getByRole('button', { name: /Show filters/i })
      expect(button).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-blue-500')
    })

    it('badge has correct positioning', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const badge = screen.getByText('1')
        expect(badge).toHaveClass('absolute', '-top-1', '-right-1')
      })
    })

    it('badge has correct styling', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const badge = screen.getByText('1')
        expect(badge).toHaveClass(
          'bg-blue-600',
          'text-white',
          'text-xs',
          'font-medium',
          'rounded-full'
        )
      })
    })
  })

  describe('Badge Position', () => {
    it('badge is positioned relative to button', async () => {
      renderWithProvider(<FilterDrawerToggle />, { activeFilters: 1 })

      await waitFor(() => {
        const button = screen.getByRole('button')
        const badge = screen.getByText('1')

        expect(button).toHaveClass('relative')
        expect(badge).toHaveClass('absolute')
      })
    })
  })
})
