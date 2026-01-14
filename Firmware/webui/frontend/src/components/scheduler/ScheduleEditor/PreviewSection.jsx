import PropTypes from 'prop-types';
import { RoutinePropType } from './propTypes';
import { generateRoutineName, describeTrigger, getActionColor } from '../../../utils/routineUtils';

/**
 * Get human-readable action name
 */
const getActionDisplayName = (action) => {
  const name = action.action_name || action.name || 'Unknown';
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

/**
 * PreviewSection Component
 *
 * Displays a summary of all routines in the schedule, showing each routine's
 * trigger and actions.
 *
 * @component
 * @example
 * <PreviewSection routines={[{ trigger: {...}, actions: [...] }]} />
 */
const PreviewSection = ({ routines = [] }) => {
  const hasRoutines = routines && routines.length > 0;

  return (
    <div className="space-y-4" aria-label="Schedule preview">
      {/* Section Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Schedule Summary
      </h3>

      {/* No Routines Message */}
      {!hasRoutines && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-500 dark:text-gray-300 italic">
            No routines configured
          </p>
        </div>
      )}

      {/* Routine Summaries */}
      {hasRoutines && (
        <div className="space-y-3">
          {routines.map((routine, index) => {
            const routineName = generateRoutineName(routine);
            const triggerDesc = describeTrigger(routine.trigger);
            const actions = routine.actions || [];

            return (
              <div
                key={routine.routine_id || index}
                className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4"
              >
                {/* Routine Name */}
                <div className="flex items-center gap-2 mb-2">
                  {/* Action color dots */}
                  <div className="flex items-center gap-1">
                    {[...new Set(actions.map(a => getActionColor(a)))].map((colorClass, i) => (
                      <div
                        key={i}
                        className={`w-2 h-2 rounded-full ${colorClass}`}
                      />
                    ))}
                  </div>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {routineName}
                  </span>
                </div>

                {/* Trigger */}
                {triggerDesc && (
                  <p className="text-sm text-blue-600 dark:text-blue-400 mb-2">
                    {triggerDesc}
                  </p>
                )}

                {/* Actions List */}
                {actions.length > 0 && (
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    <span className="font-medium">Actions: </span>
                    {actions.map((action, i) => (
                      <span key={action.action_id || i}>
                        {getActionDisplayName(action)}
                        {i < actions.length - 1 && ' → '}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Summary Stats */}
      {hasRoutines && (
        <div className="text-sm text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
          {routines.length} routine{routines.length !== 1 ? 's' : ''} •{' '}
          {routines.reduce((sum, r) => sum + (r.actions?.length || 0), 0)} total actions
        </div>
      )}
    </div>
  );
};

PreviewSection.propTypes = {
  /** Array of routines with triggers and actions */
  routines: PropTypes.arrayOf(RoutinePropType),
};

export default PreviewSection;
