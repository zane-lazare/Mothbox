/**
 * Type declarations for TimeWindowInput.jsx
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with TimeWindowInput.jsx.
 */

import { ComponentType } from 'react'

interface TimeWindowValue {
  start_time: string
  end_time: string
  start_offset_minutes?: number
  end_offset_minutes?: number
}

interface TimeWindowInputProps {
  value?: TimeWindowValue
  onChange: (value: TimeWindowValue) => void
  disabled?: boolean
  showSolarEvents?: boolean
  errors?: Record<string, string>
}

declare const TimeWindowInput: ComponentType<TimeWindowInputProps>
export default TimeWindowInput
