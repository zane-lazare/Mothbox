import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SchedulerHeader from '../SchedulerHeader';

describe('SchedulerHeader', () => {
  it('renders title "Scheduler"', () => {
    render(<SchedulerHeader />);

    const heading = screen.getByRole('heading', { name: /scheduler/i });
    expect(heading).toBeInTheDocument();
  });

  it('renders children in toolbar area', () => {
    render(
      <SchedulerHeader>
        <button>Test Button</button>
      </SchedulerHeader>
    );

    const button = screen.getByRole('button', { name: /test button/i });
    expect(button).toBeInTheDocument();
  });

  it('applies responsive classes', () => {
    const { container } = render(<SchedulerHeader />);

    // Check for responsive flex classes
    const headerContainer = container.querySelector('.flex');
    expect(headerContainer).toBeInTheDocument();
    expect(headerContainer).toHaveClass('flex-col');
    expect(headerContainer).toHaveClass('md:flex-row');
  });

  it('has proper heading hierarchy (h2)', () => {
    render(<SchedulerHeader />);

    const heading = screen.getByRole('heading', { name: /scheduler/i });
    expect(heading.tagName).toBe('H2');
  });

  it('applies correct title styling', () => {
    render(<SchedulerHeader />);

    const heading = screen.getByRole('heading', { name: /scheduler/i });
    expect(heading).toHaveClass('text-xl');
    expect(heading).toHaveClass('font-bold');
    expect(heading).toHaveClass('text-gray-900');
  });
});
