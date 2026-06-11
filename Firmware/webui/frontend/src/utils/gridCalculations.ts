/**
 * Grid calculation utilities for virtual photo gallery
 * Follows responsive breakpoints from Tailwind CSS
 *
 * @module utils/gridCalculations
 */

/**
 * Responsive breakpoint configuration
 */
interface Breakpoints {
  sm: number
  md: number
  lg: number
  xl: number
  '2xl': number
}

/**
 * Grid dimension calculation options
 */
interface GridOptions {
  gap?: number
  aspectRatio?: number
  breakpoints?: Breakpoints
}

/**
 * Item dimensions result
 */
interface ItemDimensions {
  width: number
  height: number
}

/**
 * Complete grid dimensions result
 */
interface GridDimensions {
  columnCount: number
  rowCount: number
  itemWidth: number
  itemHeight: number
  totalHeight: number
}

/**
 * Default responsive breakpoints (matches Tailwind CSS)
 * Maps container width to column count
 */
export const DEFAULT_BREAKPOINTS: Breakpoints = {
  sm: 640,   // 2 columns
  md: 768,   // 3 columns
  lg: 1024,  // 4 columns
  xl: 1280,  // 5 columns
  '2xl': 1920, // 6 columns
}

/**
 * Default gap between grid items in pixels
 */
export const DEFAULT_GAP = 16 // px

/**
 * Default aspect ratio for photo items
 * Mothbox camera: 9152x6944 pixels = 1.318:1 (slightly wider than 4:3)
 */
export const DEFAULT_ASPECT_RATIO = 9152 / 6944 // width / height

/**
 * Calculate number of columns based on container width
 *
 * @param {number} containerWidth - Width of grid container in pixels
 * @param {Object} breakpoints - Optional custom breakpoints
 * @returns {number} Number of columns (1-6)
 *
 * @example
 * calculateColumnCount(320)  // Returns 1 (mobile)
 * calculateColumnCount(1024) // Returns 4 (desktop)
 * calculateColumnCount(1920) // Returns 6 (large desktop)
 */
export function calculateColumnCount(containerWidth: number, breakpoints: Breakpoints = DEFAULT_BREAKPOINTS): number {
  // Handle edge cases
  if (!containerWidth || containerWidth <= 0) {
    return 1 // Minimum 1 column
  }

  // Determine column count based on breakpoints
  if (containerWidth < breakpoints.sm) {
    return 1 // Mobile portrait
  } else if (containerWidth < breakpoints.md) {
    return 2 // Small mobile/landscape
  } else if (containerWidth < breakpoints.lg) {
    return 3 // Tablet
  } else if (containerWidth < breakpoints.xl) {
    return 4 // Desktop
  } else if (containerWidth < breakpoints['2xl']) {
    return 5 // Large desktop
  } else {
    return 6 // Extra large desktop (max)
  }
}

/**
 * Calculate number of rows needed for photo count
 *
 * @param {number} photoCount - Total number of photos
 * @param {number} columnCount - Number of columns in grid
 * @returns {number} Number of rows (ceil)
 *
 * @example
 * calculateRowCount(12, 3) // Returns 4 (exact division)
 * calculateRowCount(10, 3) // Returns 4 (rounded up)
 * calculateRowCount(0, 3)  // Returns 0 (empty)
 */
export function calculateRowCount(photoCount: number, columnCount: number): number {
  if (photoCount <= 0) {
    return 0
  }

  if (columnCount <= 0) {
    return photoCount // Fallback: each photo gets its own row
  }

  return Math.ceil(photoCount / columnCount)
}

/**
 * Calculate dimensions for individual grid items
 *
 * @param {number} containerWidth - Width of grid container
 * @param {number} columnCount - Number of columns
 * @param {number} gap - Gap between items in pixels
 * @param {number} aspectRatio - Width/height ratio
 * @returns {Object} { width, height }
 *
 * @example
 * calculateItemDimensions(1000, 4, 16, 4/3)
 * // Returns { width: 238, height: 178.5 }
 */
export function calculateItemDimensions(
  containerWidth: number,
  columnCount: number,
  gap: number = DEFAULT_GAP,
  aspectRatio: number = DEFAULT_ASPECT_RATIO
): ItemDimensions {
  // Calculate total gap space: (n-1) gaps between n columns
  const totalGapWidth = (columnCount - 1) * gap

  // Calculate item width: available space divided by column count
  const itemWidth = (containerWidth - totalGapWidth) / columnCount

  // Calculate item height based on aspect ratio
  const itemHeight = itemWidth / aspectRatio

  return {
    width: itemWidth,
    height: itemHeight,
  }
}

/**
 * Calculate complete grid dimensions
 *
 * @param {number} containerWidth - Width of grid container
 * @param {number} photoCount - Total number of photos
 * @param {Object} options - Optional configuration
 * @param {number} options.gap - Gap between items (default: 16px)
 * @param {number} options.aspectRatio - Width/height ratio (default: 4/3)
 * @param {Object} options.breakpoints - Custom breakpoints (default: Tailwind)
 * @returns {Object} Complete grid layout
 *
 * @example
 * calculateGridDimensions(1024, 100)
 * // Returns {
 * //   columnCount: 4,
 * //   rowCount: 25,
 * //   itemWidth: 244,
 * //   itemHeight: 183,
 * //   totalHeight: 4959
 * // }
 */
export function calculateGridDimensions(
  containerWidth: number,
  photoCount: number,
  options: GridOptions = {}
): GridDimensions {
  const {
    gap = DEFAULT_GAP,
    aspectRatio = DEFAULT_ASPECT_RATIO,
    breakpoints = DEFAULT_BREAKPOINTS,
  } = options

  // Calculate column count based on container width
  const columnCount = calculateColumnCount(containerWidth, breakpoints)

  // Calculate row count based on photo count and columns
  const rowCount = calculateRowCount(photoCount, columnCount)

  // Calculate item dimensions
  const { width: itemWidth, height: itemHeight } = calculateItemDimensions(
    containerWidth,
    columnCount,
    gap,
    aspectRatio
  )

  // Calculate total grid height
  // Formula: (itemHeight * rowCount) + (gap * (rowCount - 1))
  // This accounts for gaps between rows but not after the last row
  let totalHeight = 0
  if (rowCount > 0) {
    totalHeight = (itemHeight * rowCount) + (gap * (rowCount - 1))
  }

  return {
    columnCount,
    rowCount,
    itemWidth,
    itemHeight,
    totalHeight,
  }
}
