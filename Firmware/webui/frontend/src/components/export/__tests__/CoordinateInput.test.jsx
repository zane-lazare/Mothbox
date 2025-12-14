import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CoordinateInput from '../CoordinateInput';

describe('CoordinateInput', () => {
  it('renders latitude and longitude inputs', () => {
    render(<CoordinateInput latitude={null} longitude={null} onChange={vi.fn()} />);

    expect(screen.getByLabelText(/latitude/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/longitude/i)).toBeInTheDocument();
  });

  it('displays current latitude and longitude values', () => {
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={vi.fn()} />);

    const latInput = screen.getByLabelText(/latitude/i);
    const lonInput = screen.getByLabelText(/longitude/i);

    expect(latInput).toHaveValue(37.7749);
    expect(lonInput).toHaveValue(-122.4194);
  });

  it('calls onChange with valid coordinates when latitude changes', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />);

    const latInput = screen.getByLabelText(/latitude/i);
    await user.clear(latInput);
    await user.type(latInput, '37.7749');

    expect(onChange).toHaveBeenCalledWith({ latitude: 37.7749, longitude: null });
  });

  it('calls onChange with valid coordinates when longitude changes', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />);

    const lonInput = screen.getByLabelText(/longitude/i);
    await user.clear(lonInput);
    await user.type(lonInput, '-122.4194');

    expect(onChange).toHaveBeenCalledWith({ latitude: null, longitude: -122.4194 });
  });

  it('validates latitude range (-90 to 90)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />);

    const latInput = screen.getByLabelText(/latitude/i);

    // Test invalid value > 90
    await user.clear(latInput);
    await user.type(latInput, '91');
    await user.tab();

    expect(screen.getByText(/invalid latitude.*must be in range \[-90, 90\]/i)).toBeInTheDocument();

    // Test invalid value < -90
    await user.clear(latInput);
    await user.type(latInput, '-91');
    await user.tab();

    expect(screen.getByText(/invalid latitude.*must be in range \[-90, 90\]/i)).toBeInTheDocument();
  });

  it('validates longitude range (-180 to 180)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CoordinateInput latitude={null} longitude={null} onChange={onChange} />);

    const lonInput = screen.getByLabelText(/longitude/i);

    // Test invalid value > 180
    await user.clear(lonInput);
    await user.type(lonInput, '181');
    await user.tab();

    expect(screen.getByText(/invalid longitude.*must be in range \[-180, 180\]/i)).toBeInTheDocument();

    // Test invalid value < -180
    await user.clear(lonInput);
    await user.type(lonInput, '-181');
    await user.tab();

    expect(screen.getByText(/invalid longitude.*must be in range \[-180, 180\]/i)).toBeInTheDocument();
  });

  it('shows inline error messages for invalid values', async () => {
    const user = userEvent.setup();
    render(<CoordinateInput latitude={null} longitude={null} onChange={vi.fn()} />);

    const latInput = screen.getByLabelText(/latitude/i);
    await user.clear(latInput);
    await user.type(latInput, '100');
    await user.tab();

    const errorMessage = screen.getByText(/invalid latitude.*must be in range \[-90, 90\]/i);
    expect(errorMessage).toBeInTheDocument();
    expect(errorMessage).toHaveClass('text-red-600'); // or similar error styling
  });

  it('clears error message when value becomes valid', async () => {
    const user = userEvent.setup();
    render(<CoordinateInput latitude={null} longitude={null} onChange={vi.fn()} />);

    const latInput = screen.getByLabelText(/latitude/i);

    // Enter invalid value
    await user.clear(latInput);
    await user.type(latInput, '100');
    await user.tab();
    expect(screen.getByText(/invalid latitude.*must be in range \[-90, 90\]/i)).toBeInTheDocument();

    // Enter valid value
    await user.clear(latInput);
    await user.type(latInput, '37.7749');
    await user.tab();
    expect(screen.queryByText(/invalid latitude.*must be in range \[-90, 90\]/i)).not.toBeInTheDocument();
  });

  it('respects disabled prop on both inputs', () => {
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={vi.fn()} disabled />);

    const latInput = screen.getByLabelText(/latitude/i);
    const lonInput = screen.getByLabelText(/longitude/i);

    expect(latInput).toBeDisabled();
    expect(lonInput).toBeDisabled();
  });

  it('displays external error prop if provided', () => {
    render(
      <CoordinateInput
        latitude={null}
        longitude={null}
        onChange={vi.fn()}
        error="GPS coordinates are required"
      />
    );

    expect(screen.getByText(/GPS coordinates are required/i)).toBeInTheDocument();
  });

  it('accepts empty values (null/undefined)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CoordinateInput latitude={37.7749} longitude={-122.4194} onChange={onChange} />);

    const latInput = screen.getByLabelText(/latitude/i);
    await user.clear(latInput);
    await user.tab();

    expect(onChange).toHaveBeenCalledWith({ latitude: null, longitude: -122.4194 });
  });

  it('validates that latitude is a number', async () => {
    const user = userEvent.setup();
    render(<CoordinateInput latitude={null} longitude={null} onChange={vi.fn()} />);

    const latInput = screen.getByLabelText(/latitude/i);
    await user.clear(latInput);
    await user.type(latInput, 'abc');
    await user.tab();

    // Input type="number" typically prevents non-numeric input, but test for safety
    expect(latInput).toHaveValue(null);
  });

  it('has correct accessibility attributes', () => {
    render(<CoordinateInput latitude={null} longitude={null} onChange={vi.fn()} />);

    const latInput = screen.getByLabelText(/latitude/i);
    const lonInput = screen.getByLabelText(/longitude/i);

    expect(latInput).toHaveAttribute('type', 'number');
    expect(lonInput).toHaveAttribute('type', 'number');
    expect(latInput).toHaveAttribute('step', '0.000001'); // 6 decimal places
    expect(lonInput).toHaveAttribute('step', '0.000001');
  });

  it('displays coordinate in DMS format when toggle is enabled', async () => {
    const user = userEvent.setup();
    render(
      <CoordinateInput
        latitude={37.7749}
        longitude={-122.4194}
        onChange={vi.fn()}
      />
    );

    // Click toggle button to show DMS
    const toggleButton = screen.getByRole('button', { name: /toggle format/i });
    await user.click(toggleButton);

    // Should show DMS representation
    expect(screen.getByText(/37°46'29.64"N/i)).toBeInTheDocument();
    expect(screen.getByText(/122°25'9.84"W/i)).toBeInTheDocument();
  });

  it('allows toggling between decimal and DMS display', async () => {
    const user = userEvent.setup();
    render(
      <CoordinateInput
        latitude={37.7749}
        longitude={-122.4194}
        onChange={vi.fn()}
      />
    );

    // Should have a toggle button
    const toggleButton = screen.getByRole('button', { name: /toggle format/i });
    expect(toggleButton).toBeInTheDocument();

    // Click to toggle to DMS
    await user.click(toggleButton);
    expect(screen.getByText(/37°46'29.64"N/i)).toBeInTheDocument();

    // Click again to toggle back to decimal
    await user.click(toggleButton);
    expect(screen.queryByText(/37°46'29.64"N/i)).not.toBeInTheDocument();
  });
});
