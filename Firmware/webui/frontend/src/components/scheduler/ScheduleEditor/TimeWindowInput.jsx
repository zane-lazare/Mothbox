import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { SOLAR_EVENTS, TIME_FORMAT_REGEX, isValidSolarEvent } from './constants';

/**
 * TimeWindowInput Component
 *
 * A reusable component for configuring time windows with support for:
 * - Fixed time (HH:MM format)
 * - Solar events with offset adjustments (-120 to +120 minutes)
 *
 * Used by interval, moon phase, and sensor triggers.
 *
 * @component
 * @example
 * <TimeWindowInput
 *   value={{
 *     start_time: "21:00",
 *     end_time: "05:00"
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 *   showSolarEvents={true}
 * />
 */
const TimeWindowInput = ({
  value = {
    start_time: '',
    end_time: '',
    start_offset_minutes: 0,
    end_offset_minutes: 0,
  },
  onChange,
  disabled = false,
  showSolarEvents = true,
  errors = {},
}) => {
  // Track whether each time is using fixed time (true) or solar event (false)
  const [startIsFixedTime, setStartIsFixedTime] = useState(true);
  const [endIsFixedTime, setEndIsFixedTime] = useState(true);

  // Determine initial time type based on value and validate solar events
  useEffect(() => {
    if (value.start_time) {
      const isFixed = TIME_FORMAT_REGEX.test(value.start_time);
      setStartIsFixedTime(isFixed);

      // Warn if value looks like solar event but is invalid
      if (!isFixed && !isValidSolarEvent(value.start_time)) {
        console.warn(`Invalid solar event: ${value.start_time}`);
      }
    }
    if (value.end_time) {
      const isFixed = TIME_FORMAT_REGEX.test(value.end_time);
      setEndIsFixedTime(isFixed);

      // Warn if value looks like solar event but is invalid
      if (!isFixed && !isValidSolarEvent(value.end_time)) {
        console.warn(`Invalid solar event: ${value.end_time}`);
      }
    }
  }, [value.start_time, value.end_time]);

  /**
   * Get solar event label from value
   */
  const getSolarEventLabel = (eventValue) => {
    const event = SOLAR_EVENTS.find(e => e.value === eventValue);
    return event ? event.label : eventValue;
  };

  /**
   * Generate preview text for solar events
   */
  const getSolarPreviewText = (eventValue, offsetMinutes) => {
    if (!eventValue || TIME_FORMAT_REGEX.test(eventValue)) {
      return null;
    }

    const eventLabel = getSolarEventLabel(eventValue);
    const offset = offsetMinutes || 0;

    if (offset === 0) {
      return `At ${eventLabel.toLowerCase()}`;
    } else if (offset > 0) {
      return `${offset} minute${offset !== 1 ? 's' : ''} after ${eventLabel.toLowerCase()}`;
    } else {
      return `${Math.abs(offset)} minute${Math.abs(offset) !== 1 ? 's' : ''} before ${eventLabel.toLowerCase()}`;
    }
  };

  /**
   * Validate time window combination (mixed solar/fixed warning)
   * @returns {string|null} Warning message or null if no warning needed
   */
  const getMixedTimeWindowWarning = () => {
    // Both fixed or both solar - no warning needed
    if (startIsFixedTime === endIsFixedTime) return null;

    // Mixed types - warn user about complexity
    return 'Note: Mixing fixed time with solar event may result in time windows that vary with sunrise/sunset times.';
  };

  const mixedTimeWarning = getMixedTimeWindowWarning();

  /**
   * Handle start time type change
   */
  const handleStartTypeChange = (isFixed) => {
    setStartIsFixedTime(isFixed);

    // Reset to appropriate default
    if (isFixed) {
      onChange({
        ...value,
        start_time: '',
        start_offset_minutes: 0,
      });
    } else {
      onChange({
        ...value,
        start_time: SOLAR_EVENTS[0].value,
        start_offset_minutes: 0,
      });
    }
  };

  /**
   * Handle end time type change
   */
  const handleEndTypeChange = (isFixed) => {
    setEndIsFixedTime(isFixed);

    // Reset to appropriate default
    if (isFixed) {
      onChange({
        ...value,
        end_time: '',
        end_offset_minutes: 0,
      });
    } else {
      onChange({
        ...value,
        end_time: SOLAR_EVENTS[0].value,
        end_offset_minutes: 0,
      });
    }
  };

  /**
   * Handle start time change
   */
  const handleStartTimeChange = (newTime) => {
    onChange({
      ...value,
      start_time: newTime,
    });
  };

  /**
   * Handle end time change
   */
  const handleEndTimeChange = (newTime) => {
    onChange({
      ...value,
      end_time: newTime,
    });
  };

  /**
   * Handle start offset change
   */
  const handleStartOffsetChange = (offset) => {
    const numOffset = Number(offset);
    onChange({
      ...value,
      start_offset_minutes: numOffset,
    });
  };

  /**
   * Handle end offset change
   */
  const handleEndOffsetChange = (offset) => {
    const numOffset = Number(offset);
    onChange({
      ...value,
      end_offset_minutes: numOffset,
    });
  };

  return (
    <div className="space-y-6">
      {/* Start Time */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Start Time
        </label>

        {showSolarEvents && (
          <div className="mb-3 flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                checked={startIsFixedTime}
                onChange={() => handleStartTypeChange(true)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Fixed Time</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                checked={!startIsFixedTime}
                onChange={() => handleStartTypeChange(false)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Solar Event</span>
            </label>
          </div>
        )}

        {startIsFixedTime ? (
          /* Fixed Time Input */
          <div>
            <input
              type="time"
              value={value.start_time}
              onChange={(e) => handleStartTimeChange(e.target.value)}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Start time (fixed)"
            />
          </div>
        ) : (
          /* Solar Event Input */
          <div className="space-y-2">
            <div className="flex gap-2">
              <select
                value={value.start_time}
                onChange={(e) => handleStartTimeChange(e.target.value)}
                disabled={disabled}
                className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Start time (solar event)"
              >
                {SOLAR_EVENTS.map((event) => (
                  <option key={event.value} value={event.value}>
                    {event.label}
                  </option>
                ))}
              </select>

              <div className="flex items-center gap-2">
                <label
                  htmlFor="start_offset"
                  className="text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap"
                >
                  Offset:
                </label>
                <input
                  id="start_offset"
                  type="number"
                  min={-120}
                  max={120}
                  value={value.start_offset_minutes || 0}
                  onChange={(e) => handleStartOffsetChange(e.target.value)}
                  disabled={disabled}
                  className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-2 py-2 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Start time offset (minutes)"
                />
                <span className="text-sm text-gray-500 dark:text-gray-300">min</span>
              </div>
            </div>

            {/* Preview Text */}
            {value.start_time && (
              <p className="text-sm text-gray-600 dark:text-gray-300 italic">
                {getSolarPreviewText(value.start_time, value.start_offset_minutes)}
              </p>
            )}
          </div>
        )}

        {errors.start_time && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {errors.start_time}
          </p>
        )}
      </div>

      {/* End Time */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          End Time
        </label>

        {showSolarEvents && (
          <div className="mb-3 flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                checked={endIsFixedTime}
                onChange={() => handleEndTypeChange(true)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Fixed Time</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                checked={!endIsFixedTime}
                onChange={() => handleEndTypeChange(false)}
                disabled={disabled}
                className="mr-2 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Solar Event</span>
            </label>
          </div>
        )}

        {endIsFixedTime ? (
          /* Fixed Time Input */
          <div>
            <input
              type="time"
              value={value.end_time}
              onChange={(e) => handleEndTimeChange(e.target.value)}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="End time (fixed)"
            />
          </div>
        ) : (
          /* Solar Event Input */
          <div className="space-y-2">
            <div className="flex gap-2">
              <select
                value={value.end_time}
                onChange={(e) => handleEndTimeChange(e.target.value)}
                disabled={disabled}
                className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="End time (solar event)"
              >
                {SOLAR_EVENTS.map((event) => (
                  <option key={event.value} value={event.value}>
                    {event.label}
                  </option>
                ))}
              </select>

              <div className="flex items-center gap-2">
                <label
                  htmlFor="end_offset"
                  className="text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap"
                >
                  Offset:
                </label>
                <input
                  id="end_offset"
                  type="number"
                  min={-120}
                  max={120}
                  value={value.end_offset_minutes || 0}
                  onChange={(e) => handleEndOffsetChange(e.target.value)}
                  disabled={disabled}
                  className="w-20 rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-2 py-2 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="End time offset (minutes)"
                />
                <span className="text-sm text-gray-500 dark:text-gray-300">min</span>
              </div>
            </div>

            {/* Preview Text */}
            {value.end_time && (
              <p className="text-sm text-gray-600 dark:text-gray-300 italic">
                {getSolarPreviewText(value.end_time, value.end_offset_minutes)}
              </p>
            )}
          </div>
        )}

        {errors.end_time && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {errors.end_time}
          </p>
        )}
      </div>

      {/* Mixed Time Window Warning */}
      {mixedTimeWarning && (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          {mixedTimeWarning}
        </p>
      )}

      {/* General Errors */}
      {errors.general && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {errors.general}
        </p>
      )}
    </div>
  );
};

TimeWindowInput.propTypes = {
  value: PropTypes.shape({
    start_time: PropTypes.string.isRequired,
    end_time: PropTypes.string.isRequired,
    start_offset_minutes: PropTypes.number,
    end_offset_minutes: PropTypes.number,
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  showSolarEvents: PropTypes.bool,
  errors: PropTypes.shape({
    start_time: PropTypes.string,
    end_time: PropTypes.string,
    general: PropTypes.string,
  }),
};

export default TimeWindowInput;
