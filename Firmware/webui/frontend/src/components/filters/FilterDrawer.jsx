import { useEffect } from 'react'
import PropTypes from 'prop-types'
import { useFilterContext } from '../../contexts/FilterContext'
import FilterDrawerHeader from './FilterDrawerHeader'
import FilterDrawerFooter from './FilterDrawerFooter'
import FilterSection from './FilterSection'

/**
 * FilterDrawer Component
 *
 * Main filter drawer container with responsive layout:
 * - Desktop (≥1024px): Fixed left sidebar, 320px width
 * - Tablet (768-1023px): Overlay drawer, 280px width, backdrop click to close
 * - Mobile (<768px): Full-width slide-up drawer from bottom
 *
 * @component
 * @example
 * <FilterDrawer />
 */
export function FilterDrawer() {
  const { isDrawerOpen, toggleDrawer } = useFilterContext()

  // Handle Escape key to close drawer
  useEffect(() => {
    if (!isDrawerOpen) return

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        toggleDrawer()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isDrawerOpen, toggleDrawer])

  // Prevent body scroll when drawer is open on mobile/tablet
  useEffect(() => {
    if (isDrawerOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [isDrawerOpen])

  // Handle backdrop click (tablet/mobile only)
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      toggleDrawer()
    }
  }

  return (
    <>
      {/* Backdrop for tablet/mobile - Only shown when drawer is open */}
      {isDrawerOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={handleBackdropClick}
          aria-hidden="true"
        />
      )}

      {/* Filter Drawer */}
      <aside
        role="complementary"
        aria-label="Filters"
        className={`
          fixed bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700
          transition-transform duration-200 ease-in-out z-40
          flex flex-col

          /* Desktop (≥1024px): Fixed left sidebar */
          lg:static lg:translate-x-0 lg:w-80

          /* Tablet (768-1023px): Overlay drawer from left */
          md:w-72 md:top-0 md:left-0 md:bottom-0
          ${isDrawerOpen ? 'md:translate-x-0' : 'md:-translate-x-full'}

          /* Mobile (<768px): Full-width slide-up drawer from bottom */
          max-md:left-0 max-md:right-0 max-md:bottom-0 max-md:h-[90vh] max-md:rounded-t-lg
          ${isDrawerOpen ? 'max-md:translate-y-0' : 'max-md:translate-y-full'}
        `}
      >
        <FilterDrawerHeader />

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          <FilterSection id="dateRange" title="Date Range" defaultExpanded={true}>
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              Date Range Filter (Coming Soon)
            </div>
          </FilterSection>

          <FilterSection id="tags" title="Tags">
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              Tag Filter (Coming Soon)
            </div>
          </FilterSection>

          <FilterSection id="species" title="Species">
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              Species Filter (Coming Soon)
            </div>
          </FilterSection>

          <FilterSection id="fileTypes" title="File Types">
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              File Type Filter (Coming Soon)
            </div>
          </FilterSection>

          <FilterSection id="cameraSettings" title="Camera Settings">
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              Camera Settings Filter (Coming Soon)
            </div>
          </FilterSection>

          <FilterSection id="notes" title="Notes">
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              Notes Filter (Coming Soon)
            </div>
          </FilterSection>

          <FilterSection id="customFields" title="Custom Fields">
            <div className="p-4 text-gray-500 dark:text-gray-400 text-sm">
              Custom Fields Filter (Coming Soon)
            </div>
          </FilterSection>
        </div>

        <FilterDrawerFooter />
      </aside>
    </>
  )
}

FilterDrawer.propTypes = {}

export default FilterDrawer
