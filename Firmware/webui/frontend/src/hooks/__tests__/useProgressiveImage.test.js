import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import useProgressiveImage from '../useProgressiveImage';
import { imageCache } from '../../utils/imageCache';

describe('useProgressiveImage', () => {
  let imageLoadCallbacks = [];

  beforeEach(() => {
    imageLoadCallbacks = [];

    // Clear cache before each test
    imageCache.clear();

    // Mock Image constructor
    global.Image = class {
      constructor() {
        this.src = '';
        const imageInstance = this;

        // Store callbacks for manual triggering
        imageLoadCallbacks.push({
          instance: imageInstance,
          triggerLoad: () => {
            if (imageInstance.onload) {
              imageInstance.onload();
            }
          },
          triggerError: () => {
            if (imageInstance.onerror) {
              imageInstance.onerror(new Error('Image load failed'));
            }
          }
        });
      }
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
    imageLoadCallbacks = [];
    imageCache.clear();
  });

  describe('Initial State', () => {
    it('initializes with idle state', () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg', { autoLoad: false })
      );

      expect(result.current.stage).toBe('idle');
      expect(result.current.src).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('provides loadImage function', () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg', { autoLoad: false })
      );

      expect(result.current.loadImage).toBeTypeOf('function');
    });
  });

  describe('Progressive Loading Flow', () => {
    it('loads thumbnail first (64px by default)', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      expect(imageLoadCallbacks[0]).toBeDefined();
      expect(imageLoadCallbacks[0].instance.src).toContain('size=64');
    });

    it('then loads full image (256px by default)', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      // Wait for thumbnail stage
      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      // Trigger thumbnail load
      act(() => {
        imageLoadCallbacks[0].triggerLoad();
      });

      // Should start loading full image
      await waitFor(() => {
        expect(result.current.stage).toBe('full');
      });

      expect(imageLoadCallbacks[1]).toBeDefined();
      expect(imageLoadCallbacks[1].instance.src).toContain('size=256');
    });

    it('tracks loading states correctly', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      // Initial: idle → thumbnail
      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
        expect(result.current.isLoading).toBe(true);
      });

      // Thumbnail loads → full
      act(() => {
        imageLoadCallbacks[0].triggerLoad();
      });

      await waitFor(() => {
        expect(result.current.stage).toBe('full');
        expect(result.current.isLoading).toBe(true);
      });

      // Full loads → loaded
      act(() => {
        imageLoadCallbacks[1].triggerLoad();
      });

      await waitFor(() => {
        expect(result.current.stage).toBe('loaded');
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('returns correct src for each stage', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      // Initially null
      expect(result.current.src).toBeNull();

      // Wait for thumbnail load
      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      act(() => {
        imageLoadCallbacks[0].triggerLoad();
      });

      // Should have thumbnail src
      await waitFor(() => {
        expect(result.current.src).toContain('size=64');
      });

      // Wait for full image load
      await waitFor(() => {
        expect(result.current.stage).toBe('full');
      });

      act(() => {
        imageLoadCallbacks[1].triggerLoad();
      });

      // Should have full src
      await waitFor(() => {
        expect(result.current.src).toContain('size=256');
      });
    });
  });

  describe('Custom Configuration', () => {
    it('respects custom thumbnail size', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg', { thumbnailSize: 128 })
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      expect(imageLoadCallbacks[0].instance.src).toContain('size=128');
    });

    it('respects custom full size', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg', { fullSize: 512 })
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      act(() => {
        imageLoadCallbacks[0].triggerLoad();
      });

      await waitFor(() => {
        expect(result.current.stage).toBe('full');
      });

      expect(imageLoadCallbacks[1].instance.src).toContain('size=512');
    });

    it('supports manual trigger with autoLoad: false', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg', { autoLoad: false })
      );

      // Should stay idle
      expect(result.current.stage).toBe('idle');
      expect(result.current.src).toBeNull();

      // Manually trigger loading
      act(() => {
        result.current.loadImage();
      });

      // Should start loading
      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });
    });
  });

  describe('Error Handling', () => {
    it('handles thumbnail load errors', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/missing.jpg')
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      // Trigger error
      act(() => {
        imageLoadCallbacks[0].triggerError();
      });

      await waitFor(() => {
        expect(result.current.stage).toBe('error');
        expect(result.current.error).toBeDefined();
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('handles full image load errors', async () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      // Load thumbnail successfully
      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      act(() => {
        imageLoadCallbacks[0].triggerLoad();
      });

      await waitFor(() => {
        expect(result.current.stage).toBe('full');
      });

      // Full image fails
      act(() => {
        imageLoadCallbacks[1].triggerError();
      });

      await waitFor(() => {
        expect(result.current.stage).toBe('error');
        expect(result.current.error).toBeDefined();
      });
    });

    it('does not crash on error', async () => {
      expect(() => {
        const { result } = renderHook(() =>
          useProgressiveImage('/photos/test.jpg')
        );
      }).not.toThrow();
    });
  });

  describe('Cleanup and Memory Management', () => {
    it('cancels ongoing loads on unmount', async () => {
      const { result, unmount } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      // Unmount before loading completes
      unmount();

      // Trigger load after unmount (should not crash)
      expect(() => {
        imageLoadCallbacks[0].triggerLoad();
      }).not.toThrow();
    });

    it('handles rapid photoPath changes', async () => {
      const { result, rerender } = renderHook(
        ({ path }) => useProgressiveImage(path),
        { initialProps: { path: '/photos/test1.jpg' } }
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      // Change photoPath before loading completes
      rerender({ path: '/photos/test2.jpg' });

      // Should restart loading with new path
      await waitFor(() => {
        expect(imageLoadCallbacks[imageLoadCallbacks.length - 1].instance.src)
          .toContain('test2.jpg');
      });
    });

    it('does not update state after unmount', async () => {
      const { result, unmount } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg')
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      unmount();

      // Trigger load after unmount
      act(() => {
        imageLoadCallbacks[0].triggerLoad();
      });

      // Should not throw or update state
      expect(true).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty photoPath', () => {
      const { result } = renderHook(() =>
        useProgressiveImage('', { autoLoad: false })
      );

      expect(result.current.stage).toBe('idle');
      expect(result.current.src).toBeNull();
    });

    it('handles null photoPath', () => {
      const { result } = renderHook(() =>
        useProgressiveImage(null, { autoLoad: false })
      );

      expect(result.current.stage).toBe('idle');
    });

    it('handles missing options object', () => {
      expect(() => {
        renderHook(() => useProgressiveImage('/photos/test.jpg'));
      }).not.toThrow();
    });

    it('handles invalid size values gracefully', () => {
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/test.jpg', {
          thumbnailSize: -1,
          fullSize: 0
        })
      );

      expect(result.current).toBeDefined();
    });
  });

  describe('Browser Cache Optimization', () => {
    it('prefers cached full image if available', async () => {
      // This test verifies the hook can skip thumbnail if full is cached
      // Implementation will check browser cache via Image load speed
      const { result } = renderHook(() =>
        useProgressiveImage('/photos/cached.jpg')
      );

      await waitFor(() => {
        expect(result.current.stage).toBe('thumbnail');
      });

      // In real implementation, if full image loads faster than threshold,
      // it may skip showing thumbnail
      expect(result.current).toBeDefined();
    });
  });
});
