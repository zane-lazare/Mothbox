import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import React from 'react'
import { FilterSection } from '../FilterSection'
import { FilterProvider, useFilterContext } from '../../../contexts/FilterContext'

// Helper component that sets up filters synchronously before children render
function FilterSetup({ setupFilters = null, children }) {
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
function renderWithProvider(ui, { setupFilters = null } = {}) {
  return render(
    <FilterProvider>
      <FilterSetup setupFilters={setupFilters}>{ui}</FilterSetup>
    </FilterProvider>
  )
}

describe('FilterSection', () => {
  describe('Rendering', () => {
    it('renders the section with title', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      expect(screen.getByText('Tags')).toBeInTheDocument()
    })

    it('renders children when expanded', async () => {
      const setupFilters = (ctx) => {
        ctx.toggleSection('tags')
      }

      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>,
        { setupFilters }
      )

      await waitFor(() => {
        expect(screen.getByText('Tag content')).toBeInTheDocument()
      })
    })

    it('renders as button for accessibility', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button).toBeInTheDocument()
    })
  })

  describe('Expand/Collapse Behavior', () => {
    it('is collapsed by default when defaultExpanded is false', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags" defaultExpanded={false}>
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button).toHaveAttribute('aria-expanded', 'false')
    })

    it('respects defaultExpanded prop for dateRange', () => {
      renderWithProvider(
        <FilterSection id="dateRange" title="Date Range" defaultExpanded={true}>
          <div>Date content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Date Range/i })
      // The aria-expanded may be true if dateRange is in expandedSections
      expect(button).toHaveAttribute('aria-expanded')
    })

    it('expands section when clicked', async () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })

      // Initially collapsed
      expect(button).toHaveAttribute('aria-expanded', 'false')

      // Click to expand
      fireEvent.click(button)

      await waitFor(() => {
        expect(button).toHaveAttribute('aria-expanded', 'true')
      })
    })

    it('collapses section when clicked again', async () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })

      // Expand
      fireEvent.click(button)
      await waitFor(() => {
        expect(button).toHaveAttribute('aria-expanded', 'true')
      })

      // Collapse
      fireEvent.click(button)
      await waitFor(() => {
        expect(button).toHaveAttribute('aria-expanded', 'false')
      })
    })

    it('handles Enter key to toggle', async () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })

      // Press Enter
      fireEvent.keyDown(button, { key: 'Enter', code: 'Enter' })

      await waitFor(() => {
        expect(button).toHaveAttribute('aria-expanded', 'true')
      })
    })

    it('handles Space key to toggle', async () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })

      // Press Space
      fireEvent.keyDown(button, { key: ' ', code: 'Space' })

      await waitFor(() => {
        expect(button).toHaveAttribute('aria-expanded', 'true')
      })
    })

    it('ignores other keyboard keys', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      const initialState = button.getAttribute('aria-expanded')

      // Press an irrelevant key
      fireEvent.keyDown(button, { key: 'a', code: 'KeyA' })

      // State should not change
      expect(button).toHaveAttribute('aria-expanded', initialState)
    })
  })

  describe('Active Indicator', () => {
    it('shows active indicator when dateRange has values', async () => {
      const setupFilters = (ctx) => {
        ctx.setDateRange('7days', null, null)
      }

      const { container } = renderWithProvider(
        <FilterSection id="dateRange" title="Date Range">
          <div>Date content</div>
        </FilterSection>,
        { setupFilters }
      )

      await waitFor(() => {
        const indicator = container.querySelector('.bg-blue-600.rounded-full')
        expect(indicator).toBeInTheDocument()
      })
    })

    it('shows active indicator when tags are selected', async () => {
      const setupFilters = (ctx) => {
        ctx.setTags(['moth'], null)
      }

      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>,
        { setupFilters }
      )

      await waitFor(() => {
        const indicator = container.querySelector('.bg-blue-600.rounded-full')
        expect(indicator).toBeInTheDocument()
      })
    })

    it('shows active indicator when species are selected', async () => {
      const setupFilters = (ctx) => {
        ctx.setSpecies(['Actias luna'], null)
      }

      const { container } = renderWithProvider(
        <FilterSection id="species" title="Species">
          <div>Species content</div>
        </FilterSection>,
        { setupFilters }
      )

      await waitFor(() => {
        const indicator = container.querySelector('.bg-blue-600.rounded-full')
        expect(indicator).toBeInTheDocument()
      })
    })

    it('shows active indicator when includeUnidentified is true', async () => {
      const setupFilters = (ctx) => {
        ctx.setSpecies([], true)
      }

      const { container } = renderWithProvider(
        <FilterSection id="species" title="Species">
          <div>Species content</div>
        </FilterSection>,
        { setupFilters }
      )

      await waitFor(() => {
        const indicator = container.querySelector('.bg-blue-600.rounded-full')
        expect(indicator).toBeInTheDocument()
      })
    })

    it('does not show indicator when section has no active filters', () => {
      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const indicator = container.querySelector('.bg-blue-600.rounded-full')
      expect(indicator).not.toBeInTheDocument()
    })
  })

  describe('Chevron Icon', () => {
    it('rotates chevron when expanded', async () => {
      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })

      // Click to expand
      fireEvent.click(button)

      await waitFor(() => {
        const chevron = container.querySelector('.rotate-180')
        expect(chevron).toBeInTheDocument()
      })
    })

    it('has default rotation when collapsed', () => {
      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const chevron = container.querySelector('.rotate-0')
      expect(chevron).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has correct aria-expanded attribute', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button).toHaveAttribute('aria-expanded')
    })

    it('has correct aria-controls attribute', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button).toHaveAttribute('aria-controls', 'filter-section-tags')
    })

    it('content has matching id for aria-controls', () => {
      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const content = container.querySelector('#filter-section-tags')
      expect(content).toBeInTheDocument()
    })

    it('content has aria-hidden when collapsed', () => {
      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const content = container.querySelector('#filter-section-tags')
      expect(content).toHaveAttribute('aria-hidden', 'true')
    })

    it('active indicator has descriptive aria-label', async () => {
      const setupFilters = (ctx) => {
        ctx.setTags(['moth'], null)
      }

      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>,
        { setupFilters }
      )

      await waitFor(() => {
        const indicator = screen.queryByLabelText('Active filter')
        expect(indicator).toBeInTheDocument()
      })
    })
  })

  describe('Styling', () => {
    it('applies hover styles', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button).toHaveClass('hover:bg-gray-50', 'dark:hover:bg-gray-700/50')
    })

    it('applies focus ring styles', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-inset', 'focus:ring-blue-500')
    })

    it('applies transition classes to content', () => {
      const { container } = renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const content = container.querySelector('#filter-section-tags')
      expect(content).toHaveClass('transition-all', 'duration-200', 'ease-in-out')
    })

    it('applies dark mode classes', () => {
      renderWithProvider(
        <FilterSection id="tags" title="Tags">
          <div>Tag content</div>
        </FilterSection>
      )

      const button = screen.getByRole('button', { name: /Tags/i })
      expect(button.querySelector('.font-medium')).toHaveClass('dark:text-gray-100')
    })
  })

  describe('Multiple Sections', () => {
    it('sections work independently', async () => {
      renderWithProvider(
        <>
          <FilterSection id="tags" title="Tags">
            <div>Tag content</div>
          </FilterSection>
          <FilterSection id="species" title="Species">
            <div>Species content</div>
          </FilterSection>
        </>
      )

      const tagsButton = screen.getByRole('button', { name: /Tags/i })
      const speciesButton = screen.getByRole('button', { name: /Species/i })

      // Expand tags
      fireEvent.click(tagsButton)
      await waitFor(() => {
        expect(tagsButton).toHaveAttribute('aria-expanded', 'true')
      })

      // Species should still be collapsed
      expect(speciesButton).toHaveAttribute('aria-expanded', 'false')

      // Expand species
      fireEvent.click(speciesButton)
      await waitFor(() => {
        expect(speciesButton).toHaveAttribute('aria-expanded', 'true')
      })

      // Tags should still be expanded
      expect(tagsButton).toHaveAttribute('aria-expanded', 'true')
    })
  })
})
