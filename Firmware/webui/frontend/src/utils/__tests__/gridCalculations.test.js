/**
 * Tests for grid calculation utilities
 * Tests MUST be written FIRST (TDD approach)
 */

import { describe, it, expect } from 'vitest';
import {
  calculateColumnCount,
  calculateRowCount,
  calculateItemDimensions,
  calculateGridDimensions,
  DEFAULT_BREAKPOINTS,
  DEFAULT_GAP,
  DEFAULT_ASPECT_RATIO,
} from '../gridCalculations';

describe('gridCalculations', () => {
  describe('calculateColumnCount', () => {
    it('returns 1 column for mobile (320px)', () => {
      const result = calculateColumnCount(320);
      expect(result).toBe(1);
    });

    it('returns 2 columns for small mobile (640px)', () => {
      const result = calculateColumnCount(640);
      expect(result).toBe(2);
    });

    it('returns 3 columns for tablet (768px)', () => {
      const result = calculateColumnCount(768);
      expect(result).toBe(3);
    });

    it('returns 4 columns for desktop (1024px)', () => {
      const result = calculateColumnCount(1024);
      expect(result).toBe(4);
    });

    it('returns 5 columns for large desktop (1280px)', () => {
      const result = calculateColumnCount(1280);
      expect(result).toBe(5);
    });

    it('returns 6 columns for extra large desktop (1920px)', () => {
      const result = calculateColumnCount(1920);
      expect(result).toBe(6);
    });

    it('handles edge case: zero width', () => {
      const result = calculateColumnCount(0);
      expect(result).toBe(1); // Minimum 1 column
    });

    it('handles edge case: negative width', () => {
      const result = calculateColumnCount(-100);
      expect(result).toBe(1); // Minimum 1 column
    });

    it('respects custom column configuration', () => {
      const customBreakpoints = {
        sm: 500,
        md: 800,
        lg: 1200,
        xl: 1600,
        '2xl': 2000,
      };

      expect(calculateColumnCount(400, customBreakpoints)).toBe(1);
      expect(calculateColumnCount(500, customBreakpoints)).toBe(2);
      expect(calculateColumnCount(800, customBreakpoints)).toBe(3);
      expect(calculateColumnCount(1200, customBreakpoints)).toBe(4);
      expect(calculateColumnCount(1600, customBreakpoints)).toBe(5);
      expect(calculateColumnCount(2000, customBreakpoints)).toBe(6);
    });

    it('handles widths at exact breakpoint boundaries', () => {
      expect(calculateColumnCount(639)).toBe(1);
      expect(calculateColumnCount(640)).toBe(2);
      expect(calculateColumnCount(767)).toBe(2);
      expect(calculateColumnCount(768)).toBe(3);
    });

    it('never exceeds 6 columns for very large widths', () => {
      const result = calculateColumnCount(10000);
      expect(result).toBe(6);
    });
  });

  describe('calculateRowCount', () => {
    it('calculates correct rows for exact division', () => {
      // 12 photos, 3 columns = 4 rows
      const result = calculateRowCount(12, 3);
      expect(result).toBe(4);
    });

    it('calculates correct rows with remainder', () => {
      // 10 photos, 3 columns = 4 rows (ceil)
      const result = calculateRowCount(10, 3);
      expect(result).toBe(4);
    });

    it('returns 0 for empty gallery', () => {
      const result = calculateRowCount(0, 3);
      expect(result).toBe(0);
    });

    it('returns 1 for single photo', () => {
      const result = calculateRowCount(1, 4);
      expect(result).toBe(1);
    });

    it('handles large photo count', () => {
      // 10000 photos, 4 columns = 2500 rows
      const result = calculateRowCount(10000, 4);
      expect(result).toBe(2500);
    });

    it('handles single column layout', () => {
      const result = calculateRowCount(5, 1);
      expect(result).toBe(5);
    });

    it('calculates correctly for two columns', () => {
      expect(calculateRowCount(5, 2)).toBe(3); // 3 rows for 5 photos
      expect(calculateRowCount(6, 2)).toBe(3); // 3 rows for 6 photos
      expect(calculateRowCount(7, 2)).toBe(4); // 4 rows for 7 photos
    });

    it('handles edge case: zero photos', () => {
      expect(calculateRowCount(0, 1)).toBe(0);
      expect(calculateRowCount(0, 4)).toBe(0);
    });

    it('handles edge case: many columns, few photos', () => {
      // 3 photos, 6 columns = 1 row
      const result = calculateRowCount(3, 6);
      expect(result).toBe(1);
    });
  });

  describe('calculateItemDimensions', () => {
    it('calculates correct width with gap', () => {
      // containerWidth: 1000px, columns: 4, gap: 16px
      // Expected: (1000 - 3*16) / 4 = (1000 - 48) / 4 = 238px per item
      const result = calculateItemDimensions(1000, 4, 16);
      expect(result.width).toBe(238);
    });

    it('handles single column layout', () => {
      // Full width, no gaps
      const result = calculateItemDimensions(1000, 1, 16);
      expect(result.width).toBe(1000);
    });

    it('calculates height based on default aspect ratio (4:3)', () => {
      const result = calculateItemDimensions(1000, 4, 16);
      // width = 238px, height = 238 / (4/3) = 238 * 0.75 = 178.5px
      expect(result.height).toBeCloseTo(178.5, 1);
    });

    it('supports custom aspect ratio (16:9)', () => {
      const result = calculateItemDimensions(1000, 4, 16, 16 / 9);
      // width = 238px, height = 238 / (16/9) = 238 * 0.5625 = 133.875px
      expect(result.height).toBeCloseTo(133.875, 1);
    });

    it('supports custom aspect ratio (1:1 square)', () => {
      const result = calculateItemDimensions(1000, 4, 16, 1);
      // width = height for square
      expect(result.width).toBe(238);
      expect(result.height).toBe(238);
    });

    it('uses default gap when not specified', () => {
      const result = calculateItemDimensions(1000, 4);
      // Should use DEFAULT_GAP (16px)
      expect(result.width).toBe(238);
    });

    it('uses default aspect ratio when not specified', () => {
      const result = calculateItemDimensions(1000, 4, 16);
      // Should use DEFAULT_ASPECT_RATIO (4/3)
      expect(result.height).toBeCloseTo(178.5, 1);
    });

    it('handles two column layout correctly', () => {
      // 1000px, 2 columns, 16px gap = (1000 - 16) / 2 = 492px per item
      const result = calculateItemDimensions(1000, 2, 16);
      expect(result.width).toBe(492);
    });

    it('handles zero gap', () => {
      // 1000px, 4 columns, 0px gap = 250px per item
      const result = calculateItemDimensions(1000, 4, 0);
      expect(result.width).toBe(250);
    });

    it('returns positive dimensions for edge cases', () => {
      const result = calculateItemDimensions(100, 1, 0);
      expect(result.width).toBeGreaterThan(0);
      expect(result.height).toBeGreaterThan(0);
    });
  });

  describe('calculateGridDimensions', () => {
    it('combines all calculations for complete grid layout', () => {
      const result = calculateGridDimensions(1024, 100);

      // Should return object with all required properties
      expect(result).toHaveProperty('columnCount');
      expect(result).toHaveProperty('rowCount');
      expect(result).toHaveProperty('itemWidth');
      expect(result).toHaveProperty('itemHeight');
      expect(result).toHaveProperty('totalHeight');

      // Validate types
      expect(typeof result.columnCount).toBe('number');
      expect(typeof result.rowCount).toBe('number');
      expect(typeof result.itemWidth).toBe('number');
      expect(typeof result.itemHeight).toBe('number');
      expect(typeof result.totalHeight).toBe('number');
    });

    it('calculates correct values for desktop (1024px)', () => {
      const result = calculateGridDimensions(1024, 100);

      // 1024px = 4 columns
      expect(result.columnCount).toBe(4);

      // 100 photos / 4 columns = 25 rows
      expect(result.rowCount).toBe(25);

      // itemWidth = (1024 - 3*16) / 4 = 244px
      expect(result.itemWidth).toBe(244);

      // itemHeight = 244 / (4/3) = 183px
      expect(result.itemHeight).toBeCloseTo(183, 0);

      // totalHeight = rowCount * (itemHeight + gap) - gap
      // = 25 * (183 + 16) - 16 = 25 * 199 - 16 = 4975 - 16 = 4959px
      const expectedHeight = result.rowCount * (result.itemHeight + DEFAULT_GAP) - DEFAULT_GAP;
      expect(result.totalHeight).toBeCloseTo(expectedHeight, 0);
    });

    it('handles responsive breakpoints (mobile)', () => {
      const result = calculateGridDimensions(320, 50);

      // 320px = 1 column
      expect(result.columnCount).toBe(1);

      // 50 photos / 1 column = 50 rows
      expect(result.rowCount).toBe(50);
    });

    it('handles responsive breakpoints (tablet)', () => {
      const result = calculateGridDimensions(768, 90);

      // 768px = 3 columns
      expect(result.columnCount).toBe(3);

      // 90 photos / 3 columns = 30 rows
      expect(result.rowCount).toBe(30);
    });

    it('handles responsive breakpoints (large desktop)', () => {
      const result = calculateGridDimensions(1920, 120);

      // 1920px = 6 columns
      expect(result.columnCount).toBe(6);

      // 120 photos / 6 columns = 20 rows
      expect(result.rowCount).toBe(20);
    });

    it('handles empty gallery', () => {
      const result = calculateGridDimensions(1024, 0);

      expect(result.columnCount).toBeGreaterThan(0);
      expect(result.rowCount).toBe(0);
      expect(result.totalHeight).toBe(0);
    });

    it('handles single photo', () => {
      const result = calculateGridDimensions(1024, 1);

      expect(result.rowCount).toBe(1);
    });

    it('respects custom gap option', () => {
      const result = calculateGridDimensions(1024, 100, { gap: 24 });

      // 1024px = 4 columns
      // itemWidth = (1024 - 3*24) / 4 = (1024 - 72) / 4 = 238px
      expect(result.itemWidth).toBe(238);
    });

    it('respects custom aspect ratio option', () => {
      const result = calculateGridDimensions(1000, 100, { aspectRatio: 16 / 9 });

      // itemHeight should use 16:9 ratio
      expect(result.itemHeight).toBeCloseTo(result.itemWidth / (16 / 9), 1);
    });

    it('respects custom breakpoints option', () => {
      const customBreakpoints = {
        sm: 500,
        md: 800,
        lg: 1200,
        xl: 1600,
        '2xl': 2000,
      };

      const result = calculateGridDimensions(600, 100, { breakpoints: customBreakpoints });

      // 600px with custom breakpoints = 2 columns
      expect(result.columnCount).toBe(2);
    });

    it('calculates total height correctly with gaps', () => {
      const result = calculateGridDimensions(1024, 8, { gap: 16 });

      // 8 photos, 4 columns = 2 rows
      expect(result.rowCount).toBe(2);

      // Total height = (rowHeight * rowCount) + (gap * (rowCount - 1))
      // = (itemHeight * 2) + (16 * 1) = itemHeight * 2 + 16
      const expectedHeight = (result.itemHeight * result.rowCount) + (16 * (result.rowCount - 1));
      expect(result.totalHeight).toBeCloseTo(expectedHeight, 0);
    });

    it('handles very large photo count', () => {
      const result = calculateGridDimensions(1920, 10000);

      expect(result.columnCount).toBe(6);
      expect(result.rowCount).toBe(Math.ceil(10000 / 6));
      expect(result.totalHeight).toBeGreaterThan(0);
    });
  });
});
