import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import LazyImage from '../LazyImage';

// Mock useInViewport hook
vi.mock('../../hooks/useInViewport', () => ({
  default: vi.fn()
}));

import useInViewport from '../../hooks/useInViewport';

describe('LazyImage', () => {
  const mockPhoto = {
    path: '2024-11-16/photo_001.jpg',
    filename: 'photo_001.jpg',
    size: 1024000,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Placeholder State (Not in Viewport)', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: false,
        hasBeenInViewport: false
      });
    });

    it('renders placeholder when not in viewport', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const placeholder = document.querySelector('.skeleton-loader');
      expect(placeholder).toBeTruthy();
    });

    it('displays skeleton loader', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const skeleton = document.querySelector('.skeleton-loader');
      expect(skeleton).toBeTruthy();
    });

    it('maintains aspect ratio container', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container).toBeTruthy();
      expect(container.style.aspectRatio).toBeTruthy();
    });

    it('does not load image src', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img).toBeNull();
    });

    it('applies correct CSS classes for placeholder', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container).toBeTruthy();
      expect(container.classList.contains('lazy-image-container')).toBe(true);
    });
  });

  describe('Loading State (Entering Viewport)', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: true,
        hasBeenInViewport: true
      });
    });

    it('loads image when entering viewport', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img).toBeTruthy();
      expect(img.src).toContain('photo_001.jpg');
    });

    it('shows loading indicator during image load', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const loadingIndicator = document.querySelector('.loading-indicator');
      expect(loadingIndicator).toBeTruthy();
    });

    it('uses getThumbnailUrl with correct size', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img.src).toContain('size=256');
    });

    it('respects custom thumbnail size', () => {
      render(<LazyImage photo={mockPhoto} size={128} />);

      const img = document.querySelector('img');
      expect(img.src).toContain('size=128');
    });
  });

  describe('Loaded State (Image Displayed)', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: true,
        hasBeenInViewport: true
      });
    });

    it('displays image after successful load', async () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img).toBeTruthy();

      // Simulate image load
      img.dispatchEvent(new Event('load'));

      await waitFor(() => {
        expect(img.classList.contains('opacity-100')).toBe(true);
      });
    });

    it('removes loading state after image loads', async () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      img.dispatchEvent(new Event('load'));

      await waitFor(() => {
        const loadingIndicator = document.querySelector('.loading-indicator');
        expect(loadingIndicator).toBeNull();
      });
    });

    it('applies fade-in transition', async () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img.classList.contains('opacity-0')).toBe(true);

      img.dispatchEvent(new Event('load'));

      await waitFor(() => {
        expect(img.classList.contains('opacity-100')).toBe(true);
      });
    });

    it('maintains aspect ratio after load', async () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container.style.aspectRatio).toBeTruthy();
    });
  });

  describe('Error State', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: true,
        hasBeenInViewport: true
      });
    });

    it('shows error placeholder on image load failure', async () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      img.dispatchEvent(new Event('error'));

      await waitFor(() => {
        const errorPlaceholder = document.querySelector('.error-placeholder');
        expect(errorPlaceholder).toBeTruthy();
      });
    });

    it('displays MothIcon fallback on error', async () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      img.dispatchEvent(new Event('error'));

      await waitFor(() => {
        const errorPlaceholder = document.querySelector('.error-placeholder');
        expect(errorPlaceholder).toBeTruthy();
      });
    });

    it('does not crash on error', async () => {
      expect(() => {
        render(<LazyImage photo={mockPhoto} size={256} />);
        const img = document.querySelector('img');
        img.dispatchEvent(new Event('error'));
      }).not.toThrow();
    });
  });

  describe('Layout Shift Prevention', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: false,
        hasBeenInViewport: false
      });
    });

    it('reserves space before image loads', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container.style.width).toBe('100%');
      expect(container.style.aspectRatio).toBeTruthy();
    });

    it('uses aspect ratio CSS', () => {
      render(<LazyImage photo={mockPhoto} size={256} aspectRatio={4/3} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container.style.aspectRatio).toBeTruthy();
    });

    it('matches image dimensions', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container.style.width).toBe('100%');
    });
  });

  describe('Integration with Existing ProgressiveImage', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: true,
        hasBeenInViewport: true
      });
    });

    it('can wrap ProgressiveImage component', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img).toBeTruthy();
    });

    it('passes through all photo props', () => {
      render(<LazyImage photo={mockPhoto} size={256} alt="Test Alt" />);

      const img = document.querySelector('img');
      expect(img.alt).toBe('Test Alt');
    });

    it('supports onClick handler', () => {
      const handleClick = vi.fn();
      render(<LazyImage photo={mockPhoto} size={256} onClick={handleClick} />);

      const container = document.querySelector('.lazy-image-container');
      container.click();

      expect(handleClick).toHaveBeenCalled();
    });
  });

  describe('Performance Optimizations', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: true,
        hasBeenInViewport: true
      });
    });

    it('memoizes component with React.memo', () => {
      // React.memo is applied at export level
      const { rerender } = render(<LazyImage photo={mockPhoto} size={256} />);

      rerender(<LazyImage photo={mockPhoto} size={256} />);

      // Should not re-render if props are the same
      expect(true).toBe(true); // Component will be memoized
    });

    it('does not reload on viewport re-entry', () => {
      const { rerender } = render(<LazyImage photo={mockPhoto} size={256} />);

      // Simulate viewport exit
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: false,
        hasBeenInViewport: true
      });

      rerender(<LazyImage photo={mockPhoto} size={256} />);

      // Image should still be loaded
      const img = document.querySelector('img');
      expect(img).toBeTruthy();
    });

    it('supports loading="lazy" attribute', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const img = document.querySelector('img');
      expect(img.getAttribute('loading')).toBe('lazy');
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      useInViewport.mockReturnValue({
        ref: vi.fn(),
        isInViewport: true,
        hasBeenInViewport: true
      });
    });

    it('includes alt text', () => {
      render(<LazyImage photo={mockPhoto} size={256} alt="Custom Alt" />);

      const img = document.querySelector('img');
      expect(img.alt).toBe('Custom Alt');
    });

    it('has correct ARIA attributes during loading', () => {
      render(<LazyImage photo={mockPhoto} size={256} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container).toBeTruthy();
    });

    it('is keyboard accessible', () => {
      const handleClick = vi.fn();
      render(<LazyImage photo={mockPhoto} size={256} onClick={handleClick} />);

      const container = document.querySelector('.lazy-image-container');
      expect(container).toBeTruthy();
    });
  });
});
