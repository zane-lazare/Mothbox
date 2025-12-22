# PatternEditor Components

Components for creating and editing scheduler patterns in the Mothbox Pattern Editor.

## ActionForm

Modal form component for creating or editing individual actions in a pattern.

### Features

- **Action Type Selection**: Choose from GPIO, Camera, GPS Sync, or Service actions
- **Dynamic Action Names**: Action name dropdown filters based on selected type
- **Offset Validation**: Enforces 0-1440 minute range
- **Description Editor**: Optional description with 500 character limit and live counter
- **Parameters Editor**: Add/remove key-value parameter pairs
- **Validation**: Comprehensive inline error messages
- **Dark Mode**: Full dark mode support

### Props

```jsx
{
  action?: {                        // undefined for create mode
    action_type: string,            // 'gpio', 'camera', 'gps_sync', or 'service'
    action_name: string,            // Action-specific name
    offset_minutes: number,         // 0-1440
    description?: string,           // Optional, max 500 chars
    parameters?: Record<string, string>  // Optional key-value pairs
  },
  onSave: (action: PatternAction) => void,  // Called with validated action data
  onCancel: () => void,             // Called when user cancels
  isOpen: boolean                   // Controls modal visibility
}
```

### Action Type Mappings

```javascript
const ACTION_NAMES = {
  gpio: ['attract_on', 'attract_off', 'flash_on', 'flash_off'],
  camera: ['takephoto'],
  gps_sync: ['sync'],
  service: ['backup', 'update_display'],
}
```

### Usage Example

```jsx
import ActionForm from './PatternEditor/ActionForm';

function MyComponent() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAction, setEditingAction] = useState(null);

  const handleSave = (action) => {
    console.log('Saved action:', action);
    setIsModalOpen(false);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
  };

  return (
    <>
      <button onClick={() => setIsModalOpen(true)}>
        Create Action
      </button>

      <ActionForm
        action={editingAction}
        onSave={handleSave}
        onCancel={handleCancel}
        isOpen={isModalOpen}
      />
    </>
  );
}
```

### Testing

The component has comprehensive test coverage (98.13% statement coverage):

- Rendering in create/edit modes
- Action type/name selection
- Form validation (offset, required fields, character limits)
- Parameter key-value editor (add/remove)
- Form submission with valid/invalid data
- Modal visibility control
- Dark mode styling

Run tests:
```bash
npm test -- ActionForm --run
```

### Validation Rules

1. **Action Type**: Required
2. **Action Name**: Required, must match selected type
3. **Offset**: Required, must be 0-1440 minutes
4. **Description**: Optional, max 500 characters
5. **Parameters**: Optional, empty rows excluded from saved data

### Form Behavior

- **Create Mode**: When `action` prop is undefined, form renders empty
- **Edit Mode**: When `action` prop is provided, form pre-populates fields
- **Reset on Close**: Form resets when modal is closed and reopened
- **Type Change**: Changing action type resets action name dropdown
- **Empty Parameters**: Parameter rows with empty key/value are excluded from saved data
