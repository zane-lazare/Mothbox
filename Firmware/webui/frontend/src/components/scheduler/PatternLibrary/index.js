/**
 * Pattern Library Components (Issue #225)
 *
 * Components for browsing and selecting event patterns
 * for use in the schedule editor.
 *
 * @module components/scheduler/PatternLibrary
 *
 * @example
 * // Standalone mode - full browsing experience
 * import { PatternList } from './PatternLibrary'
 *
 * function SchedulerPage() {
 *   const handlePatternSelect = (pattern) => {
 *     console.log('Selected pattern:', pattern.name)
 *   }
 *
 *   return <PatternList onPatternSelect={handlePatternSelect} />
 * }
 *
 * @example
 * // Embedded mode - compact selection in schedule editor
 * import { PatternList } from './PatternLibrary'
 *
 * function ScheduleEditor({ selectedPatternId, onPatternSelect }) {
 *   return (
 *     <PatternList
 *       mode="embedded"
 *       selectedPatternId={selectedPatternId}
 *       onPatternSelect={onPatternSelect}
 *     />
 *   )
 * }
 */

export { default as PatternList } from './PatternList'
export { default as PatternCard } from './PatternCard'
export { default as PatternDetailsDrawer } from './PatternDetailsDrawer'
export { default as PatternFilters } from './PatternFilters'
