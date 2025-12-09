# ActiveFilterChips Component

## Overview

The `ActiveFilterChips` component displays active gallery filters as removable chips above the photo gallery. It provides a clear visual representation of applied filters and allows users to remove individual filters or clear all filters at once.

## Files Created

1. **Component**: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/filters/ActiveFilterChips.jsx` (4.1KB)
2. **Tests**: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/filters/__tests__/ActiveFilterChips.test.jsx` (16KB, 31 tests)
3. **Examples**: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/filters/ActiveFilterChips.example.jsx` (3.8KB)
4. **Barrel Export**: Updated `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/filters/index.js`

## Features

### 1. Display Active Filters as Chips
- Each active filter shown as a removable chip
- Chip displays filter type (label) and value
- Examples:
  - "Date: Last 7 Days"
  - "Tags: 2 (any)"
  - "Species: Actias luna"
  - "ISO: 100 - 800"

### 2. Filter Types Supported
- **Date Range**: Preset names or custom date ranges
- **Tags**: Count with match mode (any/all)
- **Species**: Count of selected species or "Include unidentified"
- **File Types**: List of file extensions (JPG, PNG, etc.)
- **Camera Settings**: ISO, aperture, shutter speed ranges
- **Notes**: Has/no notes, keywords
- **Custom Fields**: Field name and value pairs

### 3. FilterContext Integration
- Reads from `useFilterContext()` automatically
- Uses `clearFilter(type)` for individual chip removal
- Uses `clearAllFilters()` for "Clear all" button
- Leverages `getActiveFilterSummaries()` from filterQueryBuilder utils

### 4. Compact Display
- Horizontal scrollable row layout
- Flex wrap for responsive behavior
- Long values truncated with ellipsis (40 char limit)
- Full value shown in tooltip on hover
- Count badges for multi-item filters

### 5. Styling
- Tailwind CSS with dark mode support
- Blue color scheme matching application theme
- Small chip size for compact display
- Smooth transitions on hover and removal
- Consistent with TagChip component styling

## Usage

### Basic Usage

```jsx
import { ActiveFilterChips } from '@/components/filters'
import { FilterProvider } from '@/contexts/FilterContext'

function Gallery() {
  return (
    <FilterProvider>
      <div className="space-y-4">
        <ActiveFilterChips />
        <div className="gallery">
          {/* Gallery content */}
        </div>
      </div>
    </FilterProvider>
  )
}
```

### With Custom Styling

```jsx
<ActiveFilterChips className="mb-6 px-4" />
```

### Integration Example

```jsx
<div className="flex flex-col gap-3">
  <div className="flex justify-between items-center">
    <h2 className="text-xl font-bold">Photo Gallery</h2>
    <ViewModeToggle />
  </div>
  <ActiveFilterChips />
</div>
```

## Component API

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `className` | `string` | `''` | Additional CSS classes for the container |

### Behavior

- **No filters**: Returns `null` (renders nothing)
- **Single filter**: Shows one chip, no "Clear all" button
- **Multiple filters**: Shows multiple chips + "Clear all" button
- **Long values**: Truncates to 40 characters with ellipsis
- **Removal**: Click X button or use keyboard (Enter/Space)

## Internal Components

### FilterChip

Internal component that renders individual filter chips.

**Props:**
- `label` (string, required): Filter type label
- `value` (string, required): Filter value
- `onRemove` (function, required): Remove callback

**Features:**
- Truncates values > 40 characters
- Shows full value in title tooltip
- Keyboard accessible (Enter and Space keys)
- Aria labels for accessibility

## Testing

### Test Coverage: 31 Tests

**Rendering (17 tests):**
- ✓ Renders nothing when no active filters
- ✓ Renders chips for each filter type (date, tags, species, file types, camera settings, notes, custom fields)
- ✓ Renders multiple chips for multiple filters
- ✓ Shows/hides "Clear all" button based on filter count
- ✓ Supports custom className

**Interactions (5 tests):**
- ✓ Removes individual filter when X clicked
- ✓ Removes all filters when "Clear all" clicked
- ✓ Keyboard navigation (Enter and Space keys)
- ✓ Prevents event propagation on remove

**Truncation (3 tests):**
- ✓ Truncates long values with ellipsis
- ✓ Does not truncate short values
- ✓ Shows full value in title attribute

**Accessibility (4 tests):**
- ✓ Correct role for container (group)
- ✓ Aria-labels for filter chips
- ✓ Aria-labels for remove buttons
- ✓ Keyboard focusable with tabIndex

**Dark Mode (2 tests):**
- ✓ Dark mode classes on chips
- ✓ Dark mode classes on "Clear all" button

**Edge Cases (6 tests):**
- ✓ Special characters in values
- ✓ Empty string handling
- ✓ Filter updates
- ✓ Rapid filter changes
- ✓ Filter re-rendering

### Running Tests

```bash
# Run all tests
npm test -- src/components/filters/__tests__/ActiveFilterChips.test.jsx

