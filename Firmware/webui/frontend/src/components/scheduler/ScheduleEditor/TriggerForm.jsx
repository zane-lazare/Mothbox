import PropTypes from 'prop-types';
import { useState, useEffect } from 'react';
import { TRIGGER_TYPES, TRIGGER_DEFAULTS } from './constants';
import { TimeWindowPropType, TriggerErrorsPropType } from './propTypes';
import IntervalTriggerForm from './IntervalTriggerForm';
import SolarTriggerForm from './SolarTriggerForm';
import MoonPhaseTriggerForm from './MoonPhaseTriggerForm';
import FixedTimeTriggerForm from './FixedTimeTriggerForm';
import SensorTriggerForm from './SensorTriggerForm';
import ExpertModeToggle from '../ExpertMode/ExpertModeToggle';
import CronExpressionInput from '../ExpertMode/CronExpressionInput';

/**
 * TriggerForm Component
 *
 * A switcher component that renders the appropriate trigger form based on
 * the selected trigger type. Manages trigger type selection and delegates
 * to specialized trigger form components.
 *
 * @component
 * @example
 * <TriggerForm
 *   value={{
 *     trigger_type: "interval",
 *     interval_minutes: 60,
 *     time_window: { start_time: "21:00", end_time: "05:00" },
 *     days_of_week: null
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const TriggerForm = ({
  value = {
    trigger_type: 'interval',
    ...TRIGGER_DEFAULTS.interval,
  },
  onChange,
  disabled = false,
  errors = {},
}) => {
  /**
   * Get current trigger type from value
   */
  const triggerType = value.trigger_type || 'interval';

  /**
   * Expert mode state - true if trigger_type is 'cron'
   */
  const [expertMode, setExpertMode] = useState(triggerType === 'cron' ? 'expert' : 'visual');

  /**
   * Store previous trigger type for switching back from expert mode
   */
  const [previousTriggerType, setPreviousTriggerType] = useState(
    triggerType === 'cron' ? 'interval' : triggerType
  );

  /**
   * Sync expert mode when trigger_type changes externally
   */
  useEffect(() => {
    if (triggerType === 'cron') {
      setExpertMode('expert');
    } else {
      setExpertMode('visual');
      setPreviousTriggerType(triggerType);
    }
  }, [triggerType]);

  /**
   * Handle expert mode toggle
   */
  const handleExpertModeChange = (newMode) => {
    setExpertMode(newMode);

    if (newMode === 'expert') {
      // Switch to cron trigger type
      const defaults = TRIGGER_DEFAULTS.cron;
      onChange({
        ...defaults,
        trigger_type: 'cron',
      });
    } else {
      // Switch back to previous trigger type
      const defaults = TRIGGER_DEFAULTS[previousTriggerType] || TRIGGER_DEFAULTS.interval;
      onChange({
        ...defaults,
        trigger_type: previousTriggerType,
      });
    }
  };

  /**
   * Handle trigger type change
   * Resets the value to defaults for the new trigger type
   */
  const handleTriggerTypeChange = (newType) => {
    // Get default values for the new trigger type
    const defaults = TRIGGER_DEFAULTS[newType] || TRIGGER_DEFAULTS.interval;
    onChange({
      ...defaults,
      trigger_type: newType,
    });
    setPreviousTriggerType(newType);
  };

  /**
   * Handle value change from the specific trigger form
   * Preserves the trigger_type when forwarding changes
   */
  const handleTriggerValueChange = (newValue) => {
    onChange({
      ...newValue,
      trigger_type: triggerType,
    });
  };

  /**
   * Handle cron expression change
   */
  const handleCronExpressionChange = (newExpression) => {
    onChange({
      ...value,
      trigger_type: 'cron',
      cron_expression: newExpression,
    });
  };

  /**
   * Get description for current trigger type
   */
  const getDescription = () => {
    return TRIGGER_TYPES[triggerType]?.description || '';
  };

  /**
   * Render the appropriate trigger form based on type
   */
  const renderTriggerForm = () => {
    const commonProps = {
      value,
      onChange: handleTriggerValueChange,
      disabled,
      errors,
    };

    switch (triggerType) {
      case 'interval':
        return <IntervalTriggerForm {...commonProps} />;
      case 'solar':
        return <SolarTriggerForm {...commonProps} />;
      case 'moon_phase':
        return <MoonPhaseTriggerForm {...commonProps} />;
      case 'fixed_time':
        return <FixedTimeTriggerForm {...commonProps} />;
      case 'sensor':
        return <SensorTriggerForm {...commonProps} />;
      default:
        return <IntervalTriggerForm {...commonProps} />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Trigger Configuration
      </h3>

      {/* Expert Mode Toggle */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Mode:
        </label>
        <ExpertModeToggle
          mode={expertMode}
          onChange={handleExpertModeChange}
        />
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {expertMode === 'expert'
            ? 'Expert mode allows you to enter a raw cron expression for maximum flexibility.'
            : 'Visual mode provides an intuitive interface for common scheduling patterns.'
          }
        </p>
      </div>

      {expertMode === 'expert' ? (
        /* Expert Mode: Cron Expression Input */
        <>
          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          <CronExpressionInput
            value={value.cron_expression || '0 21 * * *'}
            onChange={handleCronExpressionChange}
            disabled={disabled}
          />
        </>
      ) : (
        /* Visual Mode: Standard Trigger Forms */
        <>
          {/* Trigger Type Selector */}
          <div>
            <label
              htmlFor="trigger_type"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Trigger Type:
            </label>
            <select
              id="trigger_type"
              value={triggerType}
              onChange={(e) => handleTriggerTypeChange(e.target.value)}
              disabled={disabled}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Trigger type"
            >
              {Object.values(TRIGGER_TYPES)
                .filter((type) => type.value !== 'cron')
                .map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
            </select>
            {/* Type Description */}
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
              {getDescription()}
            </p>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Specific Trigger Form */}
          {renderTriggerForm()}
        </>
      )}
    </div>
  );
};

TriggerForm.propTypes = {
  /** Trigger configuration with type-specific fields. Type determines which fields are active. */
  value: PropTypes.shape({
    trigger_type: PropTypes.oneOf(['interval', 'solar', 'moon_phase', 'fixed_time', 'sensor', 'cron']).isRequired,
    // Interval trigger fields
    interval_minutes: PropTypes.number,
    time_window: TimeWindowPropType,
    // Solar trigger fields
    solar_event: PropTypes.string,
    offset_minutes: PropTypes.number,
    // Moon phase trigger fields
    moon_phase: PropTypes.string,
    time_of_day: PropTypes.string,
    offset_days: PropTypes.number,
    // Fixed time trigger fields
    // (time_of_day already declared)
    // Sensor trigger fields
    sensor_type: PropTypes.string,
    comparison: PropTypes.string,
    threshold: PropTypes.number,
    cooldown_minutes: PropTypes.number,
    // Cron trigger fields
    cron_expression: PropTypes.string,
    // Common fields
    days_of_week: PropTypes.arrayOf(PropTypes.number),
  }),
  /** Callback when trigger configuration changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
  /** Validation errors for trigger fields */
  errors: TriggerErrorsPropType,
};

export default TriggerForm;
