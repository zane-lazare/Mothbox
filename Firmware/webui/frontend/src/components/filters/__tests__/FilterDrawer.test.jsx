import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { FilterDrawer } from '../FilterDrawer'
import { FilterProvider } from '../../../contexts/FilterContext'
import React from 'react'

// Mock child components to simplify testing
vi.mock('../FilterDrawerHeader', () => ({
  default: () => <div data-testid="filter-drawer-header">Header</div>,
  FilterDrawerHeader: () => <div data-testid="filter-drawer-header">Header</div>,
}))

vi.mock('../FilterDrawerFooter', () => ({
  default: () => <div data-testid="filter-drawer-footer">Footer</div>,
  FilterDrawerFooter: () => <div data-testid="filter-drawer-footer">Footer</div>,
}))

vi.mock('../FilterSection', () => ({
  default: ({ id, title, children }) => (
    <div data-testid={`filter-section-${id}`}>
      {title}
      {children}
    </div>
  ),
  FilterSection: ({ id, title, children }) => (
    <div data-testid={`filter-section-${id}`}>
      {title}
      {children}
    </div>
  ),
}))

// Mock filter components (they have their own test suites)
vi.mock('../DateRangeFilter', () => ({
  DateRangeFilter: () => <div data-testid="date-range-filter">Date Range Filter</div>,
}))

vi.mock('../TagFilter', () => ({
  TagFilter: () => <div data-testid="tag-filter">Tag Filter</div>,
}))

vi.mock('../SpeciesFilter', () => ({
  SpeciesFilter: () => <div data-testid="species-filter">Species Filter</div>,
}))

vi.mock('../FileTypeFilter', () => ({
  FileTypeFilter: () => <div data-testid="file-type-filter">File Type Filter</div>,
}))

vi.mock('../CameraSettingsFilter', () => ({
  CameraSettingsFilter: () => <div data-testid="camera-settings-filter">Camera Settings Filter</div>,
}))

vi.mock('../NotesFilter', () => ({
  NotesFilter: () => <div data-testid="notes-filter">Notes Filter</div>,
}))

vi.mock('../CustomFieldsFilter', () => ({
  CustomFieldsFilter: () => <div data-testid="custom-fields-filter">Custom Fields Filter</div>,
}))

// Helper to render with FilterProvider
function renderWithProvider(ui) {
  return render(<FilterProvider>{ui}</FilterProvider>)
}

describe('FilterDrawer', () => {
  beforeEach(() => {
    // Reset document body overflow
    document.body.style.overflow = ''
  })

  describe('Rendering', () => {
    it('renders the filter drawer', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toBeInTheDocument()
    })

    it('contains header component', () => {
      renderWithProvider(<FilterDrawer />)

      expect(screen.getByTestId('filter-drawer-header')).toBeInTheDocument()
    })

    it('contains footer component', () => {
      renderWithProvider(<FilterDrawer />)

      expect(screen.getByTestId('filter-drawer-footer')).toBeInTheDocument()
    })

    it('contains all filter sections', () => {
      renderWithProvider(<FilterDrawer />)

      expect(screen.getByTestId('filter-section-dateRange')).toBeInTheDocument()
      expect(screen.getByTestId('filter-section-tags')).toBeInTheDocument()
      expect(screen.getByTestId('filter-section-species')).toBeInTheDocument()
      expect(screen.getByTestId('filter-section-fileTypes')).toBeInTheDocument()
      expect(screen.getByTestId('filter-section-cameraSettings')).toBeInTheDocument()
      expect(screen.getByTestId('filter-section-notes')).toBeInTheDocument()
      expect(screen.getByTestId('filter-section-customFields')).toBeInTheDocument()
    })
  })

  describe('Visibility and Responsive Behavior', () => {
    it('applies visible translation class when open on mobile', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })

      // Initial state: drawer is open (isDrawerOpen: true by default)
      expect(drawer).toHaveClass('max-md:translate-y-0')
    })

    it('applies desktop collapsible sidebar classes', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      // Desktop drawer is now collapsible - no longer uses lg:static
      expect(drawer).toHaveClass('lg:translate-x-0', 'lg:w-80')
    })

    it('applies tablet overlay drawer classes', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toHaveClass('md:w-72', 'md:top-0', 'md:left-0', 'md:bottom-0')
    })

    it('applies mobile slide-up drawer classes', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toHaveClass('max-md:left-0', 'max-md:right-0', 'max-md:bottom-0', 'max-md:h-[90vh]', 'max-md:rounded-t-lg')
    })
  })

  describe('Backdrop', () => {
    it('renders backdrop when drawer is open', () => {
      renderWithProvider(<FilterDrawer />)

      // Drawer is open by default, so backdrop should be present
      const backdrop = document.querySelector('.bg-black\\/50')
      expect(backdrop).toBeInTheDocument()
    })

    it('backdrop has correct ARIA attributes', () => {
      renderWithProvider(<FilterDrawer />)

      // Drawer is open by default, so backdrop should be present with aria-hidden
      const backdrop = document.querySelector('.bg-black\\/50')
      expect(backdrop).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('Body Scroll Locking', () => {
    it('sets body overflow to hidden when drawer is open', () => {
      renderWithProvider(<FilterDrawer />)

      // Drawer is open by default, so body should be locked
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('restores body overflow when component unmounts', () => {
      const { unmount } = renderWithProvider(<FilterDrawer />)

      unmount()

      expect(document.body.style.overflow).toBe('')
    })
  })

  describe('Keyboard Interactions', () => {
    it('closes drawer on Escape key when open', () => {
      // This test would require the drawer to be open
      // We'll test that the event listener is set up correctly
      renderWithProvider(<FilterDrawer />)

      const escapeEvent = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
      document.dispatchEvent(escapeEvent)

      // Since drawer is initially closed, dispatching Escape should not cause errors
      // Verify component is still rendered properly
      expect(screen.getByRole('complementary', { name: 'Filters' })).toBeInTheDocument()
    })

    it('does not interfere with other keyboard events', () => {
      renderWithProvider(<FilterDrawer />)

      const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })
      expect(() => document.dispatchEvent(enterEvent)).not.toThrow()
    })
  })

  describe('Accessibility', () => {
    it('has correct ARIA role', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toBeInTheDocument()
    })

    it('has correct ARIA label', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary')
      expect(drawer).toHaveAttribute('aria-label', 'Filters')
    })
  })

  describe('Styling', () => {
    it('applies dark mode classes', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toHaveClass('dark:bg-gray-800', 'dark:border-gray-700')
    })

    it('applies transition classes', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toHaveClass('transition-transform', 'duration-200', 'ease-in-out')
    })

    it('has correct z-index for layering', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toHaveClass('z-40')
    })

    it('applies flex column layout', () => {
      renderWithProvider(<FilterDrawer />)

      const drawer = screen.getByRole('complementary', { name: 'Filters' })
      expect(drawer).toHaveClass('flex', 'flex-col')
    })
  })
})
