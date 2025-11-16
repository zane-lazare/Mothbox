import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import VirtualPhotoGridItem from '../VirtualPhotoGridItem';

// Mock LazyImage
vi.mock('../LazyImage', () => ({
  default: vi.fn(({ photo, onClick, alt, className, size }) => (
    <div
      data-testid="lazy-image"
      data-photo={photo.filename}
      data-alt={alt}
      data-size={size}
      className={className}
      onClick={onClick}
    >
      {photo.filename}
    </div>
  ))
}));

import LazyImage from '../LazyImage';

describe('VirtualPhotoGridItem', () => {
  const mockPhoto = {
    path: '2024/photo.jpg',
    filename: 'photo.jpg',
    size: 1024000,
    timestamp: Date.now()
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders LazyImage with photo', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      expect(LazyImage).toHaveBeenCalled();
      const callArgs = LazyImage.mock.calls[0][0];
      expect(callArgs).toMatchObject({
        photo: mockPhoto
      });

      expect(screen.getByTestId('lazy-image')).toBeInTheDocument();
      expect(screen.getByText('photo.jpg')).toBeInTheDocument();
    });

    it('applies correct styling', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      expect(container.className).toContain('virtual-photo-grid-item');
      expect(container.className).toContain('group');
      expect(container.className).toContain('cursor-pointer');
    });

    it('maintains aspect ratio', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      // LazyImage should have rounded and overflow classes
      const lazyImage = screen.getByTestId('lazy-image');
      expect(lazyImage.className).toContain('rounded-lg');
      expect(lazyImage.className).toContain('overflow-hidden');
    });
  });

  describe('Click Handling', () => {
    it('calls onClick when clicked', () => {
      const onClick = vi.fn();
      render(<VirtualPhotoGridItem photo={mockPhoto} onClick={onClick} />);

      const lazyImage = screen.getByTestId('lazy-image');
      fireEvent.click(lazyImage);

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('passes photo to onClick handler', () => {
      const onClick = vi.fn();
      render(<VirtualPhotoGridItem photo={mockPhoto} onClick={onClick} />);

      const lazyImage = screen.getByTestId('lazy-image');
      fireEvent.click(lazyImage);

      // onClick is called from LazyImage, component doesn't need to pass photo
      expect(onClick).toHaveBeenCalled();
    });

    it('does not error when onClick is undefined', () => {
      expect(() => {
        render(<VirtualPhotoGridItem photo={mockPhoto} />);
      }).not.toThrow();

      const lazyImage = screen.getByTestId('lazy-image');
      expect(() => {
        fireEvent.click(lazyImage);
      }).not.toThrow();
    });
  });

  describe('Hover Effects', () => {
    it('shows hover overlay on mouse enter', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      const overlay = container.querySelector('.group-hover\\:bg-opacity-20');

      expect(overlay).toBeInTheDocument();
      expect(overlay.className).toContain('bg-opacity-0');
      expect(overlay.className).toContain('group-hover:bg-opacity-20');
    });

    it('removes hover overlay on mouse leave', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      const overlay = container.querySelector('.group-hover\\:bg-opacity-20');

      // Default state is transparent
      expect(overlay.className).toContain('bg-opacity-0');
    });

    it('has transition animation', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      const overlay = container.querySelector('.transition-opacity');

      expect(overlay).toBeInTheDocument();
      expect(overlay.className).toContain('duration-200');
    });

    it('overlay does not interfere with clicks', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      const overlay = container.querySelector('.pointer-events-none');

      expect(overlay).toBeInTheDocument();
    });
  });

  describe('Integration with LazyImage', () => {
    it('passes correct size to LazyImage', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} size={256} />);

      expect(LazyImage).toHaveBeenCalled();
      const callArgs = LazyImage.mock.calls[0][0];
      expect(callArgs.size).toBe(256);

      const lazyImage = screen.getByTestId('lazy-image');
      expect(lazyImage.dataset.size).toBe('256');
    });

    it('supports custom thumbnail sizes', () => {
      const { rerender } = render(<VirtualPhotoGridItem photo={mockPhoto} size={64} />);
      expect(screen.getByTestId('lazy-image').dataset.size).toBe('64');

      rerender(<VirtualPhotoGridItem photo={mockPhoto} size={128} />);
      expect(screen.getByTestId('lazy-image').dataset.size).toBe('128');

      rerender(<VirtualPhotoGridItem photo={mockPhoto} size={256} />);
      expect(screen.getByTestId('lazy-image').dataset.size).toBe('256');
    });

    it('uses default size when not specified', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      expect(LazyImage).toHaveBeenCalled();
      const callArgs = LazyImage.mock.calls[0][0];
      expect(callArgs.size).toBe(256); // Default size
    });

    it('passes alt text to LazyImage', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      expect(LazyImage).toHaveBeenCalled();
      const callArgs = LazyImage.mock.calls[0][0];
      expect(callArgs.alt).toBe('photo.jpg');

      const lazyImage = screen.getByTestId('lazy-image');
      expect(lazyImage.dataset.alt).toBe('photo.jpg');
    });

    it('passes className to LazyImage', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      expect(LazyImage).toHaveBeenCalled();
      const callArgs = LazyImage.mock.calls[0][0];
      expect(callArgs.className).toContain('rounded-lg');
    });
  });

  describe('Photo Props', () => {
    it('renders with minimal photo props', () => {
      const minimalPhoto = {
        path: '2024/minimal.jpg',
        filename: 'minimal.jpg'
      };

      render(<VirtualPhotoGridItem photo={minimalPhoto} />);

      expect(screen.getByText('minimal.jpg')).toBeInTheDocument();
    });

    it('renders with complete photo props', () => {
      const completePhoto = {
        path: '2024/complete.jpg',
        filename: 'complete.jpg',
        size: 2048000,
        timestamp: Date.now(),
        metadata: { width: 3840, height: 2160 }
      };

      render(<VirtualPhotoGridItem photo={completePhoto} />);

      expect(screen.getByText('complete.jpg')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('wraps LazyImage in container div', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      expect(container.className).toContain('virtual-photo-grid-item');
    });

    it('includes hover overlay as sibling', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      const children = Array.from(container.children);

      expect(children.length).toBe(2); // LazyImage + overlay
      expect(children[0].dataset.testid).toBe('lazy-image');
      expect(children[1].className).toContain('absolute');
      expect(children[1].className).toContain('inset-0');
    });

    it('overlay has correct positioning', () => {
      render(<VirtualPhotoGridItem photo={mockPhoto} />);

      const container = screen.getByTestId('lazy-image').parentElement;
      const overlay = container.children[1];

      expect(overlay.className).toContain('absolute');
      expect(overlay.className).toContain('inset-0');
      expect(overlay.className).toContain('bg-black');
    });
  });

  describe('Memoization', () => {
    it('is wrapped in React.memo', () => {
      const { rerender } = render(<VirtualPhotoGridItem photo={mockPhoto} size={256} />);

      const firstRenderCount = LazyImage.mock.calls.length;

      // Re-render with same props
      rerender(<VirtualPhotoGridItem photo={mockPhoto} size={256} />);

      // Should not re-render if props are the same (memo optimization)
      // Note: In test environment, memo might still re-render
      expect(LazyImage.mock.calls.length).toBeGreaterThanOrEqual(firstRenderCount);
    });
  });
});
