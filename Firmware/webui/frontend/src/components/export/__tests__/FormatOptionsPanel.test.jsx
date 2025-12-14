import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FormatOptionsPanel from '../FormatOptionsPanel';

describe('FormatOptionsPanel', () => {
  it('shows Darwin Core options when format is darwin_core', () => {
    render(
      <FormatOptionsPanel
        format="darwin_core"
        options={{}}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/validate output/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/include validation warnings/i)).toBeInTheDocument();
  });

  it('shows iNaturalist options when format is inaturalist', () => {
    render(
      <FormatOptionsPanel
        format="inaturalist"
        options={{}}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/include xmp sidecar/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/include manifest/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/include csv summary/i)).toBeInTheDocument();
  });

  it('shows JSON options when format is json', () => {
    render(
      <FormatOptionsPanel
        format="json"
        options={{}}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/pretty print/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/include raw exif/i)).toBeInTheDocument();
  });

  it('shows CSV options when format is csv', () => {
    render(
      <FormatOptionsPanel
        format="csv"
        options={{}}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/include utf-8 bom/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/delimiter/i)).toBeInTheDocument();
  });

  it('calls onChange with updated options when checkbox toggled', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <FormatOptionsPanel
        format="darwin_core"
        options={{ validate: false }}
        onChange={onChange}
      />
    );

    const validateCheckbox = screen.getByLabelText(/validate output/i);
    await user.click(validateCheckbox);

    expect(onChange).toHaveBeenCalledWith({ validate: true });
  });

  it('calls onChange when delimiter select changed', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <FormatOptionsPanel
        format="csv"
        options={{ delimiter: ',' }}
        onChange={onChange}
      />
    );

    const delimiterSelect = screen.getByLabelText(/delimiter/i);
    await user.selectOptions(delimiterSelect, '\t');

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ delimiter: '\t' }));
  });

  it('respects disabled prop for all controls', () => {
    render(
      <FormatOptionsPanel
        format="darwin_core"
        options={{}}
        onChange={vi.fn()}
        disabled
      />
    );

    expect(screen.getByLabelText(/validate output/i)).toBeDisabled();
    expect(screen.getByLabelText(/include validation warnings/i)).toBeDisabled();
  });

  it('shows default values for iNaturalist options', () => {
    render(
      <FormatOptionsPanel
        format="inaturalist"
        options={{
          include_xmp_sidecars: true,
          include_manifest: true,
          include_csv_summary: false,
        }}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/include xmp sidecar/i)).toBeChecked();
    expect(screen.getByLabelText(/include manifest/i)).toBeChecked();
    expect(screen.getByLabelText(/include csv summary/i)).not.toBeChecked();
  });

  it('shows default values for JSON options', () => {
    render(
      <FormatOptionsPanel
        format="json"
        options={{
          pretty_print: true,
          include_raw_exif: false,
        }}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/pretty print/i)).toBeChecked();
    expect(screen.getByLabelText(/include raw exif/i)).not.toBeChecked();
  });

  it('shows default values for CSV options', () => {
    render(
      <FormatOptionsPanel
        format="csv"
        options={{
          include_bom: true,
          delimiter: ',',
        }}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/include utf-8 bom/i)).toBeChecked();
    expect(screen.getByLabelText(/delimiter/i)).toHaveValue(',');
  });

  it('shows delimiter options: comma, tab, semicolon', () => {
    render(
      <FormatOptionsPanel
        format="csv"
        options={{ delimiter: ',' }}
        onChange={vi.fn()}
      />
    );

    const delimiterSelect = screen.getByLabelText(/delimiter/i);
    const options = Array.from(delimiterSelect.options).map(opt => opt.value);

    expect(options).toContain(',');
    expect(options).toContain('\t');
    expect(options).toContain(';');
  });

  it('renders nothing when format is null', () => {
    const { container } = render(
      <FormatOptionsPanel
        format={null}
        options={{}}
        onChange={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('updates only changed option while preserving others', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <FormatOptionsPanel
        format="json"
        options={{
          pretty_print: true,
          include_raw_exif: false,
        }}
        onChange={onChange}
      />
    );

    const rawExifCheckbox = screen.getByLabelText(/include raw exif/i);
    await user.click(rawExifCheckbox);

    expect(onChange).toHaveBeenCalledWith({
      pretty_print: true,
      include_raw_exif: true,
    });
  });
});
