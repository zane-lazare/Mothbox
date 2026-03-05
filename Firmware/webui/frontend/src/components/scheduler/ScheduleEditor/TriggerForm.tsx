import { useState, useEffect } from 'react';
import { TRIGGER_TYPES, TRIGGER_DEFAULTS } from './constants';
import type { Trigger, TriggerErrors, TriggerType } from './scheduler-types';
import IntervalTriggerForm from './IntervalTriggerForm';
import SolarTriggerForm from './SolarTriggerForm';
import MoonPhaseTriggerForm from './MoonPhaseTriggerForm';
import FixedTimeTriggerForm from './FixedTimeTriggerForm';
import SensorTriggerForm from './SensorTriggerForm';
// @ts-expect-error -- .jsx module
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

interface TriggerFormProps {
  /** Trigger configuration with type-specific fields. Type determines which fields are active. */
  value?: Trigger;
  /** Callback when trigger configuration changes */
  onChange: (value: Trigger) => void;
  /** Whether the form is disabled */
  disabled?: boolean;
  /** Validation errors for trigger fields */
  errors?: TriggerErrors;
}

const TriggerForm = ({
  // TRIGGER_DEFAULTS uses readonly arrays (as const); shallow spread + double cast
  // bridges to the mutable Trigger union. Safe: this is a static default value.
  value = { ...TRIGGER_DEFAULTS.interval } as unknown as Trigger,
  onChange,
  disabled = false,
  errors = {},
}: TriggerFormProps) => {
  /**
   * Get current trigger type from value
   */
  const triggerType: TriggerType = value.trigger_type || 'interval';

  /**
   * Expert mode state - true if trigger_type is 'cron'
   */
  const [expertMode, setExpertMode] = useState<'visual' | 'expert'>(triggerType === 'cron' ? 'expert' : 'visual');

  /**
   * Store previous trigger type for switching back from expert mode
   */
  const [previousTriggerType, setPreviousTriggerType] = useState<TriggerType>(
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
  const handleExpertModeChange = (newMode: 'visual' | 'expert') => {
    setExpertMode(newMode);

    if (newMode === 'expert') {
      // Switch to cron trigger type
      const defaults = TRIGGER_DEFAULTS.cron;
      onChange({
        ...defaults,
        trigger_type: 'cron',
      } as Trigger);
    } else {
      // Switch back to previous trigger type
      const defaults = TRIGGER_DEFAULTS[previousTriggerType as keyof typeof TRIGGER_DEFAULTS] || TRIGGER_DEFAULTS.interval;
      onChange({
        ...defaults,
        trigger_type: previousTriggerType,
      } as Trigger);
    }
  };

  /**
   * Handle trigger type change
   * Resets the value to defaults for the new trigger type
   */
  const handleTriggerTypeChange = (newType: string) => {
    // Get default values for the new trigger type
    const defaults = TRIGGER_DEFAULTS[newType as keyof typeof TRIGGER_DEFAULTS] || TRIGGER_DEFAULTS.interval;
    onChange({
      ...defaults,
      trigger_type: newType,
    } as Trigger);
    setPreviousTriggerType(newType as TriggerType);
  };

  /**
   * Handle value change from the specific trigger form
   * Preserves the trigger_type when forwarding changes
   */
  const handleTriggerValueChange = (newValue: Trigger) => {
    onChange({
      ...newValue,
      trigger_type: triggerType,
    } as Trigger);
  };

  /**
   * Handle cron expression change
   */
  const handleCronExpressionChange = (newExpression: string) => {
    onChange({
      ...value,
      trigger_type: 'cron',
      cron_expression: newExpression,
    } as Trigger);
  };

  /**
   * Get description for current trigger type
   */
  const getDescription = (): string => {
    return TRIGGER_TYPES[triggerType as keyof typeof TRIGGER_TYPES]?.description || '';
  };

  /**
   * Render the appropriate trigger form based on type
   */
  const renderTriggerForm = () => {
    // Each child form defines its own value/onChange types.
    // The switch statement guarantees the correct trigger type is dispatched.
    // We pass props explicitly; `as any` bridges the Trigger union to each
    // sub-form's specific value type until #490 adds proper narrowing.
    /* eslint-disable @typescript-eslint/no-explicit-any */
    switch (triggerType) {
      case 'interval':
        return <IntervalTriggerForm value={value as any} onChange={handleTriggerValueChange as any} disabled={disabled} errors={errors as any} />;
      case 'solar':
        return <SolarTriggerForm value={value as any} onChange={handleTriggerValueChange as any} disabled={disabled} errors={errors as any} />;
      case 'moon_phase':
        return <MoonPhaseTriggerForm value={value as any} onChange={handleTriggerValueChange as any} disabled={disabled} errors={errors as any} />;
      case 'fixed_time':
        return <FixedTimeTriggerForm value={value as any} onChange={handleTriggerValueChange as any} disabled={disabled} errors={errors as any} />;
      case 'sensor':
        return <SensorTriggerForm value={value as any} onChange={handleTriggerValueChange as any} disabled={disabled} errors={errors as any} />;
      default:
        return <IntervalTriggerForm value={value as any} onChange={handleTriggerValueChange as any} disabled={disabled} errors={errors as any} />;
    }
    /* eslint-enable @typescript-eslint/no-explicit-any */
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
            value={(value as { cron_expression?: string }).cron_expression || '0 21 * * *'}
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

export default TriggerForm;
