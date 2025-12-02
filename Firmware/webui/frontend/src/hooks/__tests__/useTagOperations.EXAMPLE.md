# useTagOperations Hook - Usage Examples

## Overview

The `useTagOperations` hook extends `useSidecarMetadata` to provide toast notifications for tag operations.

## Features

- ✅ Success toast on tag add (3 seconds)
- ✅ Success toast on tag remove (3 seconds)
- ✅ Info toast for duplicate tags or missing tags
- ✅ Error toast with undo button on failures (5 seconds)
- ✅ Automatic optimistic updates (from useSidecarMetadata)
- ✅ Automatic rollback on errors (from useSidecarMetadata)

## Basic Usage

```jsx
import useTagOperations from '../hooks/useTagOperations'

function PhotoDetail({ filename }) {
  const { data, addTag, removeTag, isUpdating } = useTagOperations(filename)

  const handleAddTag = (tag) => {
    addTag(tag) // Shows success toast automatically
  }

  const handleRemoveTag = (tag) => {
    removeTag(tag) // Shows success toast automatically
  }

  if (!data) return <div>Loading...</div>

  return (
    <div>
      <h2>Tags</h2>
      <div>
        {data.tags.map((tag) => (
          <button key={tag} onClick={() => handleRemoveTag(tag)}>
            {tag} ×
          </button>
        ))}
      </div>
      <button onClick={() => handleAddTag('butterfly')} disabled={isUpdating}>
        Add Tag
      </button>
    </div>
  )
}
```

## Toast Behavior

### Success - Adding a Tag

When a tag is successfully added, a success toast appears:

```
✅ Added tag "butterfly"
```

- Duration: 3 seconds
- Auto-dismisses

### Success - Removing a Tag

When a tag is successfully removed, a success toast appears:

```
✅ Removed tag "moth"
```

- Duration: 3 seconds
- Auto-dismisses

### Info - Duplicate Tag

When attempting to add an existing tag:

```
ℹ️ Tag already exists
```

- Duration: 3 seconds
- Auto-dismisses

### Info - Tag Not Found

When attempting to remove a non-existent tag:

```
ℹ️ Tag not found
```

- Duration: 3 seconds
- Auto-dismisses

### Error - With Undo Button

When an operation fails (network error, server error, etc.):

```
❌ Failed to add tag "butterfly"  [Undo]
```

- Duration: 5 seconds
- Has clickable "Undo" button
- Clicking "Undo" restores previous tags and shows "Changes undone"

## API Reference

### Hook Signature

```typescript
function useTagOperations(filename: string): {
  // Query State
  data: SidecarMetadata | null
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  error: Error | null

  // Tag Operations (with toasts)
  addTag: (tag: string) => void
  removeTag: (tag: string) => void

  // Other Operations (no toasts)
  updateTags: (tags: string[]) => void
  updateSpecies: (species: string) => void
  updateNotes: (notes: string) => void

  // Mutation State
  isUpdating: boolean
  updateError: Error | null
}
```

### SidecarMetadata Type

```typescript
interface SidecarMetadata {
  tags: string[]
  species: string
  notes: string
}
```

## Integration with QuickTagDropdown

The `QuickTagButton` component can use this hook:

```jsx
function QuickTagButton({ filename }) {
  const { data, addTag, removeTag, isUpdating } = useTagOperations(filename)

  const handleTagSelect = (tag) => {
    if (data?.tags.includes(tag)) {
      removeTag(tag) // Shows "Removed tag" toast
    } else {
      addTag(tag) // Shows "Added tag" toast
    }
  }

  return (
    <QuickTagDropdown
      tags={data?.tags || []}
      onTagSelect={handleTagSelect}
      disabled={isUpdating}
    />
  )
}
```

## Error Handling

The hook automatically handles errors:

1. **Optimistic Update**: UI updates immediately
2. **Error Occurs**: Automatic rollback to previous state
3. **Error Toast**: Shows error with undo button
4. **User Clicks Undo**: Restores tags and shows "Changes undone" toast

## Comparison with useSidecarMetadata

| Feature | useSidecarMetadata | useTagOperations |
|---------|-------------------|------------------|
| Query data | ✅ | ✅ |
| Optimistic updates | ✅ | ✅ |
| Automatic rollback | ✅ | ✅ |
| Toast notifications | ❌ | ✅ (add/remove only) |
| Undo functionality | ❌ | ✅ (on error) |

**When to use each:**
- Use `useSidecarMetadata` for silent operations (e.g., programmatic bulk updates)
- Use `useTagOperations` for user-triggered operations (e.g., button clicks)

## Testing

See `useTagOperations.test.jsx` for comprehensive test coverage:

- ✅ Success toasts
- ✅ Info toasts (duplicate/not found)
- ✅ Error toasts
- ✅ Pass-through functions (no toasts)
- ✅ Query state exposure
- ✅ Mutation state exposure

## Notes

- Toast notifications use `react-hot-toast` (already installed)
- Toast durations match `TOAST_CONFIG` constants
- Error toasts include custom undo button (rendered via toast callback)
- The hook uses `useCallback` for stable function references
- Previous tags are tracked with `useRef` for undo functionality
