/**
 * Tests for useVirtualGrid hook
 * Tests MUST be written FIRST (TDD approach)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import useVirtualGrid from '../useVirtualGrid';

describe('useVirtualGrid', () => {
  let resizeObserverCallback;
  let mockResizeObserver;

  beforeEach(() => {
    // Mock ResizeObserver
    mockResizeObserver = {
      observe: vi.fn((element) => {
        // Immediately trigger callback with element's width
        if (resizeObserverCallback && element) {
          const width = element.offsetWidth || 0;
          resizeObserverCallback([{ contentRect: { width } }]);
        }
      }),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    };

    global.ResizeObserver = vi.fn((callback) => {
      resizeObserverCallback = callback;
      return mockResizeObserver;
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it('initializes with container ref', () => {
    const { result } = renderHook(() => useVirtualGrid(100));

    expect(result.current).toHaveProperty('containerRef');
    expect(result.current.containerRef).toBeDefined();
    expect(typeof result.current.containerRef).toBe('function'); // Callback ref
  });

  it('calculates grid dimensions from container width', async () => {
    const { result } = renderHook(() => useVirtualGrid(100));

    // Attach mock element to callback ref
    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(4);
    });

    expect(result.current.rowCount).toBe(25);
    expect(result.current.itemWidth).toBeGreaterThan(0);
    expect(result.current.itemHeight).toBeGreaterThan(0);
    expect(result.current.totalHeight).toBeGreaterThan(0);
  });

  it('provides correct grid parameters for react-window', async () => {
    const { result } = renderHook(() => useVirtualGrid(48));

    const mockElement = { offsetWidth: 768 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBeDefined();
    });

    expect(result.current).toHaveProperty('columnCount');
    expect(result.current).toHaveProperty('rowCount');
    expect(result.current).toHaveProperty('itemWidth');
    expect(result.current).toHaveProperty('itemHeight');
    expect(result.current).toHaveProperty('totalHeight');

    expect(typeof result.current.columnCount).toBe('number');
    expect(typeof result.current.rowCount).toBe('number');
    expect(typeof result.current.itemWidth).toBe('number');
    expect(typeof result.current.itemHeight).toBe('number');
    expect(typeof result.current.totalHeight).toBe('number');
  });

  it('updates when photo count changes', async () => {
    const { result, rerender } = renderHook(
      ({ photoCount }) => useVirtualGrid(photoCount),
      { initialProps: { photoCount: 50 } }
    );

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.rowCount).toBe(13);
    });

    const initialHeight = result.current.totalHeight;

    rerender({ photoCount: 100 });

    await waitFor(() => {
      expect(result.current.rowCount).toBe(25);
    });

    expect(result.current.totalHeight).toBeGreaterThan(initialHeight);
  });

  it('handles ref changes', async () => {
    const { result } = renderHook(() => useVirtualGrid(100));

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(4);
    });

    expect(mockResizeObserver.observe).toHaveBeenCalled();
  });

  it('cleans up on unmount', () => {
    const { result, unmount } = renderHook(() => useVirtualGrid(100));

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    expect(global.ResizeObserver).toHaveBeenCalled();

    unmount();

    expect(mockResizeObserver.disconnect).toHaveBeenCalled();
  });

  it('handles empty gallery (zero photos)', async () => {
    const { result } = renderHook(() => useVirtualGrid(0));

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(4);
    });

    expect(result.current.rowCount).toBe(0);
    expect(result.current.totalHeight).toBe(0);
  });

  it('handles single photo', async () => {
    const { result } = renderHook(() => useVirtualGrid(1));

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(4);
    });

    expect(result.current.rowCount).toBe(1);
  });

  it('handles mobile viewport (320px)', async () => {
    const { result } = renderHook(() => useVirtualGrid(50));

    const mockElement = { offsetWidth: 320 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(1);
    });

    expect(result.current.rowCount).toBe(50);
  });

  it('handles tablet viewport (768px)', async () => {
    const { result } = renderHook(() => useVirtualGrid(90));

    const mockElement = { offsetWidth: 768 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(3);
    });

    expect(result.current.rowCount).toBe(30);
  });

  it('handles large desktop viewport (1920px)', async () => {
    const { result } = renderHook(() => useVirtualGrid(120));

    const mockElement = { offsetWidth: 1920 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(6);
    });

    expect(result.current.rowCount).toBe(20);
  });

  it('respects custom options', async () => {
    const customOptions = {
      gap: 24,
      aspectRatio: 16 / 9,
    };

    const { result } = renderHook(() => useVirtualGrid(100, customOptions));

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(4);
    });

    expect(result.current.itemWidth).toBe(238);
    expect(result.current.itemHeight).toBeCloseTo(133.875, 1);
  });

  it('memoizes calculations (same inputs return same object reference)', async () => {
    const { result, rerender } = renderHook(() => useVirtualGrid(100));

    const mockElement = { offsetWidth: 1024 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(4);
    });

    const firstRenderValues = {
      columnCount: result.current.columnCount,
      rowCount: result.current.rowCount,
      itemWidth: result.current.itemWidth,
      itemHeight: result.current.itemHeight,
      totalHeight: result.current.totalHeight,
    };

    rerender();

    expect(result.current.columnCount).toBe(firstRenderValues.columnCount);
    expect(result.current.rowCount).toBe(firstRenderValues.rowCount);
    expect(result.current.itemWidth).toBe(firstRenderValues.itemWidth);
    expect(result.current.itemHeight).toBe(firstRenderValues.itemHeight);
    expect(result.current.totalHeight).toBe(firstRenderValues.totalHeight);
  });

  it('handles very large photo count', async () => {
    const { result } = renderHook(() => useVirtualGrid(10000));

    const mockElement = { offsetWidth: 1920 };
    act(() => {
      result.current.containerRef(mockElement);
    });

    await waitFor(() => {
      expect(result.current.columnCount).toBe(6);
    });

    expect(result.current.rowCount).toBe(Math.ceil(10000 / 6));
    expect(result.current.totalHeight).toBeGreaterThan(0);
  });

  it('initializes with zero width before ResizeObserver triggers', () => {
    const { result } = renderHook(() => useVirtualGrid(100));

    expect(result.current).toHaveProperty('containerRef');
    expect(result.current).toHaveProperty('columnCount');
    expect(result.current).toHaveProperty('rowCount');
  });

  it('observes container element when ref is set', () => {
    const { result } = renderHook(() => useVirtualGrid(100));

    const mockElement = { offsetWidth: 1024 };

    act(() => {
      result.current.containerRef(mockElement);
    });

    expect(global.ResizeObserver).toHaveBeenCalled();
    expect(mockResizeObserver.observe).toHaveBeenCalled();
  });
});
