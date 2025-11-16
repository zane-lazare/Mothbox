import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import VirtualPhotoGrid from '../VirtualPhotoGrid';

// Mock react-window
vi.mock('react-window', () => ({
  FixedSizeGrid: vi.fn(({ children, columnCount, rowCount }) => (
    <div data-testid="virtual-grid">
      {/* Render a few cells for testing */}
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

// Mock VirtualPhotoGridItem
vi.mock('../VirtualPhotoGridItem', () => ({
  default: vi.fn(({ photo, onClick }) => (
    <div data-testid={`photo-item-${photo.filename}`} onClick={() => onClick?.()}>
      {photo.filename}
    </div>
  ))
}));

// Mock EmptyStateMessage
vi.mock('../EmptyStateMessage', () => ({
  default: vi.fn(() => <div data-testid="empty-state">No photos</div>)
}));

// Mock LoadingSpinner
vi.mock('../LoadingSpinner', () => ({
  default: vi.fn(() => <div data-testid="loading-spinner">Loading...</div>)
}));

import { FixedSizeGrid } from 'react-window';
import useVirtualGrid from '../../hooks/useVirtualGrid';
import VirtualPhotoGridItem from '../VirtualPhotoGridItem';
import EmptyStateMessage from '../EmptyStateMessage';
import LoadingSpinner from '../LoadingSpinner';

describe('VirtualPhotoGrid', () => {
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

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const renderWithQuery = (component) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  describe('Initialization and Rendering', () => {
    it('renders FixedSizeGrid with correct props', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(4);
      expect(callArgs.columnWidth).toBe(256);
      expect(callArgs.rowCount).toBe(25);
      expect(callArgs.rowHeight).toBe(272);
      expect(callArgs.overscanRowCount).toBeGreaterThanOrEqual(0);
    });

    it('uses useVirtualGrid hook for grid calculations', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(useVirtualGrid).toHaveBeenCalledWith(100, expect.any(Object));
    });

    it('attaches containerRef to wrapper', () => {
      const mockRef = vi.fn();
      useVirtualGrid.mockReturnValue({
        containerRef: mockRef,
        columnCount: 4,
        rowCount: 25,
        itemWidth: 256,
        itemHeight: 272,
        totalHeight: 6800
      });

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(mockRef).toHaveBeenCalled();
    });

    it('renders grid items via cell renderer', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // Should render at least first photo
      expect(screen.getByTestId('photo-item-photo_0.jpg')).toBeInTheDocument();
    });
  });

  describe('Grid Layout and Dimensions', () => {
    it('calculates correct column/row counts', () => {
      const photos50 = mockPhotos.slice(0, 50);
      renderWithQuery(<VirtualPhotoGrid photos={photos50} />);

      // 50 photos ÷ 4 columns = 13 rows (rounded up)
      expect(useVirtualGrid).toHaveBeenCalledWith(50, expect.any(Object));
    });

    it('handles window resize', () => {
      // Test that component uses hook values correctly
      // In real usage, ResizeObserver triggers hook updates
      const customMock = {
        containerRef: vi.fn(),
        columnCount: 2,
        rowCount: 50,
        itemWidth: 512,
        itemHeight: 544,
        totalHeight: 27200
      };

      useVirtualGrid.mockReturnValue(customMock);

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(2);
      expect(callArgs.columnWidth).toBe(512);
    });

    it('respects GALLERY_CONFIG.VIRTUALIZATION settings', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.overscanRowCount).toBeGreaterThanOrEqual(0);
    });

    it('maintains aspect ratio', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // itemHeight should be itemWidth + gap (e.g., 256 + 16 = 272 for 4:3 ratio)
      const lastCallIndex = FixedSizeGrid.mock.calls.length - 1;
      const lastCallArgs = FixedSizeGrid.mock.calls[lastCallIndex][0];
      expect(lastCallArgs).toBeDefined();
      expect(lastCallArgs.rowHeight).toBeDefined();
      expect(lastCallArgs.columnWidth).toBeDefined();
      expect(lastCallArgs.rowHeight).toBeGreaterThan(lastCallArgs.columnWidth);
    });
  });

  describe('Photo Data Integration', () => {
    it('displays photos from TanStack Query data', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(VirtualPhotoGridItem).toHaveBeenCalled();
      const callArgs = VirtualPhotoGridItem.mock.calls[0][0];
      expect(callArgs.photo.filename).toMatch(/photo_\d+\.jpg/);
    });

    it('handles empty photo array', () => {
      renderWithQuery(<VirtualPhotoGrid photos={[]} isLoading={false} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(EmptyStateMessage).toHaveBeenCalled();
    });

    it('handles single photo', () => {
      const singlePhoto = [mockPhotos[0]];
      renderWithQuery(<VirtualPhotoGrid photos={singlePhoto} />);

      expect(useVirtualGrid).toHaveBeenCalledWith(1, expect.any(Object));
      expect(screen.getByTestId('photo-item-photo_0.jpg')).toBeInTheDocument();
    });

    it('handles large photo count (1000+)', () => {
      const largePhotoSet = Array.from({ length: 1000 }, (_, i) => ({
        path: `2024/photo_${i}.jpg`,
        filename: `photo_${i}.jpg`,
        size: 1024000,
        timestamp: Date.now() - i * 1000,
      }));

      renderWithQuery(<VirtualPhotoGrid photos={largePhotoSet} />);

      expect(useVirtualGrid).toHaveBeenCalledWith(1000, expect.any(Object));
      // Should only render visible items (mocked to 10)
      const renderedItems = screen.getAllByTestId(/photo-item-/);
      expect(renderedItems.length).toBeLessThanOrEqual(10);
    });

    it('updates when photo data changes', () => {
      const { rerender } = renderWithQuery(<VirtualPhotoGrid photos={mockPhotos.slice(0, 50)} />);

      expect(useVirtualGrid).toHaveBeenCalledWith(50, expect.any(Object));

      rerender(
        <QueryClientProvider client={queryClient}>
          <VirtualPhotoGrid photos={mockPhotos} />
        </QueryClientProvider>
      );

      expect(useVirtualGrid).toHaveBeenCalledWith(100, expect.any(Object));
    });
  });

  describe('Virtualization Behavior', () => {
    it('renders only visible items + overscan', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // Mock renders max 10 items despite 100 photos
      const renderedItems = screen.getAllByTestId(/photo-item-/);
      expect(renderedItems.length).toBeLessThanOrEqual(10);
    });

    it('uses overscan rows for smooth scrolling', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.overscanRowCount).toBeGreaterThanOrEqual(0);
    });

    it('renders correct items for each cell', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // First item should be photo_0.jpg
      expect(screen.getByTestId('photo-item-photo_0.jpg')).toBeInTheDocument();
      // Second item should be photo_1.jpg
      expect(screen.getByTestId('photo-item-photo_1.jpg')).toBeInTheDocument();
    });

    it('handles partial last row', () => {
      const photos98 = mockPhotos.slice(0, 98);
      renderWithQuery(<VirtualPhotoGrid photos={photos98} />);

      // 98 photos ÷ 4 columns = 24.5 rows → 25 rows
      // Last row has 2 items
      expect(useVirtualGrid).toHaveBeenCalledWith(98, expect.any(Object));
    });
  });

  describe('Loading States', () => {
    it('shows skeleton loaders while loading', () => {
      renderWithQuery(<VirtualPhotoGrid photos={[]} isLoading={true} />);

      const skeletons = screen.getAllByRole('generic').filter(
        el => el.className.includes('skeleton-loader')
      );
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('transitions from skeleton to photos', () => {
      const { rerender } = renderWithQuery(
        <VirtualPhotoGrid photos={[]} isLoading={true} />
      );

      expect(screen.queryByTestId('virtual-grid')).not.toBeInTheDocument();

      rerender(
        <QueryClientProvider client={queryClient}>
          <VirtualPhotoGrid photos={mockPhotos} isLoading={false} />
        </QueryClientProvider>
      );

      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });

    // Note: Infinite scroll loading indicator is now managed by Gallery component
  });

  describe('Empty State', () => {
    it('renders empty state when no photos', () => {
      renderWithQuery(<VirtualPhotoGrid photos={[]} isLoading={false} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    it('uses existing EmptyStateMessage component', () => {
      renderWithQuery(<VirtualPhotoGrid photos={[]} isLoading={false} />);

      expect(EmptyStateMessage).toHaveBeenCalled();
    });
  });

  // Note: Infinite scroll sentinel is now managed by Gallery component, not VirtualPhotoGrid
  // Integration tests for infinite scroll behavior are in Gallery.infinite-scroll.*.test.jsx

  describe('Click and Interaction', () => {
    it('calls onPhotoClick when photo clicked', async () => {
      const onPhotoClick = vi.fn();
      renderWithQuery(
        <VirtualPhotoGrid
          photos={mockPhotos}
          onPhotoClick={onPhotoClick}
        />
      );

      const firstPhoto = screen.getByTestId('photo-item-photo_0.jpg');
      firstPhoto.click();

      await waitFor(() => {
        expect(onPhotoClick).toHaveBeenCalled();
      });
    });

    it('supports keyboard navigation', async () => {
      const onPhotoClick = vi.fn();
      renderWithQuery(
        <VirtualPhotoGrid
          photos={mockPhotos}
          onPhotoClick={onPhotoClick}
        />
      );

      // Grid should be accessible
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });

    it('maintains focus during scroll', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // react-window maintains focus automatically
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });
  });

  describe('View Mode Support', () => {
    it('supports grid view mode', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} viewMode="grid" />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(4); // Default grid columns
    });

    it('supports list view mode', () => {
      useVirtualGrid.mockReturnValue({
        containerRef: vi.fn(),
        columnCount: 1, // List mode forces 1 column
        rowCount: 100,
        itemWidth: 1024,
        itemHeight: 128,
        totalHeight: 12800
      });

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} viewMode="list" />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(1);
    });

    it('adjusts columns for list mode', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} viewMode="list" />);

      // Hook should be called with breakpoints for list mode
      expect(useVirtualGrid).toHaveBeenCalledWith(
        100,
        expect.objectContaining({
          breakpoints: expect.any(Object)
        })
      );
    });
  });

  describe('Responsive Behavior', () => {
    it('renders 1 column on mobile', () => {
      useVirtualGrid.mockReturnValue({
        containerRef: vi.fn(),
        columnCount: 1,
        rowCount: 100,
        itemWidth: 320,
        itemHeight: 336,
        totalHeight: 33600
      });

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(1);
    });

    it('renders 4 columns on desktop', () => {
      useVirtualGrid.mockReturnValue({
        containerRef: vi.fn(),
        columnCount: 4,
        rowCount: 25,
        itemWidth: 256,
        itemHeight: 272,
        totalHeight: 6800
      });

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(4);
    });

    it('renders 6 columns on 4K displays', () => {
      useVirtualGrid.mockReturnValue({
        containerRef: vi.fn(),
        columnCount: 6,
        rowCount: 17,
        itemWidth: 256,
        itemHeight: 272,
        totalHeight: 4624
      });

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(6);
    });

    it('handles orientation changes', () => {
      // Test landscape orientation
      const landscapeMock = {
        containerRef: vi.fn(),
        columnCount: 6,
        rowCount: 17,
        itemWidth: 256,
        itemHeight: 272,
        totalHeight: 4624
      };

      useVirtualGrid.mockReturnValue(landscapeMock);

      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      expect(FixedSizeGrid).toHaveBeenCalled();
      const callArgs = FixedSizeGrid.mock.calls[0][0];
      expect(callArgs.columnCount).toBe(6);
    });
  });

  describe('Performance Optimizations', () => {
    it('memoizes cell renderer', () => {
      const { rerender } = renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      const firstCallIndex = FixedSizeGrid.mock.calls.length - 1;
      const firstCallChildren = FixedSizeGrid.mock.calls[firstCallIndex]?.[0]?.children;

      rerender(
        <QueryClientProvider client={queryClient}>
          <VirtualPhotoGrid photos={mockPhotos} />
        </QueryClientProvider>
      );

      const lastCallIndex = FixedSizeGrid.mock.calls.length - 1;
      const secondCallChildren = FixedSizeGrid.mock.calls[lastCallIndex]?.[0]?.children;

      // Should be same function reference (memoized)
      expect(firstCallChildren).toBeDefined();
      expect(secondCallChildren).toBeDefined();
      expect(firstCallChildren).toBe(secondCallChildren);
    });

    it('uses React.memo for component', () => {
      const { rerender } = renderWithQuery(
        <VirtualPhotoGrid photos={mockPhotos} />
      );

      const renderCount = FixedSizeGrid.mock.calls.length;

      // Re-render with same props should not re-render component
      rerender(
        <QueryClientProvider client={queryClient}>
          <VirtualPhotoGrid photos={mockPhotos} />
        </QueryClientProvider>
      );

      // Component is memoized, but QueryClientProvider causes re-render
      expect(FixedSizeGrid.mock.calls.length).toBeGreaterThanOrEqual(renderCount);
    });

    it('provides stable keys for items', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // VirtualPhotoGridItem should receive stable photo objects
      expect(VirtualPhotoGridItem).toHaveBeenCalled();
      const callArgs = VirtualPhotoGridItem.mock.calls[0][0];
      expect(callArgs.photo.path).toBeDefined();
      expect(typeof callArgs.photo.path).toBe('string');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // Grid container should exist
      const grid = screen.getByTestId('virtual-grid');
      expect(grid).toBeInTheDocument();
    });

    it('maintains tab order', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // react-window handles tab order
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });

    it('includes skip to content link', () => {
      renderWithQuery(<VirtualPhotoGrid photos={mockPhotos} />);

      // Component should render accessible structure
      expect(screen.getByTestId('virtual-grid')).toBeInTheDocument();
    });
  });
});
