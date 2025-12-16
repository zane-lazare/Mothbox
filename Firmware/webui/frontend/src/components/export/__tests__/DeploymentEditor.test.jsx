import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DeploymentEditor from '../DeploymentEditor';

// Create a wrapper component with QueryClientProvider for tests
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Helper to render with QueryClientProvider
const renderWithQueryClient = (ui, options = {}) => {
  return render(ui, { wrapper: createWrapper(), ...options });
};

describe('DeploymentEditor', () => {
  const mockOnSave = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all required form fields', () => {
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/deployment name/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('validates deployment_name is required', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const saveButton = screen.getByRole('button', { name: /save/i });
    expect(saveButton).toBeDisabled(); // Disabled when no name

    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test Deployment');

    expect(saveButton).not.toBeDisabled();
  });

  it('enforces deployment_name max length (200 chars) with maxLength attribute', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const nameInput = screen.getByLabelText(/deployment name/i);
    expect(nameInput).toHaveAttribute('maxLength', '200');

    // Type 200 characters - should be allowed
    const exactlyAllowed = 'a'.repeat(200);
    await user.type(nameInput, exactlyAllowed);

    // Verify character counter shows
    expect(screen.getByText('200/200 characters')).toBeInTheDocument();
  });

  it('enforces location_name max length (500 chars) with maxLength attribute', () => {
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const locationInput = screen.getByLabelText(/location name/i);
    expect(locationInput).toHaveAttribute('maxLength', '500');
  });

  it('validates date range (start <= end)', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const startDateInput = screen.getByLabelText(/start date/i);
    const endDateInput = screen.getByLabelText(/end date/i);

    await user.type(startDateInput, '2024-12-01');
    await user.type(endDateInput, '2024-11-01'); // End before start
    await user.tab();

    expect(screen.getByText(/end date must be after start date/i)).toBeInTheDocument();
  });

  it('shows validation errors inline for date range', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Add valid name first
    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test Deployment');

    // Create invalid date range
    const startDateInput = screen.getByLabelText(/start date/i);
    const endDateInput = screen.getByLabelText(/end date/i);
    await user.type(startDateInput, '2024-12-01');
    await user.type(endDateInput, '2024-11-01'); // End before start
    await user.tab();

    const errorMessage = screen.getByText(/end date must be after start date/i);
    expect(errorMessage).toBeInTheDocument();
    expect(errorMessage).toHaveClass('text-red-600'); // or similar error styling
  });

  it('disables Save when form is invalid', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const saveButton = screen.getByRole('button', { name: /save/i });
    expect(saveButton).toBeDisabled();

    // Add valid name
    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test');
    expect(saveButton).not.toBeDisabled();

    // Add invalid date range
    const startDateInput = screen.getByLabelText(/start date/i);
    const endDateInput = screen.getByLabelText(/end date/i);
    await user.type(startDateInput, '2024-12-01');
    await user.type(endDateInput, '2024-11-01');

    expect(saveButton).toBeDisabled();
  });

  it('calls onSave with correct data structure', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Oak Ridge Survey');

    const locationInput = screen.getByLabelText(/location name/i);
    await user.type(locationInput, 'Oak Ridge, TN');

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    expect(mockOnSave).toHaveBeenCalledWith({
      deployment_name: 'Oak Ridge Survey',
      location_name: 'Oak Ridge, TN',
      latitude: null,
      longitude: null,
      altitude: null,
      start_date: null,
      end_date: null,
      environmental: {},
      mothbox_id: '',
      firmware_version: '',
      custom: {}
    });
  });

  it('shows confirmation dialog when canceling with unsaved changes', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test');

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // ConfirmDialog should be shown
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/discard unsaved changes/i)).toBeInTheDocument();
    expect(screen.getByText(/you have unsaved changes/i)).toBeInTheDocument();

    // Clicking "Keep Editing" should close dialog without calling onCancel
    const keepEditingButton = screen.getByRole('button', { name: /keep editing/i });
    await user.click(keepEditingButton);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(mockOnCancel).not.toHaveBeenCalled();
  });

  it('calls onCancel when confirming discard in dialog', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Type something to trigger changes
    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test');

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // ConfirmDialog should be shown
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // Clicking "Discard" should close dialog and call onCancel
    const discardButton = screen.getByRole('button', { name: /discard/i });
    await user.click(discardButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('does not show confirmation dialog when canceling without changes', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Cancel without making any changes
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // No dialog should appear, onCancel should be called immediately
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('handles environmental key-value pairs', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Expand environmental section
    const envSection = screen.getByText(/environmental conditions/i);
    await user.click(envSection);

    // Add key-value pair
    const addButton = screen.getByRole('button', { name: /add environmental field/i });
    await user.click(addButton);

    const keyInputs = screen.getAllByPlaceholderText(/key/i);
    const valueInputs = screen.getAllByPlaceholderText(/value/i);

    await user.type(keyInputs[0], 'temperature');
    await user.type(valueInputs[0], '18-28°C');

    // Save and verify
    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test');

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({
        environmental: {
          temperature: '18-28°C'
        }
      })
    );
  });

  it('allows removing environmental key-value pairs', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={{
          deployment_name: 'Test',
          environmental: {
            temperature: '20°C',
            humidity: '60%'
          }
        }}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Expand environmental section
    const envSection = screen.getByText(/environmental conditions/i);
    await user.click(envSection);

    // Remove first key-value pair
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    await user.click(removeButtons[0]);

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({
        environmental: {
          humidity: '60%'
        }
      })
    );
  });

  it('handles custom fields with max 50 keys', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Expand custom section
    const customSection = screen.getByText(/custom fields/i);
    await user.click(customSection);

    // Add key-value pair
    const addButton = screen.getByRole('button', { name: /add custom field/i });
    await user.click(addButton);

    const keyInputs = screen.getAllByPlaceholderText(/key/i);
    const valueInputs = screen.getAllByPlaceholderText(/value/i);

    await user.type(keyInputs[keyInputs.length - 1], 'project_code');
    await user.type(valueInputs[valueInputs.length - 1], 'ORNL-2024-001');

    const nameInput = screen.getByLabelText(/deployment name/i);
    await user.type(nameInput, 'Test');

    const saveButton = screen.getByRole('button', { name: /save/i });
    await user.click(saveButton);

    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({
        custom: {
          project_code: 'ORNL-2024-001'
        }
      })
    );
  });

  it('disables add button when 50 custom keys reached', async () => {
    const user = userEvent.setup();
    const customFields = {};
    for (let i = 0; i < 50; i++) {
      customFields[`key${i}`] = `value${i}`;
    }

    renderWithQueryClient(
      <DeploymentEditor
        deployment={{
          deployment_name: 'Test',
          custom: customFields
        }}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Expand custom section
    const customSection = screen.getByText(/custom fields/i);
    await user.click(customSection);

    const addButton = screen.getByRole('button', { name: /add custom field/i });
    expect(addButton).toBeDisabled();
  });

  it('shows tooltip when custom fields limit reached', async () => {
    const user = userEvent.setup();
    const customFields = {};
    for (let i = 0; i < 50; i++) {
      customFields[`key${i}`] = `value${i}`;
    }

    renderWithQueryClient(
      <DeploymentEditor
        deployment={{ deployment_name: 'Test', custom: customFields }}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Expand custom section
    const customSection = screen.getByText(/custom fields/i);
    await user.click(customSection);

    // Find the wrapper span with tooltip
    const tooltipWrapper = screen.getByTitle(/maximum of 50 custom fields/i);
    expect(tooltipWrapper).toBeInTheDocument();
  });

  it('renders collapsible sections', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Environmental section should be collapsed by default
    expect(screen.queryByRole('button', { name: /add environmental field/i })).not.toBeInTheDocument();

    // Click to expand
    const envSection = screen.getByText(/environmental conditions/i);
    await user.click(envSection);

    expect(screen.getByRole('button', { name: /add environmental field/i })).toBeInTheDocument();
  });

  it('populates form with existing deployment data', () => {
    const existingDeployment = {
      deployment_name: 'Oak Ridge Survey',
      location_name: 'Oak Ridge, TN',
      latitude: 35.9606,
      longitude: -83.9207,
      altitude: 350.5,
      start_date: '2024-06-01',
      end_date: '2024-08-31',
      environmental: {
        habitat: 'deciduous forest'
      },
      mothbox_id: 'mothbox-001',
      firmware_version: '5.2.1',
      custom: {
        project_code: 'ORNL-2024-001'
      }
    };

    renderWithQueryClient(
      <DeploymentEditor
        deployment={existingDeployment}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/deployment name/i)).toHaveValue('Oak Ridge Survey');
    expect(screen.getByLabelText(/location name/i)).toHaveValue('Oak Ridge, TN');
    expect(screen.getByLabelText(/altitude/i)).toHaveValue(350.5);
    expect(screen.getByLabelText(/start date/i)).toHaveValue('2024-06-01');
    expect(screen.getByLabelText(/end date/i)).toHaveValue('2024-08-31');
  });

  it('displays loading state', () => {
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
        isLoading={true}
      />
    );

    const saveButton = screen.getByRole('button', { name: /saving/i });
    expect(saveButton).toBeDisabled();
  });

  it('displays error message when provided', () => {
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
        error="Failed to save deployment"
      />
    );

    expect(screen.getByText(/failed to save deployment/i)).toBeInTheDocument();
  });

  it('integrates CoordinateInput component', () => {
    renderWithQueryClient(
      <DeploymentEditor
        deployment={null}
        directory="/photos/deployment1"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByLabelText(/latitude/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/longitude/i)).toBeInTheDocument();
  });
});
