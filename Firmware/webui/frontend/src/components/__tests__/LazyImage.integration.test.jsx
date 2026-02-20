import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import LazyImage from '../LazyImage';

describe('LazyImage Integration Tests', () => {
  let observerCallback;
  let observerInstance;

  beforeEach(() => {
    // Mock IntersectionObserver (not the hook, test the real integration)
    global.IntersectionObserver = vi.fn(function (callback) {
      observerCallback = callback;
      observerInstance = {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn()
      };
      return observerInstance;
    });
  });

  it('complete lifecycle: placeholder → loading → loaded', async () => {
    const mockPhoto = {
      path: '2024-11-16/photo_001.jpg',
      filename: 'photo_001.jpg',
      size: 1024000,
    };

    // 1. Render with not in viewport
    const { container } = render(<LazyImage photo={mockPhoto} size={256} />);

    // Initially should show placeholder
    expect(document.querySelector('.skeleton-loader')).toBeTruthy();
    expect(document.querySelector('img')).toBeNull();

    // 2. Trigger intersection
    const mockElement = container.querySelector('.lazy-image-container');
    act(() => {
      observerCallback([{ target: mockElement, isIntersecting: true }]);
    });

    // Should show loading state
    await waitFor(() => {
      expect(document.querySelector('img')).toBeTruthy();
      expect(document.querySelector('.loading-indicator')).toBeTruthy();
    });

    // 3. Wait for image load
    const img = document.querySelector('img');
    act(() => {
      img.dispatchEvent(new Event('load'));
    });

    // 4. Verify all states transitioned correctly
    await waitFor(() => {
      expect(img.classList.contains('opacity-100')).toBe(true);
      expect(document.querySelector('.loading-indicator')).toBeNull();
    });
  });

  it('handles rapid scroll (multiple images)', async () => {
    const photos = [
      { path: '2024-11-16/photo_001.jpg', filename: 'photo_001.jpg', size: 1024000 },
      { path: '2024-11-16/photo_002.jpg', filename: 'photo_002.jpg', size: 1024000 },
      { path: '2024-11-16/photo_003.jpg', filename: 'photo_003.jpg', size: 1024000 },
    ];

    // Store all observer callbacks
    const callbacks = [];
    global.IntersectionObserver = vi.fn(function (callback) {
      callbacks.push(callback);
      return {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn()
      };
    });

    // Render multiple LazyImage components
    const { container } = render(
      <div>
        {photos.map((photo, index) => (
          <LazyImage key={index} photo={photo} size={256} />
        ))}
      </div>
    );

    // Trigger intersections in sequence using each callback
    const containers = container.querySelectorAll('.lazy-image-container');

    act(() => {
      containers.forEach((element, index) => {
        if (callbacks[index]) {
          callbacks[index]([{ target: element, isIntersecting: true }]);
        }
      });
    });

    // Verify all load correctly
    await waitFor(() => {
      const images = document.querySelectorAll('img');
      expect(images.length).toBe(3);
    });
  });

  it('works with virtual scrolling (items mount/unmount)', async () => {
    const mockPhoto = {
      path: '2024-11-16/photo_001.jpg',
      filename: 'photo_001.jpg',
      size: 1024000,
    };

    // Simulate element mounting
    const { unmount, container } = render(<LazyImage photo={mockPhoto} size={256} />);

    const mockElement = container.querySelector('.lazy-image-container');

    // Element enters viewport
    act(() => {
      observerCallback([{ target: mockElement, isIntersecting: true }]);
    });

    await waitFor(() => {
      expect(document.querySelector('img')).toBeTruthy();
    });

    // Element gets unmounted (virtual scrolling)
    unmount();

    expect(observerInstance.disconnect).toHaveBeenCalled();
  });

  it('handles error during image load', async () => {
    const mockPhoto = {
      path: '2024-11-16/photo_invalid.jpg',
      filename: 'photo_invalid.jpg',
      size: 1024000,
    };

    const { container } = render(<LazyImage photo={mockPhoto} size={256} />);

    // Trigger intersection
    const mockElement = container.querySelector('.lazy-image-container');
    act(() => {
      observerCallback([{ target: mockElement, isIntersecting: true }]);
    });

    await waitFor(() => {
      expect(document.querySelector('img')).toBeTruthy();
    });

    // Trigger error
    const img = document.querySelector('img');
    act(() => {
      img.dispatchEvent(new Event('error'));
    });

    // Should show error placeholder
    await waitFor(() => {
      expect(document.querySelector('.error-placeholder')).toBeTruthy();
      expect(document.querySelector('.loading-indicator')).toBeNull();
    });
  });

  it('maintains performance with custom rootMargin', async () => {
    const mockPhoto = {
      path: '2024-11-16/photo_001.jpg',
      filename: 'photo_001.jpg',
      size: 1024000,
    };

    render(<LazyImage photo={mockPhoto} size={256} />);

    // Verify IntersectionObserver created with correct options
    expect(global.IntersectionObserver).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        rootMargin: '100px',
        threshold: 0.1
      })
    );
  });

  it('cleans up observers on component unmount', async () => {
    const mockPhoto = {
      path: '2024-11-16/photo_001.jpg',
      filename: 'photo_001.jpg',
      size: 1024000,
    };

    const { unmount, container } = render(<LazyImage photo={mockPhoto} size={256} />);

    const mockElement = container.querySelector('.lazy-image-container');

    // Trigger intersection
    act(() => {
      observerCallback([{ target: mockElement, isIntersecting: true }]);
    });

    // Unmount component
    unmount();

    // Verify cleanup
    expect(observerInstance.disconnect).toHaveBeenCalled();
  });

  it('handles viewport exit without reloading image', async () => {
    const mockPhoto = {
      path: '2024-11-16/photo_001.jpg',
      filename: 'photo_001.jpg',
      size: 1024000,
    };

    const { container } = render(<LazyImage photo={mockPhoto} size={256} />);

    const mockElement = container.querySelector('.lazy-image-container');

    // Enter viewport
    act(() => {
      observerCallback([{ target: mockElement, isIntersecting: true }]);
    });

    await waitFor(() => {
      expect(document.querySelector('img')).toBeTruthy();
    });

    const imgSrc = document.querySelector('img').src;

    // Load image
    act(() => {
      document.querySelector('img').dispatchEvent(new Event('load'));
    });

    // Exit viewport
    act(() => {
      observerCallback([{ target: mockElement, isIntersecting: false }]);
    });

    // Image should still be there (hasBeenInViewport remains true)
    await waitFor(() => {
      const img = document.querySelector('img');
      expect(img).toBeTruthy();
      expect(img.src).toBe(imgSrc); // Same src, not reloaded
    });
  });
});
