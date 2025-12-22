import PropTypes from 'prop-types';

/**
 * PreviewSection Component
 *
 * Displays a preview of when a schedule will execute based on the trigger,
 * pattern, and date range configuration.
 *
 * @component
 * @example
 * <PreviewSection
 *   trigger={{
 *     type: 'interval',
 *     interval_minutes: 60,
 *     time_window: { start_time: '21:00', end_time: '05:00' }
 *   }}
 *   dateRange={{ start_date: '2024-06-01', end_date: '2024-08-31' }}
 *   pattern={{ name: 'Night Photography', actions: [...] }}
 * />
 */
const PreviewSection = ({
  trigger,
  dateRange,
  pattern,
  // disabled prop reserved for future use (e.g., dimming preview during save)
  // eslint-disable-next-line no-unused-vars
  disabled = false,
}) => {
  /**
   * Format action count
   */
  const getActionCountText = (actions) => {
    const count = actions?.length || 0;
    return count === 1 ? '1 action' : `${count} actions`;
  };

  /**
   * Calculate total pattern duration from wait actions
   * @returns {number} Total seconds
   */
  const calculatePatternDuration = () => {
    if (!pattern?.actions) return 0;

    return pattern.actions.reduce((total, action) => {
      if (action.type === 'wait' && action.parameters?.duration_seconds) {
        return total + action.parameters.duration_seconds;
      }
      return total;
    }, 0);
  };

  /**
   * Format duration in seconds to human-readable string
   * @param {number} seconds
   * @returns {string}
   */
  const formatDuration = (seconds) => {
    if (seconds === 0) return 'instant';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0 && minutes > 0) {
      return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} minute${minutes !== 1 ? 's' : ''}`;
    } else if (hours > 0) {
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    } else {
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
  };

  /**
   * Format interval for display
   */
  const formatInterval = (minutes) => {
    if (minutes < 60) {
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    } else if (minutes % 60 === 0) {
      const hours = minutes / 60;
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    } else {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    }
  };

  /**
   * Get trigger summary text
   */
  const getTriggerSummary = () => {
    if (!trigger) return null;

    switch (trigger.type) {
      case 'interval':
        return `Every ${formatInterval(trigger.interval_minutes)} from ${trigger.time_window?.start_time || ''} to ${trigger.time_window?.end_time || ''}`;

      case 'solar': {
        const event = trigger.solar_event?.replace(/_/g, ' ') || 'solar event';
        if (trigger.offset_minutes > 0) {
          return `${trigger.offset_minutes} minutes after ${event}`;
        } else if (trigger.offset_minutes < 0) {
          return `${Math.abs(trigger.offset_minutes)} minutes before ${event}`;
        } else {
          return `At ${event}`;
        }
      }

      case 'fixed_time':
        if (trigger.days_of_week && trigger.days_of_week.length < 7) {
          const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
          const days = trigger.days_of_week.map(d => dayNames[d]).join(', ');
          return `At ${trigger.time} on ${days}`;
        }
        return `Daily at ${trigger.time}`;

      case 'moon_phase': {
        const phase = trigger.phase?.replace(/_/g, ' ') || 'moon phase';
        return `At ${trigger.time || 'sunset'} on ${phase}`;
      }

      case 'sensor':
        return 'Preview not available for sensor triggers';

      default:
        return 'Unknown trigger type';
    }
  };

  /**
   * Generate mock preview execution times
   * In a real implementation, this would call a backend API
   */
  const getMockExecutionTimes = () => {
    if (!trigger || !pattern) return [];

    // Mock data - would be replaced with actual API call
    const baseDate = dateRange?.start_date
      ? new Date(dateRange.start_date)
      : new Date();

    const times = [];
    for (let i = 0; i < 5; i++) {
      const date = new Date(baseDate);
      date.setDate(date.getDate() + i);
      date.setHours(21, 0, 0, 0); // Default to 9 PM
      times.push(date);
    }

    return times;
  };

  /**
   * Format date for display
   */
  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  /**
   * Format execution time for display
   */
  const formatExecutionTime = (date) => {
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const executionTimes = getMockExecutionTimes();
  const triggerSummary = getTriggerSummary();
  const patternDuration = pattern ? calculatePatternDuration() : 0;

  return (
    <div className="space-y-4" aria-label="Schedule preview">
      {/* Section Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Schedule Preview
      </h3>

      {/* No Trigger Message */}
      {!trigger && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
            No trigger configured
          </p>
        </div>
      )}

      {/* No Pattern Message */}
      {!pattern && trigger && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
            No pattern selected
          </p>
        </div>
      )}

      {/* Pattern Information */}
      {pattern && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
          <div>
            <p className="font-medium text-gray-900 dark:text-white">
              {pattern.name}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {getActionCountText(pattern.actions)}
            </p>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium">Duration:</span>{' '}
            {formatDuration(patternDuration)}
          </div>
        </div>
      )}

      {/* Trigger Summary */}
      {trigger && pattern && triggerSummary && (
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <p className="text-sm text-blue-900 dark:text-blue-200">
            {triggerSummary}
          </p>
        </div>
      )}

      {/* Date Constraints */}
      {dateRange && (dateRange.start_date || dateRange.end_date) && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          <p className="font-medium mb-1">Active Period:</p>
          <p>
            {dateRange.start_date ? formatDate(dateRange.start_date) : 'No start date'} →{' '}
            {dateRange.end_date ? formatDate(dateRange.end_date) : 'No end date'}
          </p>
        </div>
      )}

      {/* Execution Preview */}
      {trigger && pattern && trigger.type !== 'sensor' && (
        <div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Next Executions:
          </p>
          <ul
            className="space-y-2"
            role="list"
            aria-label="Next execution times"
          >
            {executionTimes.map((time, index) => (
              <li
                key={index}
                className="text-sm text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-700 rounded px-3 py-2"
              >
                {formatExecutionTime(time)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

PreviewSection.propTypes = {
  trigger: PropTypes.shape({
    type: PropTypes.oneOf(['interval', 'solar', 'moon_phase', 'fixed_time', 'sensor']),
    // Interval trigger
    interval_minutes: PropTypes.number,
    time_window: PropTypes.shape({
      start_time: PropTypes.string,
      end_time: PropTypes.string,
      start_offset_minutes: PropTypes.number,
      end_offset_minutes: PropTypes.number,
    }),
    // Solar trigger
    solar_event: PropTypes.string,
    offset_minutes: PropTypes.number,
    // Fixed time trigger
    time: PropTypes.string,
    // Moon phase trigger
    phase: PropTypes.string,
    offset_days: PropTypes.number,
    // Common
    days_of_week: PropTypes.arrayOf(PropTypes.number),
    // Sensor trigger
    sensor_type: PropTypes.string,
    threshold: PropTypes.number,
  }),
  dateRange: PropTypes.shape({
    start_date: PropTypes.string,
    end_date: PropTypes.string,
  }),
  pattern: PropTypes.shape({
    pattern_id: PropTypes.string,
    name: PropTypes.string,
    description: PropTypes.string,
    actions: PropTypes.arrayOf(
      PropTypes.shape({
        action_id: PropTypes.string,
        type: PropTypes.string,
        parameters: PropTypes.object,
      })
    ),
    category: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string),
  }),
  disabled: PropTypes.bool,
};

export default PreviewSection;
