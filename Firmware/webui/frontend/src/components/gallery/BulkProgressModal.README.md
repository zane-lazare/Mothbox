# BulkProgressModal Component

## Overview
A stateless modal component that displays progress during bulk operations (tag, species, delete) in the gallery. Implements TDD workflow with 100% test coverage.

## Features
- **Three states**: processing, success, error
- **Progress visualization**: Animated progress bar with percentage
- **Batch support**: Shows current/total batches for large operations (>100 photos)
- **Error reporting**: Displays up to 5 error messages with overflow indicator
- **Non-dismissible during processing**: Prevents accidental cancellation
- **Accessible**: Proper ARIA attributes, role="dialog", progressbar
- **Portal-based**: Renders to document.body for proper z-index layering
- **Dark mode support**: Full Tailwind dark mode classes

## Usage

```jsx
import BulkProgressModal from '@/components/gallery/BulkProgressModal'

function Gallery() {
  const [modalState, setModalState] = useState({
    isOpen: false,
    status: 'processing',
    progress: 0,
    processedCount: 0,
    totalCount: 0
  })

  const handleBulkTag = async (photoIds, tagName) => {
    setModalState({
      isOpen: true,
      status: 'processing',
      progress: 0,
      processedCount: 0,
      totalCount: photoIds.length,
      operation: 'tag'
    })

    let processed = 0
    const errors = {}

    for (const id of photoIds) {
      try {
        await api.tagPhoto(id, tagName)
        processed++
      } catch (err) {
        errors[id] = err.message
      }

      setModalState(prev => ({
        ...prev,
        progress: Math.round((processed / photoIds.length) * 100),
        processedCount: processed
      }))
    }

    setModalState({
      isOpen: true,
      status: Object.keys(errors).length > 0 ? 'error' : 'success',
      successCount: processed,
      failedCount: Object.keys(errors).length,
      errors,
      operation: 'tag'
    })
  }

  return (
    <>
      {/* Gallery UI */}

      <BulkProgressModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState(prev => ({ ...prev, isOpen: false }))}
        onCancel={() => {
          // Cancel logic
          setModalState(prev => ({ ...prev, isOpen: false }))
        }}
        status={modalState.status}
        progress={modalState.progress}
        processedCount={modalState.processedCount}
        totalCount={modalState.totalCount}
        successCount={modalState.successCount}
        failedCount={modalState.failedCount}
        errors={modalState.errors}
        operation={modalState.operation}
      />
    </>
  )
}
```

## Props

### Required Props
- `isOpen` (boolean): Whether modal is visible
- `onClose` (function): Callback when modal closes (after completion)
- `status` ('processing' | 'success' | 'error'): Current operation status
- `progress` (number): Progress percentage (0-100)
- `processedCount` (number): Number of photos processed so far
- `totalCount` (number): Total number of photos to process

### Optional Props
- `onCancel` (function): Callback when user cancels operation (only shown during processing)
- `currentBatch` (number): Current batch number (for multi-batch operations)
- `totalBatches` (number): Total number of batches
- `successCount` (number): Number of successfully processed photos (for completion states)
- `failedCount` (number): Number of failed photos (for completion states)
- `errors` (object): Map of filename -> error message
- `operation` ('tag' | 'species' | 'delete'): Type of operation (default: 'tag')

## States

### Processing State
Shows:
- Progress bar with current percentage
- "Processing X of Y photos" text
- Batch info (if totalBatches > 1)
- Cancel button

Modal is non-dismissible:
- No click-outside-to-close
- No Escape key close

### Success State
Shows:
- Green check circle icon
- "Complete!" heading
- Success count (and failed count if any failures)
- "Done" button to close

### Error State
Shows:
- Red exclamation circle icon
- "Error" heading
- Failed count
- Up to 5 error messages (with "and X more" if >5 errors)
- "Close" button

## Multi-Batch Support

For operations with >100 photos, display batch info:

```jsx
<BulkProgressModal
  isOpen={true}
  status="processing"
  progress={50}
  processedCount={150}
  totalCount={300}
  currentBatch={2}
  totalBatches={3}
  operation="tag"
  onClose={handleClose}
  onCancel={handleCancel}
/>
```

Output: "Processing 150 of 300 photos (Batch 2 of 3)"

## Error Handling

```jsx
<BulkProgressModal
  isOpen={true}
  status="error"
  failedCount={7}
  errors={{
    'photo1.jpg': 'Network error',
    'photo2.jpg': 'Permission denied',
    'photo3.jpg': 'Invalid tag',
    'photo4.jpg': 'Timeout',
    'photo5.jpg': 'Server error',
    'photo6.jpg': 'Not found',
    'photo7.jpg': 'Conflict'
  }}
  onClose={handleClose}
/>
```

Shows first 5 errors + "...and 2 more"

## Testing

```bash
# Run tests
npm test -- BulkProgressModal --run

# Run with coverage
npm test -- BulkProgressModal --run --coverage
```

**Coverage**: 100% (51 tests)

### Test Categories
- Rendering (7 tests)
- Progress Display (8 tests)
- States (11 tests)
- Cancel Button (4 tests)
- Modal Behavior (4 tests)
- Completion (6 tests)
- Edge Cases (8 tests)
- Accessibility (3 tests)

## Accessibility

- `role="dialog"` on modal container
- `aria-modal="true"` for screen reader context
- `aria-label` with operation type
- Progress bar with `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Semantic heading hierarchy
- Focus management (handled by parent)

## Implementation Notes

### Why Stateless?
Parent component controls all state via props, allowing:
- Better testability
- Single source of truth
- Easier state management in parent
- No internal state complexity

### Why Portal?
Uses React's `createPortal` to render to `document.body`:
- Avoids z-index stacking issues
- Ensures modal always appears on top
- Prevents CSS containment issues

### Why Non-Dismissible During Processing?
Prevents data inconsistency if user accidentally closes modal during async operations. User must explicitly click "Cancel" button.

## Design Decisions

1. **No auto-close**: Modal requires explicit user action (Done/Close button)
2. **Error limit of 5**: Prevents UI overflow, shows "and X more" for remaining
3. **Batch info threshold**: Only shows batch info when totalBatches > 1
4. **Progress bar animation**: CSS transition for smooth visual feedback
5. **Dark mode**: Full support via Tailwind dark: classes

## Future Enhancements

Potential improvements for future phases:
- Retry failed photos button in error state
- Pause/Resume functionality
- Time remaining estimation
- Download error report button
- Detailed error expansion (show all errors on click)
- Animation on state transitions
- Confetti on success (optional, configurable)

## Related Components

- **BulkTagModal**: Parent component that uses BulkProgressModal
- **BulkDeleteModal**: Parent component that uses BulkProgressModal
- **QuickTagDropdown**: Triggers bulk operations that use this modal

## Files

- Component: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/gallery/BulkProgressModal.jsx`
- Tests: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/gallery/__tests__/BulkProgressModal.test.jsx`
- Documentation: `/home/zane/projects/Mothbox/Firmware/webui/frontend/src/components/gallery/BulkProgressModal.README.md`
