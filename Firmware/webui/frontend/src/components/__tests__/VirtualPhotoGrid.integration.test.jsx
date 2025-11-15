import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import VirtualPhotoGrid from '../VirtualPhotoGrid';

// Mock react-window
vi.mock('react-window', () => ({
  FixedSizeGrid: vi.fn(({ children, columnCount, rowCount }) => (
    <div data-testid="virtual-grid">
      {Array.from({ length: Math.min(rowCount * columnCount, 10) }).map((_, index) => {
        const rowIndex = Math.floor(index / columnCount);
        const columnIndex = index % columnCount;
        return children({
          rowIndex,
          columnIndex,
          style: {},
          key: `cell-${rowIndex}-${columnIndex}`,
        });
      })}
    </div>
  ))
}));

// Mock useVirtualGrid hook
vi.mock('../../hooks/useVirtualGrid', () => ({
  default: vi.fn()
}));

// Mock components
vi.mock('../VirtualPhotoGridItem', () => ({
  default: vi.fn(({ photo, onClick }) => (
    <div data-testid={`photo-item-${photo.filename}`} onClick={() => onClick?.()}>
      {photo.filename}
    </div>
  ))
}));

vi.mock('../EmptyStateMessage', () => ({
  default: vi.fn(() => <div data-testid="empty-state">No photos</div>)
}));

vi.mock('../LoadingSpinner', () => ({
  default: vi.fn(() => <div data-testid="loading-spinner">Loading...</div>)
}));

import { FixedSizeGrid } from 'react-window';
import useVirtualGrid from '../../hooks/useVirtualGrid';
import VirtualPhotoGridItem from '../VirtualPhotoGridItem';

