/**
 * Cycle-based grouping utilities for scheduler views.
 *
 * Used by Week and Day views in pattern mode to group executions
 * by cycle day (0-6) rather than calendar date.
 *
 * @module components/scheduler/utils/cycleGroupingUtils
 */

/**
 * Execution item (extended from ScheduleExecution with additional fields)
 */
export interface ExecutionItem {
  start_time: string
  pattern_id: string
  event_name?: string
  action?: string
  scheduled_time?: string
  trigger_info?: Record<string, unknown>
}

/**
 * Cycle information from preview API
 */
export interface CycleInfo {
  start_hour: number
  end_hour?: number
}

/**
 * Execution grouped by hour
 */
export interface ExecutionsByHour {
  [hour: number]: ExecutionItem[]
}

/**
 * Cycle group structure (day-0 through day-6)
 */
export interface CycleGroup {
  [dayKey: `day-${number}`]: ExecutionsByHour
}

/**
 * Calculates the first cycle start time from a reference date.
 *
 * @param referenceDate - First date of the display period
 * @param startHour - Hour when each cycle starts (0-23)
 * @returns When the first cycle begins
 */
export function getFirstCycleStart(referenceDate: Date, startHour: number): Date {
  const firstCycleStart = new Date(referenceDate)
  firstCycleStart.setHours(startHour, 0, 0, 0)

  // If reference time is before start_hour, first cycle started yesterday
  if (referenceDate.getHours() < startHour) {
    firstCycleStart.setDate(firstCycleStart.getDate() - 1)
  }

  return firstCycleStart
}

/**
 * Determines which cycle day (0-6) an execution belongs to.
 *
 * A "cycle" starts at startHour each day. For overnight schedules,
 * post-midnight hours belong to the previous day's cycle.
 *
 * @param execTime - Execution timestamp
 * @param firstCycleStart - When the first cycle begins
 * @param startHour - Hour when each cycle starts (0-23)
 * @returns Cycle day (0-6), or -1 if outside range
 */
export function getCycleDay(execTime: Date, firstCycleStart: Date, startHour: number): number {
  const CYCLE_MS = 24 * 60 * 60 * 1000
  const hour = execTime.getHours()

  // Determine which cycle this execution belongs to
  const execCycleStart = new Date(execTime)
  execCycleStart.setHours(startHour, 0, 0, 0)

  // If execution hour is before start_hour, it belongs to previous day's cycle
  if (hour < startHour) {
    execCycleStart.setDate(execCycleStart.getDate() - 1)
  }

  const cycleDay = Math.floor(
    (execCycleStart.getTime() - firstCycleStart.getTime()) / CYCLE_MS
  )

  return (cycleDay >= 0 && cycleDay <= 6) ? cycleDay : -1
}

/**
 * Groups executions by cycle day (0-6) and hour for pattern mode.
 *
 * @param executions - Execution objects with start_time
 * @param cycleInfo - { start_hour } from preview API
 * @param referenceDate - First date of the week
 * @returns { 'day-0': { hour: [execs] }, ... 'day-6': { hour: [execs] } }
 */
export function groupExecutionsByCycleDay(
  executions: ExecutionItem[] | null | undefined,
  cycleInfo: CycleInfo | null | undefined,
  referenceDate: Date
): CycleGroup {
  if (!executions?.length) return {}

  const startHour = cycleInfo?.start_hour ?? 0
  const firstCycleStart = getFirstCycleStart(referenceDate, startHour)

  // Initialize structure for 7 cycle days
  const grouped: CycleGroup = {}
  for (let d = 0; d < 7; d++) {
    grouped[`day-${d}`] = {}
  }

  const seen = new Set<string>()

  for (const exec of executions) {
    if (!exec.start_time) continue

    const execTime = new Date(exec.start_time)
    if (isNaN(execTime.getTime())) continue

    const hour = execTime.getHours()
    const cycleDay = getCycleDay(execTime, firstCycleStart, startHour)

    if (cycleDay < 0) continue

    // Deduplicate
    const key = `day-${cycleDay}-${hour}-${exec.pattern_id}-${execTime.toTimeString().slice(0, 5)}`
    if (seen.has(key)) continue
    seen.add(key)

    const dayKey = `day-${cycleDay}` as `day-${number}`
    if (!grouped[dayKey][hour]) {
      grouped[dayKey][hour] = []
    }
    grouped[dayKey][hour].push(exec)
  }

  return grouped
}
