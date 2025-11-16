import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useScrollRestoration from '../useScrollRestoration';

describe('useScrollRestoration', () => {
  let mockSessionStorage;

  beforeEach(() => {
    // Mock sessionStorage
    mockSessionStorage = {
      data: {},
      getItem: vi.fn((key) => mockSessionStorage.data[key] || null),
      setItem: vi.fn((key, value) => {
        mockSessionStorage.data[key] = value;
      }),
      removeItem: vi.fn((key) => {
        delete mockSessionStorage.data[key];
      }),
      clear: vi.fn(() => {
        mockSessionStorage.data = {};
      })
    };

    global.sessionStorage = mockSessionStorage;

    // Mock console methods to suppress expected logs in tests
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    mockSessionStorage.data = {};
  });

  describe('Initialization', () => {
    it('initializes scroll ref', () => {
      const { result } = renderHook(() => useScrollRestoration());

      expect(result.current.scrollRef).toBeDefined();
      expect(result.current.scrollRef.current).toBeNull();
    });

    it('provides saveScrollPosition function', () => {
      const { result } = renderHook(() => useScrollRestoration());

      expect(result.current.saveScrollPosition).toBeTypeOf('function');
    });

    it('provides scrollTo function', () => {
      const { result } = renderHook(() => useScrollRestoration());

      expect(result.current.scrollTo).toBeTypeOf('function');
    });

    it('uses default key when not provided', () => {
      const { result } = renderHook(() => useScrollRestoration());

      expect(result.current).toBeDefined();
    });

    it('uses custom key when provided', () => {
      const { result } = renderHook(() => useScrollRestoration('gallery'));

      expect(result.current).toBeDefined();
    });
  });

  describe('Saving Scroll Position', () => {
    it('saves scroll position to sessionStorage', () => {
      const { result } = renderHook(() => useScrollRestoration('test'));

      // Create mock element with scrollTop
      const mockElement = {
        scrollTop: 1500
      };
      result.current.scrollRef.current = mockElement;

      act(() => {
        result.current.saveScrollPosition();
      });

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        'gallery-scroll-position-test',
        expect.stringContaining('"scrollTop":1500')
      );
    });

    it('includes timestamp in saved position', () => {
      const { result } = renderHook(() => useScrollRestoration('test'));

      const mockElement = { scrollTop: 500 };
      result.current.scrollRef.current = mockElement;

      const beforeTime = Date.now();
      act(() => {
        result.current.saveScrollPosition();
      });
      const afterTime = Date.now();

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-test']);
      expect(savedData.timestamp).toBeGreaterThanOrEqual(beforeTime);
      expect(savedData.timestamp).toBeLessThanOrEqual(afterTime);
    });

    it('includes key in saved position', () => {
      const { result } = renderHook(() => useScrollRestoration('gallery-page'));

      const mockElement = { scrollTop: 300 };
      result.current.scrollRef.current = mockElement;

      act(() => {
        result.current.saveScrollPosition();
      });

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-gallery-page']);
      expect(savedData.key).toBe('gallery-page');
    });

    it('handles null scrollRef gracefully', () => {
      const { result } = renderHook(() => useScrollRestoration());

      result.current.scrollRef.current = null;

      expect(() => {
        act(() => {
          result.current.saveScrollPosition();
        });
      }).not.toThrow();

      expect(mockSessionStorage.setItem).not.toHaveBeenCalled();
    });

    it('overwrites previous saved position', () => {
      const { result } = renderHook(() => useScrollRestoration());

      const mockElement = { scrollTop: 100 };
      result.current.scrollRef.current = mockElement;

      act(() => {
        result.current.saveScrollPosition();
      });

      mockElement.scrollTop = 500;

      act(() => {
        result.current.saveScrollPosition();
      });

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-default']);
      expect(savedData.scrollTop).toBe(500);
    });
  });

  describe('Restoring Scroll Position', () => {
    it('restores scroll position on mount', () => {
      vi.useFakeTimers();

      // Save a position first
      const savedPosition = {
        scrollTop: 800,
        timestamp: Date.now(),
        key: 'test'
      };
      mockSessionStorage.data['gallery-scroll-position-test'] = JSON.stringify(savedPosition);

      const { result } = renderHook(() => useScrollRestoration('test'));

      // Create mock element
      const mockScrollTo = vi.fn();
      const mockElement = {
        scrollTop: 0,
        scrollTo: mockScrollTo
      };
      result.current.scrollRef.current = mockElement;

      // Fast-forward setTimeout
      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(mockScrollTo).toHaveBeenCalledWith({ scrollTop: 800 });

      vi.useRealTimers();
    });

    it('does not restore if no saved position exists', () => {
      vi.useFakeTimers();

      const { result } = renderHook(() => useScrollRestoration('test'));

      const mockScrollTo = vi.fn();
      const mockElement = { scrollTo: mockScrollTo };
      result.current.scrollRef.current = mockElement;

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(mockScrollTo).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('does not restore if saved position is stale (>5min)', () => {
      vi.useFakeTimers();

      // Save position from 6 minutes ago (exceeds 5min TTL)
      const stalePosition = {
        scrollTop: 500,
        timestamp: Date.now() - 360000, // 6 minutes
        key: 'test'
      };
      mockSessionStorage.data['gallery-scroll-position-test'] = JSON.stringify(stalePosition);

      const { result } = renderHook(() => useScrollRestoration('test'));

      const mockScrollTo = vi.fn();
      result.current.scrollRef.current = { scrollTo: mockScrollTo };

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(mockScrollTo).not.toHaveBeenCalled();
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('gallery-scroll-position-test');

      vi.useRealTimers();
    });

    it('does not restore if key does not match', () => {
      vi.useFakeTimers();

      const savedPosition = {
        scrollTop: 300,
        timestamp: Date.now(),
        key: 'different-key'
      };
      mockSessionStorage.data['gallery-scroll-position-test-key'] = JSON.stringify(savedPosition);

      const { result } = renderHook(() => useScrollRestoration('test-key'));

      const mockScrollTo = vi.fn();
      result.current.scrollRef.current = { scrollTo: mockScrollTo };

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(mockScrollTo).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('handles corrupted sessionStorage data gracefully', () => {
      mockSessionStorage.data['gallery-scroll-position-test'] = 'invalid-json';

      expect(() => {
        renderHook(() => useScrollRestoration('test'));
      }).not.toThrow();

      expect(console.warn).toHaveBeenCalled();
    });
  });

  describe('Manual Scroll Control', () => {
    it('scrollTo works with react-window grid ref', () => {
      const { result } = renderHook(() => useScrollRestoration());

      const mockScrollTo = vi.fn();
      const mockGridRef = {
        scrollTo: mockScrollTo
      };
      result.current.scrollRef.current = mockGridRef;

      act(() => {
        result.current.scrollTo(1200);
      });

      expect(mockScrollTo).toHaveBeenCalledWith({ scrollTop: 1200 });
    });

    it('scrollTo works with native scrollTop', () => {
      const { result } = renderHook(() => useScrollRestoration());

      const mockElement = {
        scrollTop: 0
      };
      result.current.scrollRef.current = mockElement;

      act(() => {
        result.current.scrollTo(600);
      });

      expect(mockElement.scrollTop).toBe(600);
    });

    it('scrollTo handles null ref gracefully', () => {
      const { result } = renderHook(() => useScrollRestoration());

      result.current.scrollRef.current = null;

      expect(() => {
        act(() => {
          result.current.scrollTo(500);
        });
      }).not.toThrow();
    });
  });

  describe('TTL and Cleanup', () => {
    it('respects 5 minute TTL', () => {
      vi.useFakeTimers();

      const now = Date.now();

      // Position saved 4 minutes ago (within 5min TTL)
      const recentPosition = {
        scrollTop: 400,
        timestamp: now - 240000, // 4 minutes
        key: 'test'
      };
      mockSessionStorage.data['gallery-scroll-position-test'] = JSON.stringify(recentPosition);

      const { result } = renderHook(() => useScrollRestoration('test'));

      const mockScrollTo = vi.fn();
      result.current.scrollRef.current = { scrollTo: mockScrollTo };

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(mockScrollTo).toHaveBeenCalledWith({ scrollTop: 400 });

      vi.useRealTimers();
    });

    it('clears stale positions on restore attempt', () => {
      vi.useFakeTimers();

      const stalePosition = {
        scrollTop: 100,
        timestamp: Date.now() - 360000, // 6 minutes ago (exceeds 5min TTL)
        key: 'test'
      };
      mockSessionStorage.data['gallery-scroll-position-test'] = JSON.stringify(stalePosition);

      renderHook(() => useScrollRestoration('test'));

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('gallery-scroll-position-test');

      vi.useRealTimers();
    });
  });

  describe('Edge Cases', () => {
    it('handles missing sessionStorage gracefully', () => {
      const originalSessionStorage = global.sessionStorage;
      global.sessionStorage = undefined;

      // Should not throw - gracefully degrades when sessionStorage is unavailable
      expect(() => {
        renderHook(() => useScrollRestoration());
      }).not.toThrow();

      global.sessionStorage = originalSessionStorage;
    });

    it('handles rapid save calls', () => {
      const { result } = renderHook(() => useScrollRestoration());

      const mockElement = { scrollTop: 100 };
      result.current.scrollRef.current = mockElement;

      act(() => {
        result.current.saveScrollPosition();
        mockElement.scrollTop = 200;
        result.current.saveScrollPosition();
        mockElement.scrollTop = 300;
        result.current.saveScrollPosition();
      });

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-default']);
      expect(savedData.scrollTop).toBe(300);
    });

    it('handles ref changes after mount', () => {
      const { result } = renderHook(() => useScrollRestoration());

      const mockElement1 = { scrollTop: 100 };
      result.current.scrollRef.current = mockElement1;

      act(() => {
        result.current.saveScrollPosition();
      });

      const mockElement2 = { scrollTop: 500 };
      result.current.scrollRef.current = mockElement2;

      act(() => {
        result.current.saveScrollPosition();
      });

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-default']);
      expect(savedData.scrollTop).toBe(500);
    });

    it('works with zero scroll position', () => {
      const { result } = renderHook(() => useScrollRestoration());

      const mockElement = { scrollTop: 0 };
      result.current.scrollRef.current = mockElement;

      act(() => {
        result.current.saveScrollPosition();
      });

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-default']);
      expect(savedData.scrollTop).toBe(0);
    });
  });

  describe('Multiple Instances', () => {
    it('different keys maintain separate scroll positions', () => {
      const { result: result1 } = renderHook(() => useScrollRestoration('page1'));
      const { result: result2 } = renderHook(() => useScrollRestoration('page2'));

      const mockElement1 = { scrollTop: 100 };
      const mockElement2 = { scrollTop: 500 };

      result1.current.scrollRef.current = mockElement1;
      result2.current.scrollRef.current = mockElement2;

      act(() => {
        result1.current.saveScrollPosition();
      });

      const savedData = JSON.parse(mockSessionStorage.data['gallery-scroll-position-page1']);
      expect(savedData.scrollTop).toBe(100);
      expect(savedData.key).toBe('page1');
    });
  });
});
