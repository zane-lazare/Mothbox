/**
 * TriggerLabel - Simple text label showing trigger type
 *
 * Per unified-scheduler-mockup.html, displays trigger type as gray text
 * instead of colored badge.
 *
 * @module components/scheduler/ScheduleEditor/TriggerLabel
 */

import { memo } from 'react'
// @ts-expect-error -- .js module
import { getTriggerLabel } from '@/utils/routineUtils'
import type { Trigger } from './scheduler-types'

interface TriggerLabelProps {
  trigger?: Trigger | null;
}

/**
 * TriggerLabel component
 *
 * @param {Object} props - Component props
 * @param {Object} props.trigger - Trigger configuration object
 * @returns {JSX.Element|null} Label element or null if no trigger
 *
 * @example
 * <TriggerLabel trigger={{ trigger_type: 'solar' }} />
 * // Renders: <span className="...">Solar</span>
 */
function TriggerLabel({ trigger }: TriggerLabelProps) {
  const label = getTriggerLabel(trigger)

  if (!label) {
    return null
  }

  return (
    <span
      className="text-xs text-gray-600 dark:text-gray-500"
      data-testid="trigger-badge"
    >
      {label}
    </span>
  )
}

export default memo(TriggerLabel)
