/**
 * Schedule Editor Components (Issue #227)
 *
 * Main export for the Schedule Editor module. Provides components for
 * creating and editing schedules with triggers, event patterns, and
 * date constraints.
 *
 * @module components/scheduler/ScheduleEditor
 *
 * @example
 * // Main drawer component
 * import { ScheduleEditor } from './ScheduleEditor'
 *
 * function SchedulerPage() {
 *   const [isOpen, setIsOpen] = useState(false)
 *
 *   return (
 *     <ScheduleEditor
 *       isOpen={isOpen}
 *       onSave={(schedule) => console.log('Save:', schedule)}
 *       onCancel={() => setIsOpen(false)}
 *     />
 *   )
 * }
 *
 * @example
 * // Using individual components
 * import { TriggerForm, EventPatternSelector } from './ScheduleEditor'
 *
 * function CustomForm() {
 *   const [trigger, setTrigger] = useState({...})
 *   return <TriggerForm value={trigger} onChange={setTrigger} />
 * }
 */

// Main drawer component
export { default as ScheduleEditor } from './ScheduleEditor';

// Section components
export { default as TriggerForm } from './TriggerForm';

// Trigger form sub-components
export { default as IntervalTriggerForm } from './IntervalTriggerForm';
export { default as SolarTriggerForm } from './SolarTriggerForm';
export { default as MoonPhaseTriggerForm } from './MoonPhaseTriggerForm';
export { default as FixedTimeTriggerForm } from './FixedTimeTriggerForm';
export { default as SensorTriggerForm } from './SensorTriggerForm';

// Utility components
export { default as TimeWindowInput } from './TimeWindowInput';
export { default as DaysOfWeekSelector } from './DaysOfWeekSelector';

// Routine components (Issue #324, #325)
export { default as TriggerLabel } from './TriggerLabel';
export { default as RoutineCard } from './RoutineCard';
export { default as RoutineList } from './RoutineList';
export { default as NewRoutineCard } from './NewRoutineCard';
export { default as PreConditionForm } from './PreConditionForm';

// Conflict detection (Issue #331)
export { default as ConflictPanel } from './ConflictPanel';

// Constants and types
export {
  SCHEDULE_LIMITS,
  TRIGGER_TYPES,
  SOLAR_EVENTS,
  MOON_PHASES,
  DAYS_OF_WEEK,
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
  TRIGGER_DEFAULTS,
  TIME_FORMAT_REGEX,
} from './constants';

// Type exports
export type { ScheduleSaveData } from './ScheduleEditor';
export type { IntervalTriggerValue } from './IntervalTriggerForm';
export type { SolarTriggerValue } from './SolarTriggerForm';
export type { MoonPhaseTriggerValue } from './MoonPhaseTriggerForm';
export type { FixedTimeTriggerValue } from './FixedTimeTriggerForm';
export type { SensorTriggerValue } from './SensorTriggerForm';
export type { RecurringDaysTriggerValue } from './RecurringDaysTriggerForm';
export type { TimeWindowValue } from './TimeWindowInput';
export type { PreConditionValue } from './PreConditionForm';
export type { SolarEventValue, MoonPhaseValue } from './constants';

// Shared TypeScript types from scheduler-types.ts
export type {
  TimeWindow,
  TimeWindowErrors,
  TriggerType,
  BaseTrigger,
  IntervalTrigger,
  SolarTrigger,
  MoonPhaseTrigger,
  FixedTimeTrigger,
  SensorTrigger,
  CronTrigger,
  RecurringDaysTrigger,
  Trigger,
  TriggerErrors,
  RoutineAction,
  PreCondition,
  Routine,
  Schedule,
  ConflictReport,
} from './scheduler-types';
