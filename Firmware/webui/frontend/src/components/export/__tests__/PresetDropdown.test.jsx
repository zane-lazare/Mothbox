import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PresetDropdown from '../PresetDropdown';

describe('PresetDropdown', () => {
  const mockBuiltInPresets = [
    { name: 'gbif_biodiversity', display_name: 'GBIF Biodiversity Export', category: 'built_in' },
    { name: 'inaturalist_upload', display_name: 'iNaturalist Upload', category: 'built_in' },
    { name: 'simple_json', display_name: 'Simple JSON Export', category: 'built_in' },
    { name: 'simple_csv', display_name: 'Simple CSV Export', category: 'built_in' },
    { name: 'hdr_series', display_name: 'HDR Series Export', category: 'built_in' },
    { name: 'focus_bracket_series', display_name: 'Focus Bracket Series Export', category: 'built_in' },
  ];

  const mockUserPresets = [
    { name: 'my_custom_preset', display_name: 'My Custom Preset', category: 'user' },
  ];

  it('renders dropdown with preset options', () => {
    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    expect(screen.getByRole('combobox', { name: /preset/i })).toBeInTheDocument();
  });

  it('groups presets by category (built-in vs user)', () => {
    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={[...mockBuiltInPresets, ...mockUserPresets]}
        onSavePreset={vi.fn()}
      />
    );

    expect(screen.getByRole('group', { name: /built-in presets/i })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: /user presets/i })).toBeInTheDocument();
  });

  it('shows lock icon for built-in presets', () => {
    render(
      <PresetDropdown
        value="gbif_biodiversity"
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    // Lock icon and text should be shown when a built-in preset is selected
    expect(screen.getByText(/built-in preset/i)).toBeInTheDocument();
  });

  it('calls onChange when preset selected', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <PresetDropdown
        value={null}
        onChange={onChange}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    const select = screen.getByRole('combobox', { name: /preset/i });
    await user.selectOptions(select, 'gbif_biodiversity');

    expect(onChange).toHaveBeenCalledWith('gbif_biodiversity');
  });

  it('shows "No preset" option', () => {
    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    expect(screen.getByRole('option', { name: /no preset/i })).toBeInTheDocument();
  });

  it('shows "Save as preset" option', () => {
    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    expect(screen.getByRole('option', { name: /save current settings/i })).toBeInTheDocument();
  });

  it('calls onSavePreset when save option selected', async () => {
    const user = userEvent.setup();
    const onSavePreset = vi.fn();

    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={onSavePreset}
      />
    );

    const select = screen.getByRole('combobox', { name: /preset/i });
    await user.selectOptions(select, '__save_new__');

    expect(onSavePreset).toHaveBeenCalled();
  });

  it('handles empty presets list', () => {
    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={[]}
        onSavePreset={vi.fn()}
      />
    );

    expect(screen.getByRole('option', { name: /no preset/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /save current settings/i })).toBeInTheDocument();
  });

  it('respects disabled prop', () => {
    render(
      <PresetDropdown
        value={null}
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
        disabled
      />
    );

    expect(screen.getByRole('combobox', { name: /preset/i })).toBeDisabled();
  });

  it('displays selected preset value', () => {
    render(
      <PresetDropdown
        value="gbif_biodiversity"
        onChange={vi.fn()}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    const select = screen.getByRole('combobox', { name: /preset/i });
    expect(select).toHaveValue('gbif_biodiversity');
  });

  it('clears selection when "No preset" selected', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <PresetDropdown
        value="gbif_biodiversity"
        onChange={onChange}
        presets={mockBuiltInPresets}
        onSavePreset={vi.fn()}
      />
    );

    const select = screen.getByRole('combobox', { name: /preset/i });
    await user.selectOptions(select, '');

    expect(onChange).toHaveBeenCalledWith(null);
  });
});
