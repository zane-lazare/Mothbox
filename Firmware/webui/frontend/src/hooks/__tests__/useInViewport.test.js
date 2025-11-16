import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useInViewport from '../useInViewport';

describe('useInViewport', () => {
  let observerCallback;
  let observerInstance;

  beforeEach(() => {
    // Mock IntersectionObserver
    global.IntersectionObserver = vi.fn((callback) => {
      observerCallback = callback;
      observerInstance = {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      };
      return observerInstance;
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Functionality', () => {
    it('initializes with isInViewport: false', () => {
      const { result } = renderHook(() => useInViewport());

      expect(result.current.isInViewport).toBe(false);
      expect(result.current.hasBeenInViewport).toBe(false);
    });

    it('provides a ref for element attachment', () => {
      const { result } = renderHook(() => useInViewport());

      expect(result.current.ref).toBeTypeOf('function');
    });

    it('creates IntersectionObserver on mount', () => {
      renderHook(() => useInViewport());

      expect(global.IntersectionObserver).toHaveBeenCalledTimes(1);
    });

    it('observes element when ref is attached', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      act(() => {
        result.current.ref(mockElement);
      });

      expect(observerInstance.observe).toHaveBeenCalledWith(mockElement);
    });
  });

  describe('Viewport Entry Detection', () => {
    it('sets isInViewport to true when element enters viewport', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      act(() => {
        result.current.ref(mockElement);
      });

      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: true }]);
      });

      expect(result.current.isInViewport).toBe(true);
    });

    it('sets hasBeenInViewport to true on first entry', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      act(() => {
        result.current.ref(mockElement);
      });

      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: true }]);
      });

      expect(result.current.hasBeenInViewport).toBe(true);
    });

    it('sets isInViewport to false when element exits viewport', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      act(() => {
        result.current.ref(mockElement);
      });

      // Enter viewport
      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: true }]);
      });

      // Exit viewport
      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: false }]);
      });

      expect(result.current.isInViewport).toBe(false);
    });

    it('keeps hasBeenInViewport true after exit', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      act(() => {
        result.current.ref(mockElement);
      });

      // Enter viewport
      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: true }]);
      });

      // Exit viewport
      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: false }]);
      });

      expect(result.current.hasBeenInViewport).toBe(true);
    });
  });

  describe('Configuration Options', () => {
    it('uses default rootMargin if not provided', () => {
      renderHook(() => useInViewport());

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ rootMargin: '0px' })
      );
    });

    it('respects custom rootMargin', () => {
      renderHook(() => useInViewport({ rootMargin: '100px' }));

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ rootMargin: '100px' })
      );
    });

    it('uses default threshold if not provided', () => {
      renderHook(() => useInViewport());

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ threshold: 0.1 })
      );
    });

    it('respects custom threshold', () => {
      renderHook(() => useInViewport({ threshold: 0.5 }));

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ threshold: 0.5 })
      );
    });

    it('respects root option', () => {
      const rootElement = document.createElement('div');
      renderHook(() => useInViewport({ root: rootElement }));

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ root: rootElement })
      );
    });
  });

  describe('Edge Cases and Cleanup', () => {
    it('handles multiple rapid intersections', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      act(() => {
        result.current.ref(mockElement);
      });

      // Rapid transitions
      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: true }]);
        observerCallback([{ target: mockElement, isIntersecting: false }]);
        observerCallback([{ target: mockElement, isIntersecting: true }]);
        observerCallback([{ target: mockElement, isIntersecting: false }]);
      });

      expect(result.current.isInViewport).toBe(false);
      expect(result.current.hasBeenInViewport).toBe(true);
    });

    it('handles ref changes', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement1 = document.createElement('div');
      const mockElement2 = document.createElement('div');

      act(() => {
        result.current.ref(mockElement1);
      });

      expect(observerInstance.observe).toHaveBeenCalledWith(mockElement1);

      // Change ref to new element
      act(() => {
        result.current.ref(mockElement2);
      });

      expect(observerInstance.unobserve).toHaveBeenCalledWith(mockElement1);
      expect(observerInstance.observe).toHaveBeenCalledWith(mockElement2);
    });

    it('handles null ref', () => {
      const { result } = renderHook(() => useInViewport());

      expect(() => {
        act(() => {
          result.current.ref(null);
        });
      }).not.toThrow();
    });

    it('disconnects observer on unmount', () => {
      const { unmount } = renderHook(() => useInViewport());

      unmount();

      expect(observerInstance.disconnect).toHaveBeenCalled();
    });

    it('unobserves previous element when ref changes', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement1 = document.createElement('div');
      const mockElement2 = document.createElement('div');

      act(() => {
        result.current.ref(mockElement1);
      });

      act(() => {
        result.current.ref(mockElement2);
      });

      expect(observerInstance.unobserve).toHaveBeenCalledWith(mockElement1);
    });
  });

  describe('Integration with react-window', () => {
    it('works with overscan (rootMargin)', () => {
      renderHook(() => useInViewport({ rootMargin: '-50px' }));

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({ rootMargin: '-50px' })
      );
    });

    it('integrates with virtual scrolling', () => {
      const { result } = renderHook(() => useInViewport());
      const mockElement = document.createElement('div');

      // Simulate element mounting
      act(() => {
        result.current.ref(mockElement);
      });

      // Element enters viewport
      act(() => {
        observerCallback([{ target: mockElement, isIntersecting: true }]);
      });

      // Element gets unmounted (virtual scrolling)
      act(() => {
        result.current.ref(null);
      });

      expect(observerInstance.unobserve).toHaveBeenCalledWith(mockElement);
    });
  });
});
