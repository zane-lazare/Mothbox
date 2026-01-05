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
export { default as EventPatternSelector } from './EventPatternSelector';
export { default as DateRangeSection } from './DateRangeSection';
export { default as PreviewSection } from './PreviewSection';

// Trigger form sub-components
export { default as IntervalTriggerForm } from './IntervalTriggerForm';
export { default as SolarTriggerForm } from './SolarTriggerForm';
export { default as MoonPhaseTriggerForm } from './MoonPhaseTriggerForm';
export { default as FixedTimeTriggerForm } from './FixedTimeTriggerForm';
export { default as SensorTriggerForm } from './SensorTriggerForm';

// Utility components
export { default as TimeWindowInput } from './TimeWindowInput';
export { default as DaysOfWeekSelector } from './DaysOfWeekSelector';

// Routine components (Issue #324)
export { default as TriggerLabel } from './TriggerLabel';
export { default as RoutineCard } from './RoutineCard';
export { default as RoutineList } from './RoutineList';
export { default as NewRoutineCard } from './NewRoutineCard';

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

// PropTypes (shared shapes)
export {
  TimeWindowPropType,
  TimeWindowErrorsPropType,
  TriggerErrorsPropType,
  TriggerPropType,
  ActionPropType,
  PatternPropType,
  DateRangePropType,
  PatternSelectionPropType,
  SchedulePropType,
} from './propTypes';
