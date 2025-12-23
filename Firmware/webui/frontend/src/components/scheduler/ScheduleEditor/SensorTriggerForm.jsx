import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { SENSOR_TYPES, SENSOR_COMPARISONS, SCHEDULE_LIMITS, validateNumericInput } from './constants';
import { NUMERIC_ERRORS } from './errorMessages';

/**
 * SensorTriggerForm Component
 *
 * A form for configuring sensor-based triggers that execute patterns
 * when sensor readings meet specified conditions with cooldown periods.
 *
 * @component
 * @example
 * <SensorTriggerForm
 *   value={{
 *     sensor_type: "light",
 *     comparison: "lt",
 *     threshold: 100,
 *     cooldown_minutes: 5
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const SensorTriggerForm = ({
  value = {
    sensor_type: 'light',
    comparison: 'lt',
    threshold: 100,
    cooldown_minutes: 5,
  },
  onChange,
  disabled = false,
  errors = {},
}) => {
  // Local validation error states
  const [thresholdError, setThresholdError] = useState(null);
  const [cooldownError, setCooldownError] = useState(null);

  /**
   * Handle sensor type change
   */
  const handleSensorTypeChange = (newSensorType) => {
    onChange({
      ...value,
      sensor_type: newSensorType,
    });
  };

  /**
   * Handle comparison operator change
   */
  const handleComparisonChange = (newComparison) => {
    onChange({
      ...value,
      comparison: newComparison,
    });
  };

  /**
   * Handle threshold change with validation
   */
  const handleThresholdChange = (newThreshold) => {
    const validated = validateNumericInput(newThreshold, 0);
    if (validated === null) {
      setThresholdError(NUMERIC_ERRORS.INVALID_THRESHOLD);
      return;
    }
    setThresholdError(null);
    onChange({
      ...value,
      threshold: validated,
    });
  };

  /**
   * Handle cooldown minutes change with validation
   */
  const handleCooldownChange = (newCooldown) => {
    const validated = validateNumericInput(newCooldown, 0, SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES);
    if (validated === null) {
      setCooldownError(NUMERIC_ERRORS.INVALID_COOLDOWN(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES));
      return;
    }
    setCooldownError(null);
    onChange({
      ...value,
      cooldown_minutes: validated,
    });
  };

  /**
   * Get description for the selected sensor type
   * @returns {string} Description text
   */
  const getSensorDescription = () => {
    const sensor = SENSOR_TYPES.find((s) => s.value === value.sensor_type);
    return sensor ? sensor.description : '';
  };

  /**
   * Get label for the selected sensor type
   * @returns {string} Label text
   */
  const getSensorLabel = () => {
    const sensor = SENSOR_TYPES.find((s) => s.value === value.sensor_type);
    return sensor ? sensor.label.toLowerCase() : value.sensor_type;
  };

  /**
   * Get symbol for the selected comparison operator
   * @returns {string} Symbol
   */
  const getComparisonSymbol = () => {
    const comparison = SENSOR_COMPARISONS.find((c) => c.value === value.comparison);
    return comparison ? comparison.symbol : value.comparison;
  };

  /**
   * Get unit for the selected sensor type
   * @returns {string} Unit string
   */
  const getSensorUnit = () => {
    const units = {
      motion: '',
      light: 'lux',
      temperature: '°C',
    };
    return units[value.sensor_type] || '';
  };

  /**
   * Memoized preview text to prevent recalculation on every render
   */
  const previewText = useMemo(() => {
    const sensorLabel = getSensorLabel();
    const comparisonSymbol = getComparisonSymbol();
    const unit = getSensorUnit();
    const thresholdText = unit ? `${value.threshold} ${unit}` : value.threshold;

    return `When ${sensorLabel} ${comparisonSymbol} ${thresholdText}, cooldown: ${value.cooldown_minutes} min`;
  }, [value.sensor_type, value.comparison, value.threshold, value.cooldown_minutes]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Sensor Configuration
      </h3>

      {/* Sensor Type Selection */}
      <div>
        <label
          htmlFor="sensor_type"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Sensor Type:
        </label>
        <select
          id="sensor_type"
          value={value.sensor_type}
          onChange={(e) => handleSensorTypeChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600
                   bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Sensor type"
        >
          {SENSOR_TYPES.map((sensor) => (
            <option key={sensor.value} value={sensor.value}>
              {sensor.label}
            </option>
          ))}
        </select>
        {/* Sensor Type Description */}
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-300">
          {getSensorDescription()}
        </p>
      </div>

      {/* Comparison Operator Selection */}
      <div>
        <label
          htmlFor="comparison"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Comparison:
        </label>
        <select
          id="comparison"
          value={value.comparison}
          onChange={(e) => handleComparisonChange(e.target.value)}
          disabled={disabled}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600
                   bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Comparison"
        >
          {SENSOR_COMPARISONS.map((comp) => (
            <option key={comp.value} value={comp.value}>
              {comp.label} ({comp.symbol})
            </option>
          ))}
        </select>
      </div>

      {/* Threshold Input */}
      <div>
        <label
          htmlFor="threshold"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Threshold:
        </label>
        <div className="flex items-center gap-2">
          <input
            id="threshold"
            type="number"
            min={0}
            value={value.threshold}
            onChange={(e) => handleThresholdChange(e.target.value)}
            disabled={disabled}
            className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Threshold"
          />
          {getSensorUnit() && (
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {getSensorUnit()}
            </span>
          )}
        </div>
        {(thresholdError || errors.threshold) && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {thresholdError || errors.threshold}
          </p>
        )}
      </div>

      {/* Cooldown Input */}
      <div>
        <label
          htmlFor="cooldown_minutes"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Cooldown (minutes):
        </label>
        <div className="flex items-center gap-2">
          <input
            id="cooldown_minutes"
            type="number"
            min={0}
            max={SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES}
            value={value.cooldown_minutes}
            onChange={(e) => handleCooldownChange(e.target.value)}
            disabled={disabled}
            className="w-32 rounded-md border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Cooldown in minutes"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">minutes</span>
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-300">
          Minimum time between consecutive triggers
        </p>
        {(cooldownError || errors.cooldown_minutes) && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {cooldownError || errors.cooldown_minutes}
          </p>
        )}
      </div>

      {/* Preview */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Preview:
        </label>
        <p className="text-sm text-gray-600 dark:text-gray-300 italic bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
          {previewText}
        </p>
      </div>
    </div>
  );
};

SensorTriggerForm.propTypes = {
  /** Sensor trigger configuration containing sensor_type, comparison, threshold, and cooldown_minutes */
  value: PropTypes.shape({
    sensor_type: PropTypes.string.isRequired,
    comparison: PropTypes.string.isRequired,
    threshold: PropTypes.number.isRequired,
    cooldown_minutes: PropTypes.number.isRequired,
  }),
  /** Callback when sensor trigger configuration changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the form is disabled */
  disabled: PropTypes.bool,
  /** Validation errors for sensor trigger fields */
  errors: PropTypes.shape({
    sensor_type: PropTypes.string,
    comparison: PropTypes.string,
    threshold: PropTypes.string,
    cooldown_minutes: PropTypes.string,
  }),
};

export default SensorTriggerForm;
