/**
 * ActiveFilterChips Usage Examples
 *
 * This file demonstrates how to use the ActiveFilterChips component
 * in different scenarios within the Mothbox application.
 */

import React from 'react'
import { ActiveFilterChips } from '@/components/filters'
import { FilterProvider } from '@/contexts/FilterContext'

/**
 * Example 1: Basic Usage
 * Most common usage - just place it above the gallery
 */
export function BasicExample() {
  return (
    <FilterProvider>
      <div className="space-y-4">
        {/* Active filter chips display */}
        <ActiveFilterChips />

        {/* Your gallery content */}
        <div className="gallery">
          {/* Gallery items... */}
        </div>
      </div>
    </FilterProvider>
  )
}

/**
 * Example 2: With Custom Styling
 * Add custom spacing or styling
 */
export function StyledExample() {
  return (
    <FilterProvider>
      <div className="space-y-4">
        {/* Custom margin and padding */}
        <ActiveFilterChips className="mb-6 px-4" />

        <div className="gallery">
          {/* Gallery items... */}
        </div>
      </div>
    </FilterProvider>
  )
}

/**
 * Example 3: Integrated with Gallery Header
 * Place chips in a header section with other controls
 */
export function IntegratedExample() {
  return (
    <FilterProvider>
      <div className="space-y-4">
        {/* Gallery header */}
        <div className="flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Photo Gallery</h2>
            <div className="flex gap-2">
              {/* Other controls like view toggle, etc. */}
            </div>
          </div>

          {/* Active filter chips */}
          <ActiveFilterChips className="min-h-[32px]" />
        </div>

        <div className="gallery">
          {/* Gallery items... */}
        </div>
      </div>
    </FilterProvider>
  )
}

/**
 * Example 4: Conditional Rendering with Count
 * Show a message when filters are active
 */
export function ConditionalExample() {
  return (
    <FilterProvider>
      {({ hasActiveFilters }) => (
        <div className="space-y-4">
          {hasActiveFilters && (
            <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
              <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                Active filters:
              </p>
              <ActiveFilterChips />
            </div>
          )}

          <div className="gallery">
            {/* Gallery items... */}
          </div>
        </div>
      )}
    </FilterProvider>
  )
}

/**
 * Example 5: Responsive Layout
 * Optimize layout for mobile and desktop
 */
export function ResponsiveExample() {
  return (
    <FilterProvider>
      <div className="space-y-4">
        {/* Scrollable on mobile, wrapped on desktop */}
        <div className="overflow-x-auto lg:overflow-visible">
          <ActiveFilterChips className="whitespace-nowrap lg:whitespace-normal" />
        </div>

        <div className="gallery">
          {/* Gallery items... */}
        </div>
      </div>
    </FilterProvider>
  )
}

/**
 * Integration Notes:
 *
 * 1. The component automatically reads from FilterContext, so ensure it's
 *    wrapped in a FilterProvider.
 *
 * 2. The component returns null when no filters are active, so you don't
 *    need to conditionally render it.
 *
 * 3. Each chip shows the filter type (label) and value, making it clear
 *    what filters are applied.
 *
 * 4. Users can remove individual filters by clicking the X on each chip,
 *    or remove all filters with the "Clear all" button.
 *
 * 5. Long filter values are automatically truncated with ellipsis, but
 *    the full value is shown in a tooltip.
 *
 * 6. The component is fully accessible with keyboard navigation and
 *    screen reader support.
 */
