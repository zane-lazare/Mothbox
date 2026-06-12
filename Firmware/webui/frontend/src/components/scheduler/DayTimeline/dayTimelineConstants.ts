/**
 * DayTimeline styling constants (Issue #326)
 *
 * Provides static Tailwind class mappings for JIT compatibility.
 * Dynamic class construction doesn't work with Tailwind's JIT compiler,
 * so we define all possible class combinations here.
 *
 * Imports from shared scheduler constants for single source of truth.
 *
 * @module components/scheduler/DayTimeline/dayTimelineConstants
 */

import type { ActionColorVariant } from '../constants'
import {
  ACTION_TYPE_COLORS as SHARED_ACTION_TYPE_COLORS,
  ACTION_TYPE_LABELS,
  DEFAULT_ACTION_COLORS as SHARED_DEFAULT_ACTION_COLORS,
  CONFLICT_COLORS,
  ROW_CONFLICT_STYLES,
  HDR_ACTION_NAMES,
  isHdrAction,
} from '../constants'

// Re-export shared constants for use by DayTimeline components
export { isHdrAction, HDR_ACTION_NAMES, ROW_CONFLICT_STYLES }

/**
 * Action type color mapping for execution chips.
 * Maps action types to their Tailwind background/text classes.
 * Re-exported from shared constants with DayTimeline-specific structure.
 */
export const ACTION_TYPE_COLORS: Record<string, Pick<ActionColorVariant, 'bg' | 'text'>> =
  Object.fromEntries(
    Object.entries(SHARED_ACTION_TYPE_COLORS).map(([key, val]) => [
      key,
      { bg: val.bg, text: val.text },
    ])
  )

/**
 * Default colors for unknown action types.
 */
export const DEFAULT_ACTION_COLORS = {
  bg: SHARED_DEFAULT_ACTION_COLORS.bg,
  text: SHARED_DEFAULT_ACTION_COLORS.text,
} as const

/**
 * Conflict ring styles for execution chips.
 */
export const CHIP_CONFLICT_RINGS = {
  error: CONFLICT_COLORS.error.ring,
  warning: CONFLICT_COLORS.warning.ring,
} as const

/**
 * Legend item type definition
 */
export interface LegendItem {
  color: string
  label: string
  isRing?: boolean
}

/**
 * Legend items for the timeline.
 * Generated from shared constants to include all action types.
 */
export const LEGEND_ITEMS: readonly LegendItem[] = [
  // Action type indicators (from shared constants)
  ...Object.entries(SHARED_ACTION_TYPE_COLORS).map(([type, colors]) => ({
    color: colors.solid,
    label: ACTION_TYPE_LABELS[type],
  })),
  // Conflict indicators
  { color: CONFLICT_COLORS.error.ring, label: 'Collision', isRing: true },
  { color: CONFLICT_COLORS.warning.ring, label: 'Warning', isRing: true },
] as const

/**
 * Type definitions for DayTimeline constants
 */
export type ChipConflictRings = typeof CHIP_CONFLICT_RINGS
export type DefaultActionColors = typeof DEFAULT_ACTION_COLORS
