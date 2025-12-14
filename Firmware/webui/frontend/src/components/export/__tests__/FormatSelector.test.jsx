import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FormatSelector from '../FormatSelector';

describe('FormatSelector', () => {
  it('renders all 4 format options', () => {
    render(<FormatSelector value={null} onChange={vi.fn()} />);

    expect(screen.getByText('Darwin Core CSV')).toBeInTheDocument();
    expect(screen.getByText('iNaturalist Export')).toBeInTheDocument();
    expect(screen.getByText('JSON Export')).toBeInTheDocument();
    expect(screen.getByText('CSV Export')).toBeInTheDocument();
  });

  it('shows correct format descriptions', () => {
    render(<FormatSelector value={null} onChange={vi.fn()} />);

    expect(screen.getByText(/GBIF biodiversity standard/i)).toBeInTheDocument();
    expect(screen.getByText(/ZIP with photos and XMP sidecar/i)).toBeInTheDocument();
    expect(screen.getByText(/Full metadata export/i)).toBeInTheDocument();
    expect(screen.getByText(/Flat CSV/i)).toBeInTheDocument();
  });

  it('calls onChange with format value when clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FormatSelector value={null} onChange={onChange} />);

    await user.click(screen.getByRole('radio', { name: /Darwin Core CSV/i }));
    expect(onChange).toHaveBeenCalledWith('darwin_core');

    await user.click(screen.getByRole('radio', { name: /iNaturalist Export/i }));
    expect(onChange).toHaveBeenCalledWith('inaturalist');
  });

  it('shows selected state with visual indicator', () => {
    render(<FormatSelector value="darwin_core" onChange={vi.fn()} />);

    const darwinInput = screen.getByRole('radio', { name: /Darwin Core CSV/i });
    expect(darwinInput).toBeChecked();

    const jsonInput = screen.getByRole('radio', { name: /JSON Export/i });
    expect(jsonInput).not.toBeChecked();
  });

  it('supports keyboard navigation with arrow keys', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FormatSelector value="darwin_core" onChange={onChange} />);

    const darwinInput = screen.getByRole('radio', { name: /Darwin Core CSV/i });
    darwinInput.focus();

    await user.keyboard('{ArrowDown}');
    expect(onChange).toHaveBeenCalledWith('inaturalist');
  });

  it('supports space/enter to select', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FormatSelector value={null} onChange={onChange} />);

    const jsonInput = screen.getByRole('radio', { name: /JSON Export/i });
    jsonInput.focus();

    await user.keyboard(' ');
    expect(onChange).toHaveBeenCalledWith('json');
  });

  it('respects disabled prop', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FormatSelector value={null} onChange={onChange} disabled />);

    const darwinInput = screen.getByRole('radio', { name: /Darwin Core CSV/i });
    expect(darwinInput).toBeDisabled();

    await user.click(darwinInput);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('has correct ARIA attributes for accessibility', () => {
    render(<FormatSelector value="darwin_core" onChange={vi.fn()} />);

    const radioGroup = screen.getByRole('radiogroup');
    expect(radioGroup).toHaveAttribute('aria-label', 'Export format');

    const darwinInput = screen.getByRole('radio', { name: /Darwin Core CSV/i });
    expect(darwinInput).toHaveAccessibleName();
    expect(darwinInput).toHaveAttribute('aria-describedby');
  });

  it('displays format icons', () => {
    const { container } = render(<FormatSelector value={null} onChange={vi.fn()} />);

    // Check for SVG icons (heroicons)
    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThanOrEqual(4); // At least one per format
  });

  it('highlights selected card with blue border', () => {
    const { container } = render(<FormatSelector value="darwin_core" onChange={vi.fn()} />);

    // Find the selected card's container
    const selectedCard = container.querySelector('[data-selected="true"]');
    expect(selectedCard).toBeInTheDocument();
    expect(selectedCard).toHaveClass('ring-blue-500');
  });
});