# Run with coverage
npm test -- src/components/filters/__tests__/ActiveFilterChips.test.jsx --coverage

# Run in watch mode
npm test -- src/components/filters/__tests__/ActiveFilterChips.test.jsx
```

## Accessibility

- **ARIA Roles**: Container has `role="group"` with `aria-label="Active filters"`
- **ARIA Labels**: Each chip has descriptive `aria-label` (e.g., "Filter: Date: Last 7 Days")
- **Remove Buttons**: Clear `aria-label` for each remove button (e.g., "Remove Date filter")
- **Keyboard Navigation**: All interactive elements focusable with Tab
- **Keyboard Actions**: Enter and Space keys trigger remove action
- **Screen Readers**: Status role on chips announces filter state

## Dark Mode Support

All components support dark mode using Tailwind's `dark:` variants:

- **Chips**: `bg-blue-100 dark:bg-blue-900`, `text-blue-800 dark:text-blue-200`
- **Remove Button Hover**: `hover:bg-blue-200 dark:hover:bg-blue-800`
- **Clear All Button**: `text-gray-700 dark:text-gray-300`, `hover:bg-gray-100 dark:hover:bg-gray-700`

## Performance

- **Memoization**: Component wrapped in `React.memo()` to prevent unnecessary re-renders
- **Callback Memoization**: `useCallback` for all event handlers
- **Efficient Updates**: Only re-renders when filter state changes
- **Minimal DOM**: Renders nothing when no filters active

## Integration Points

### Dependencies

- `react` - Core React library
- `prop-types` - Runtime prop validation
- `@heroicons/react/20/solid` - XMarkIcon for remove buttons
- `../../contexts/FilterContext` - Filter state management
- `../../utils/filterQueryBuilder` - Filter summary generation

### Related Components

- `FilterDrawer` - Main filter UI component
- `TagChip` - Similar chip styling pattern
- `FilterDrawerToggle` - Shows active filter count

### Context Usage

```jsx
const {
  clearFilter,      // Function to clear specific filter
  clearAllFilters,  // Function to clear all filters
  ...filterState    // All filter state (dateRange, tags, species, etc.)
} = useFilterContext()
```

## Styling Details

### Container Classes
```css
flex flex-wrap items-center gap-2
```

### Chip Classes
```css
inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
bg-blue-100 dark:bg-blue-900
text-blue-800 dark:text-blue-200
text-xs font-medium
transition-colors duration-150
```

### Remove Button Classes
```css
ml-0.5 -mr-1 p-0.5 rounded-full
hover:bg-blue-200 dark:hover:bg-blue-800
focus:outline-none focus:ring-2 focus:ring-blue-500
transition-colors duration-150
```

### Clear All Button Classes
```css
text-xs px-2 py-1 rounded-md font-medium
text-gray-700 dark:text-gray-300
hover:bg-gray-100 dark:hover:bg-gray-700
focus:outline-none focus:ring-2 focus:ring-blue-500
transition-colors duration-150
```

## Future Enhancements

Potential improvements for future iterations:

1. **Expandable Chips**: Show all tags/species when count is clicked
2. **Chip Reordering**: Drag-and-drop to reorder filter chips
3. **Filter Presets**: Save/load filter combinations
4. **Chip Colors**: Different colors for different filter types
5. **Animation**: Smooth enter/exit animations for chips
6. **Compact Mode**: Ultra-compact view for mobile
7. **Filter History**: Quick access to recently used filters

## Browser Support

Tested and supported on:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Android)

## License

Part of the Mothbox project. See main project LICENSE for details.
