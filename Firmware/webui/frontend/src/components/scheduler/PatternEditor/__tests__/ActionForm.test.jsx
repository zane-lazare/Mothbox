import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ActionForm from '../ActionForm';
import { ACTION_LIMITS } from '../constants';

describe('ActionForm', () => {
  const mockOnSave = vi.fn();
  const mockOnCancel = vi.fn();

  const defaultProps = {
    isOpen: true,
    onSave: mockOnSave,
    onCancel: mockOnCancel,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render empty form in create mode', () => {
      render(<ActionForm {...defaultProps} />);

      expect(screen.getByLabelText(/action type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/action name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/offset/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('should render with action data in edit mode', () => {
      const action = {
        action_type: 'gpio',
        action_name: 'attract_on',
        offset_minutes: 30,
        description: 'Turn on attract lights',
        parameters: { duration: '60' },
      };

      render(<ActionForm {...defaultProps} action={action} />);

      expect(screen.getByLabelText(/action type/i)).toHaveValue('gpio');
      expect(screen.getByLabelText(/action name/i)).toHaveValue('attract_on');
      expect(screen.getByLabelText(/offset/i)).toHaveValue(30);
      expect(screen.getByLabelText(/description/i)).toHaveValue('Turn on attract lights');
    });

    it('should not render when isOpen is false', () => {
      render(<ActionForm {...defaultProps} isOpen={false} />);

      expect(screen.queryByLabelText(/action type/i)).not.toBeInTheDocument();
    });

    it('should apply dark mode styling', () => {
      document.documentElement.classList.add('dark');
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      expect(actionTypeSelect).toHaveClass('dark:bg-gray-800');

      document.documentElement.classList.remove('dark');
    });
  });

  describe('Action Type and Name Selection', () => {
    it('should change available action names when action type changes', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);

      // Select GPIO type
      await user.selectOptions(actionTypeSelect, 'gpio');
      const gpioOptions = Array.from(actionNameSelect.options).map(opt => opt.value);
      expect(gpioOptions).toContain('attract_on');
      expect(gpioOptions).toContain('attract_off');
      expect(gpioOptions).toContain('flash_on');
      expect(gpioOptions).toContain('flash_off');

      // Select camera type
      await user.selectOptions(actionTypeSelect, 'camera');
      const cameraOptions = Array.from(actionNameSelect.options).map(opt => opt.value);
      expect(cameraOptions).toContain('takephoto');
      expect(cameraOptions).not.toContain('attract_on');

      // Select gps_sync type
      await user.selectOptions(actionTypeSelect, 'gps_sync');
      const gpsOptions = Array.from(actionNameSelect.options).map(opt => opt.value);
      expect(gpsOptions).toContain('sync');

      // Select service type
      await user.selectOptions(actionTypeSelect, 'service');
      const serviceOptions = Array.from(actionNameSelect.options).map(opt => opt.value);
      expect(serviceOptions).toContain('backup');
      expect(serviceOptions).toContain('update_display');
    });

    it('should reset action name when action type changes', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);

      // Select GPIO and set action name
      await user.selectOptions(actionTypeSelect, 'gpio');
      await user.selectOptions(actionNameSelect, 'attract_on');
      expect(actionNameSelect).toHaveValue('attract_on');

      // Change type - should reset name
      await user.selectOptions(actionTypeSelect, 'camera');
      expect(actionNameSelect.value).toBe('');
    });
  });

  describe('Validation', () => {
    it('should require offset field', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);
      const saveButton = screen.getByRole('button', { name: /save/i });

      await user.selectOptions(actionTypeSelect, 'gpio');
      await user.selectOptions(actionNameSelect, 'attract_on');
      await user.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/offset is required/i)).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('should validate offset is within valid range', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const offsetInput = screen.getByLabelText(/offset/i);
      const saveButton = screen.getByRole('button', { name: /save/i });

      // Test below minimum
      await user.clear(offsetInput);
      await user.type(offsetInput, '-1');
      await user.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(new RegExp(`offset must be between ${ACTION_LIMITS.MIN_OFFSET_MINUTES} and ${ACTION_LIMITS.MAX_OFFSET_MINUTES}`, 'i'))).toBeInTheDocument();
      });

      // Test above maximum
      await user.clear(offsetInput);
      await user.type(offsetInput, String(ACTION_LIMITS.MAX_OFFSET_MINUTES + 1));
      await user.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(new RegExp(`offset must be between ${ACTION_LIMITS.MIN_OFFSET_MINUTES} and ${ACTION_LIMITS.MAX_OFFSET_MINUTES}`, 'i'))).toBeInTheDocument();
      });

      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('should require action type and name', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const offsetInput = screen.getByLabelText(/offset/i);
      const saveButton = screen.getByRole('button', { name: /save/i });

      await user.type(offsetInput, '30');
      await user.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/action type is required/i)).toBeInTheDocument();
      });
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('should enforce description max length', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const descriptionInput = screen.getByLabelText(/description/i);
      const longText = 'a'.repeat(ACTION_LIMITS.DESCRIPTION_MAX_LENGTH + 1);

      await user.type(descriptionInput, longText);

      // Should be truncated to max length
      expect(descriptionInput.value.length).toBeLessThanOrEqual(ACTION_LIMITS.DESCRIPTION_MAX_LENGTH);
    });

    it('should show character count for description', () => {
      render(<ActionForm {...defaultProps} />);

      expect(screen.getByText(new RegExp(`0 / ${ACTION_LIMITS.DESCRIPTION_MAX_LENGTH}`, 'i'))).toBeInTheDocument();
    });

    it('should update character count as user types', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const descriptionInput = screen.getByLabelText(/description/i);
      await user.type(descriptionInput, 'Test description');

      expect(screen.getByText(new RegExp(`16 / ${ACTION_LIMITS.DESCRIPTION_MAX_LENGTH}`, 'i'))).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('should call onSave with correct data when form is valid', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);
      const offsetInput = screen.getByLabelText(/offset/i);
      const descriptionInput = screen.getByLabelText(/description/i);
      const saveButton = screen.getByRole('button', { name: /save/i });

      await user.selectOptions(actionTypeSelect, 'gpio');
      await user.selectOptions(actionNameSelect, 'attract_on');
      await user.type(offsetInput, '30');
      await user.type(descriptionInput, 'Turn on attract lights');
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith({
          action_type: 'gpio',
          action_name: 'attract_on',
          offset_minutes: 30,
          description: 'Turn on attract lights',
          parameters: {},
        });
      });
    });

    it('should not call onSave when validation fails', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('should include parameters in saved data', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);
      const offsetInput = screen.getByLabelText(/offset/i);

      await user.selectOptions(actionTypeSelect, 'gpio');
      await user.selectOptions(actionNameSelect, 'attract_on');
      await user.type(offsetInput, '30');

      // Add parameter
      const addParamButton = screen.getByRole('button', { name: /add parameter/i });
      await user.click(addParamButton);

      const keyInputs = screen.getAllByPlaceholderText(/key/i);
      const valueInputs = screen.getAllByPlaceholderText(/value/i);

      await user.type(keyInputs[0], 'duration');
      await user.type(valueInputs[0], '60');

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            parameters: { duration: '60' },
          })
        );
      });
    });
  });

  describe('Cancel Button', () => {
    it('should call onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it('should not save data when cancel is clicked', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const offsetInput = screen.getByLabelText(/offset/i);
      await user.type(offsetInput, '30');

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Parameters Key-Value Editor', () => {
    it('should render parameters from edit mode', () => {
      const action = {
        action_type: 'gpio',
        action_name: 'attract_on',
        offset_minutes: 30,
        parameters: {
          duration: '60',
          intensity: 'high',
        },
      };

      render(<ActionForm {...defaultProps} action={action} />);

      const keyInputs = screen.getAllByPlaceholderText(/key/i);
      const valueInputs = screen.getAllByPlaceholderText(/value/i);

      expect(keyInputs).toHaveLength(2);
      expect(keyInputs[0]).toHaveValue('duration');
      expect(valueInputs[0]).toHaveValue('60');
      expect(keyInputs[1]).toHaveValue('intensity');
      expect(valueInputs[1]).toHaveValue('high');
    });

    it('should add new parameter row', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add parameter/i });
      await user.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/key/i);
      expect(keyInputs).toHaveLength(1);
    });

    it('should remove parameter row', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add parameter/i });
      await user.click(addButton);
      await user.click(addButton);

      let keyInputs = screen.getAllByPlaceholderText(/key/i);
      expect(keyInputs).toHaveLength(2);

      const removeButtons = screen.getAllByRole('button', { name: /remove/i });
      await user.click(removeButtons[0]);

      keyInputs = screen.getAllByPlaceholderText(/key/i);
      expect(keyInputs).toHaveLength(1);
    });

    it('should update parameter values', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add parameter/i });
      await user.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/key/i);
      const valueInputs = screen.getAllByPlaceholderText(/value/i);

      await user.type(keyInputs[0], 'test_key');
      await user.type(valueInputs[0], 'test_value');

      expect(keyInputs[0]).toHaveValue('test_key');
      expect(valueInputs[0]).toHaveValue('test_value');
    });

    it('should not include empty parameter rows in saved data', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);
      const offsetInput = screen.getByLabelText(/offset/i);

      await user.selectOptions(actionTypeSelect, 'gpio');
      await user.selectOptions(actionNameSelect, 'attract_on');
      await user.type(offsetInput, '30');

      // Add parameter row but leave it empty
      const addButton = screen.getByRole('button', { name: /add parameter/i });
      await user.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            parameters: {},
          })
        );
      });
    });
  });

  describe('Modal Behavior', () => {
    it('should close modal on successful save', async () => {
      const user = userEvent.setup();
      render(<ActionForm {...defaultProps} />);

      const actionTypeSelect = screen.getByLabelText(/action type/i);
      const actionNameSelect = screen.getByLabelText(/action name/i);
      const offsetInput = screen.getByLabelText(/offset/i);
      const saveButton = screen.getByRole('button', { name: /save/i });

      await user.selectOptions(actionTypeSelect, 'gpio');
      await user.selectOptions(actionNameSelect, 'attract_on');
      await user.type(offsetInput, '30');
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalled();
      });
    });

    it('should reset form when closed and reopened', async () => {
      const { rerender } = render(<ActionForm {...defaultProps} />);

      const offsetInput = screen.getByLabelText(/offset/i);
      await userEvent.type(offsetInput, '30');

      // Close modal
      rerender(<ActionForm {...defaultProps} isOpen={false} />);

      // Reopen modal
      rerender(<ActionForm {...defaultProps} isOpen={true} />);

      const newOffsetInput = screen.getByLabelText(/offset/i);
      expect(newOffsetInput).toHaveValue(null);
    });
  });
});
