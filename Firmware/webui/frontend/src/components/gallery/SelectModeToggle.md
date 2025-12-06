# SelectModeToggle Component

## Overview

The `SelectModeToggle` component is a toggle button that allows users to enter and exit photo selection mode in the gallery. It integrates with the `SelectionContext` to manage selection state across the application.

## Features

- ✅ Toggle between "Select" and "Cancel" modes
- ✅ Visual feedback with different states (active/inactive)
- ✅ Keyboard accessible (Enter and Space keys)
- ✅ Screen reader support with ARIA attributes
- ✅ Icons from Heroicons (CheckCircleIcon and XMarkIcon)
- ✅ Styling matches ViewModeToggle pattern
- ✅ 100% test coverage (25 tests)

## Usage

### Basic Usage

```jsx
import SelectModeToggle from './components/gallery/SelectModeToggle'
import { SelectionProvider } from './contexts/SelectionContext'

function App() {
  return (
    <SelectionProvider>
      <SelectModeToggle />
    </SelectionProvider>
  )
}
```

### With Gallery Integration

```jsx
import { SelectionProvider } from './contexts/SelectionContext'
import SelectModeToggle from './components/gallery/SelectModeToggle'
import PhotoGrid from './components/PhotoGrid'

function Gallery() {
  return (
    <SelectionProvider>
      <div className="gallery-toolbar">
        <SelectModeToggle />
        {/* Other toolbar items */}
      </div>
      <PhotoGrid />
    </SelectionProvider>
  )
}
```

## Dependencies

### Context
- `SelectionContext` - Provides `isSelectMode` state and `toggleSelectMode` action
- Must be wrapped in `SelectionProvider`

### Hooks
- `useSelection` - Hook to access SelectionContext

### Icons
- `CheckCircleIcon` from `@heroicons/react/24/outline` - Shown in "Select" state
- `XMarkIcon` from `@heroicons/react/24/outline` - Shown in "Cancel" state

## Component API

### Props

None - The component is controlled entirely by `SelectionContext`.

### Context Values Used

```typescript
{
  isSelectMode: boolean,        // Current selection mode state
  toggleSelectMode: () => void  // Function to toggle selection mode
}
```

## Visual States

### Inactive State (Select Mode)
- Shows CheckCircleIcon
- Shows "Select" text
- White background with gray border
- `aria-pressed="false"`

### Active State (Cancel Mode)
- Shows XMarkIcon
- Shows "Cancel" text
- Blue background (bg-blue-600)
- White text
- `aria-pressed="true"`

## Accessibility

### ARIA Attributes
- `role="button"` - Implicit from `<button>` element
- `aria-pressed` - Indicates toggle state (true/false)
- `aria-label` - Descriptive label for screen readers
  - Inactive: "Enter selection mode"
  - Active: "Exit selection mode"
- `aria-hidden="true"` on icons - Icons are decorative

### Keyboard Support
- **Enter** - Toggles selection mode
- **Space** - Toggles selection mode
- **Tab** - Focuses the button (standard browser behavior)

### Focus Management
- Visible focus ring (Tailwind: `focus:ring-2 focus:ring-blue-500`)
- `focus:outline-none` to use custom focus styling

## Styling

### CSS Classes

The component uses Tailwind CSS classes following the ViewModeToggle pattern:

```javascript
// Base classes (all states)
'flex items-center gap-2 px-3 py-2 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500'

// Inactive state
'bg-white hover:bg-gray-50 text-gray-700 border border-gray-300'

// Active state
'bg-blue-600 hover:bg-blue-700 text-white font-medium shadow'
```

### Customization

To customize styling, modify the class strings in the component:

```jsx
const baseButtonClasses = '...'  // Modify base styles
const activeClasses = '...'      // Modify active state
const inactiveClasses = '...'    // Modify inactive state
```

## Testing

### Test Coverage
- 100% statements, branches, functions, and lines
- 25 tests covering all functionality

### Test Files
- `/src/components/gallery/__tests__/SelectModeToggle.test.jsx`

### Test Categories
1. **Rendering** (7 tests)
   - Button element existence
   - Text and icon display
   - ARIA attributes

2. **Interaction** (5 tests)
   - Click handling
   - Toggle behavior
   - Keyboard accessibility