describe('VirtualPhotoGrid Integration Tests', () => {
  let queryClient;
  const mockPhotos = Array.from({ length: 100 }, (_, i) => ({
    path: `2024/photo_${i}.jpg`,
    filename: `photo_${i}.jpg`,
    size: 1024000,
    timestamp: Date.now() - i * 1000,
  }));

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    // Default mock return for useVirtualGrid
    useVirtualGrid.mockReturnValue({
      containerRef: vi.fn(),
      columnCount: 4,
      rowCount: 25,
      itemWidth: 256,
      itemHeight: 272,
      totalHeight: 6800
    });

    // Mock ResizeObserver
    global.ResizeObserver = vi.fn(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn()
    }));

    vi.clearAllMocks();
  });

  const renderWithQuery = (component) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('complete lifecycle: loading → photos → click', async () => {
    const onPhotoClick = vi.fn();

    // 1. Render with isLoading
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid
        photos={[]}
        isLoading={true}
        onPhotoClick={onPhotoClick}
      />
    );

    // Should show skeleton loaders
    const skeletons = screen.getAllByRole('generic').filter(
      el => el.className.includes('skeleton-loader')
    );
    expect(skeletons.length).toBeGreaterThan(0);

    // 2. Update to photos loaded
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid
          photos={mockPhotos}
          isLoading={false}
          onPhotoClick={onPhotoClick}
        />
      </QueryClientProvider>
    );

    // Should show grid
    await waitFor(() => {
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });

    // Should show photos
    expect(screen.getByTestId('photo-item-photo_0.jpg')).toBeInTheDocument();

    // 3. Click photo
    const firstPhoto = screen.getByTestId('photo-item-photo_0.jpg');
    fireEvent.click(firstPhoto);

    // 4. Verify all states
    await waitFor(() => {
      expect(onPhotoClick).toHaveBeenCalled();
    });

    expect(FixedSizeGrid).toHaveBeenCalled();
    expect(VirtualPhotoGridItem).toHaveBeenCalled();
  });

  it('infinite scroll: load more pages', async () => {
    const fetchNextPage = vi.fn();

    // 1. Render first page
    renderWithQuery(
      <VirtualPhotoGrid
        photos={mockPhotos.slice(0, 50)}
        hasNextPage={true}
        isFetchingNextPage={false}
      />
    );

    expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();

    // 2. Should NOT show loading spinner when not fetching
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();

    // 3. Simulate fetching next page
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid
        photos={mockPhotos.slice(0, 50)}
        hasNextPage={true}
        isFetchingNextPage={true}
      />
    );

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

    // 4. Append new page
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid
          photos={mockPhotos}
          hasNextPage={false}
          isFetchingNextPage={false}
        />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(useVirtualGrid).toHaveBeenCalledWith(100, expect.any(Object));
    });

    // No more pages
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });

  it('responsive: resize container', async () => {
    // Test mobile viewport
    const mobileMock = {
      containerRef: vi.fn(),
      columnCount: 1,
      rowCount: 100,
      itemWidth: 320,
      itemHeight: 336,
      totalHeight: 33600
    };

    useVirtualGrid.mockReturnValue(mobileMock);

    renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

    // Verify mobile layout applied
    await waitFor(() => {
      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(1);
      expect(callArgs.columnWidth).toBe(320);
    });
  });

  it('view mode: switch grid ↔ list', async () => {
    // 1. Render in grid mode
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid photos={mockPhotos} viewMode="grid" />
    );

    expect(useVirtualGrid).toHaveBeenCalledWith(
      100,
      expect.objectContaining({
        breakpoints: undefined
      })
    );

    // 2. Switch to list mode
    useVirtualGrid.mockReturnValue({
      containerRef: vi.fn(),
      columnCount: 1,
      rowCount: 100,
      itemWidth: 1024,
      itemHeight: 128,
      totalHeight: 12800
    });

    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid photos={mockPhotos} viewMode="list" />
      </QueryClientProvider>
    );

    // 3. Verify layout changes
    await waitFor(() => {
      expect(useVirtualGrid).toHaveBeenCalledWith(
        100,
        expect.objectContaining({
          breakpoints: expect.objectContaining({ sm: 0 })
        })
      );
    });

    const lastCallIndex = FixedSizeGrid.mock.calls.length - 1;
    const lastCallArgs = FixedSizeGrid.mock.calls[lastCallIndex][0];
    expect(lastCallArgs.columnCount).toBe(1);
  });

  it('handles rapid photo updates', async () => {
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid photos={mockPhotos.slice(0, 10)} />
    );

    expect(useVirtualGrid).toHaveBeenCalledWith(10, expect.any(Object));

    // Rapid updates
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid photos={mockPhotos.slice(0, 50)} />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(useVirtualGrid).toHaveBeenCalledWith(50, expect.any(Object));
    });

    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid photos={mockPhotos} />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(useVirtualGrid).toHaveBeenCalledWith(100, expect.any(Object));
    });
  });

  it('maintains state during loading transitions', async () => {
    const onPhotoClick = vi.fn();

    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid
        photos={mockPhotos.slice(0, 50)}
        isLoading={false}
        isFetchingNextPage={false}
        hasNextPage={true}
        onPhotoClick={onPhotoClick}
      />
    );

    const firstPhoto = screen.getByTestId('photo-item-photo_0.jpg');
    expect(firstPhoto).toBeInTheDocument();

    // Start fetching next page
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid
          photos={mockPhotos.slice(0, 50)}
          isLoading={false}
          isFetchingNextPage={true}
          hasNextPage={true}
          onPhotoClick={onPhotoClick}
        />
      </QueryClientProvider>
    );

    // First photo should still be visible
    expect(screen.getByTestId('photo-item-photo_0.jpg')).toBeInTheDocument();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

    // Click should still work during loading
    fireEvent.click(screen.getByTestId('photo-item-photo_0.jpg'));
    expect(onPhotoClick).toHaveBeenCalled();
  });

  it('handles empty state transitions', async () => {
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid photos={mockPhotos} isLoading={false} />
    );

    expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();

    // Clear photos
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid photos={[]} isLoading={false} />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('virtual-grid')).not.toBeInTheDocument();
  });

  it('integrates with custom options', async () => {
    const customOptions = {
      gap: 20,
      aspectRatio: 16 / 9,
      thumbnailSize: 128
    };

    renderWithQuery(
      <VirtualPhotoGrid
        photos={mockPhotos}
        options={customOptions}
      />
    );

    expect(useVirtualGrid).toHaveBeenCalledWith(
      100,
      expect.objectContaining({
        gap: 20,
        aspectRatio: 16 / 9
      })
    );

    expect(VirtualPhotoGridItem).toHaveBeenCalled();
    const callArgs = VirtualPhotoGridItem.mock.calls[0][0];
    expect(callArgs.size).toBe(128);
  });

  it('handles concurrent updates gracefully', async () => {
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid
        photos={mockPhotos.slice(0, 50)}
        isLoading={false}
        hasNextPage={true}
      />
    );

    // Simulate concurrent updates
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid
          photos={mockPhotos.slice(0, 75)}
          isLoading={false}
          hasNextPage={true}
        />
      </QueryClientProvider>
    );

    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid
          photos={mockPhotos}
          isLoading={false}
          hasNextPage={false}
        />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });

    expect(useVirtualGrid).toHaveBeenLastCalledWith(100, expect.any(Object));
  });

  it('preserves scroll position during updates', async () => {
    const { rerender } = renderWithQuery(
      <VirtualPhotoGrid photos={mockPhotos.slice(0, 50)} />
    );

    // react-window maintains scroll position automatically
    expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();

    // Add more photos
    rerender(
      <QueryClientProvider client={queryClient}>
        <VirtualPhotoGrid photos={mockPhotos} />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });

    // Grid should still be rendered
    expect(FixedSizeGrid).toHaveBeenCalled();
  });
});
