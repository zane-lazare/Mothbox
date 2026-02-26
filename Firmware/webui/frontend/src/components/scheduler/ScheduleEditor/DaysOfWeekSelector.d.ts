/**
 * Type declarations for DaysOfWeekSelector.jsx
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with DaysOfWeekSelector.jsx.
 */

import { ComponentType } from 'react'

interface DaysOfWeekSelectorProps {
  value: number[] | null
  onChange: (value: number[] | null) => void
  disabled?: boolean
  compact?: boolean
}

declare const DaysOfWeekSelector: ComponentType<DaysOfWeekSelectorProps>
export default DaysOfWeekSelector