3. **Styling** (4 tests)
   - CSS classes
   - Visual state changes
   - Icon styling

4. **Accessibility** (5 tests)
   - ARIA labels
   - Role attributes
   - Focus states

5. **Integration** (2 tests)
   - Context state reflection
   - Multiple instances

6. **Edge Cases** (2 tests)
   - Rapid clicking
   - Error handling

### Running Tests

```bash
# Run component tests
npm test -- SelectModeToggle --run

# Run with coverage
npm test -- SelectModeToggle --run --coverage

# Watch mode
npm test -- SelectModeToggle
```

## Implementation Details

### State Management
- Uses `useSelection` hook to access `SelectionContext`
- State is managed by `SelectionProvider` reducer
- Clicking the button dispatches `TOGGLE_SELECT_MODE` action
- Exiting select mode automatically clears selected photos

### Performance
- No internal state - fully controlled by context
- Memoized callbacks in context prevent unnecessary re-renders
- Lightweight component with minimal re-render triggers

### Error Handling
- Throws error if used outside `SelectionProvider`
- Error message: "useSelection must be used within SelectionProvider"

## Examples

### Example 1: Basic Toggle

```jsx
import { SelectionProvider } from './contexts/SelectionContext'
import SelectModeToggle from './components/gallery/SelectModeToggle'

function Example1() {
  return (
    <SelectionProvider>
      <div className="p-4">
        <SelectModeToggle />
      </div>
    </SelectionProvider>
  )
}
```

### Example 2: Multiple Toggles (Shared State)

```jsx
import { SelectionProvider } from './contexts/SelectionContext'
import SelectModeToggle from './components/gallery/SelectModeToggle'

function Example2() {
  return (
    <SelectionProvider>
      <header>
        <SelectModeToggle />
      </header>
      <footer>
        <SelectModeToggle />
      </footer>
      {/* Both buttons reflect the same state */}
    </SelectionProvider>
  )
}
```

### Example 3: With Selection Status

```jsx
import { SelectionProvider } from './contexts/SelectionContext'
import SelectModeToggle from './components/gallery/SelectModeToggle'
import useSelection from './hooks/useSelection'

function SelectionStatus() {
  const { selectedCount, isSelectMode } = useSelection()

  return (
    <div className="flex items-center gap-4">
      <SelectModeToggle />
      {isSelectMode && (
        <span className="text-sm text-gray-600">
          {selectedCount} photo{selectedCount !== 1 ? 's' : ''} selected
        </span>
      )}
    </div>
  )
}

function Example3() {
  return (
    <SelectionProvider>
      <SelectionStatus />
    </SelectionProvider>
  )
}
```

## Related Components

- **SelectionContext** - Provides selection state management
- **useSelection** - Hook to access selection context
- **ViewModeToggle** - Similar toggle component for view modes
- **PhotoGridItem** - Uses selection context to show selection UI

## Browser Support

- Modern browsers with ES6+ support
- Tailwind CSS v3+
- React 18+

## Changelog

### v1.0.0 (2025-12-06)
- Initial implementation
- TDD approach with 25 tests
- 100% test coverage
- Full accessibility support
- Integration with SelectionContext

## Future Enhancements

Potential improvements for future iterations:

1. **Animation** - Add smooth transitions for icon/text changes
2. **Badge** - Show selected count in the button
3. **Tooltip** - Add tooltip for additional context
4. **Dark Mode** - Add dark mode variants
5. **Mobile** - Optimize touch target size for mobile devices
6. **Shortcuts** - Add keyboard shortcut indicator (e.g., "Ctrl+A")

## Troubleshooting

### Component not rendering
**Problem**: Component throws error or doesn't render
**Solution**: Ensure component is wrapped in `SelectionProvider`

```jsx
// ❌ Wrong
<SelectModeToggle />

// ✅ Correct
<SelectionProvider>
  <SelectModeToggle />
</SelectionProvider>
```

### State not updating
**Problem**: Clicking button doesn't toggle state
**Solution**: Check that `SelectionProvider` is properly set up and no other code is interfering with context

### Styling issues
**Problem**: Button doesn't look right
**Solution**: Ensure Tailwind CSS is configured and classes are being processed

## License

Part of the Mothbox project. See main project LICENSE file.
