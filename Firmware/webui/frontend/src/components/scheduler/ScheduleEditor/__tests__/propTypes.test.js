/**
 * Tests for shared PropTypes module (Issue #262)
 *
 * Verifies that all PropTypes are properly exported and validate
 * expected data structures.
 */

import PropTypes from 'prop-types';
import {
  TimeWindowPropType,
  TimeWindowErrorsPropType,
  TriggerErrorsPropType,
  TriggerPropType,
  ActionPropType,
  PatternPropType,
  DateRangePropType,
  PatternSelectionPropType,
  SchedulePropType,
} from '../propTypes';

// Helper to test PropTypes validation
// PropTypes.checkPropTypes returns undefined if valid, logs warning if invalid
const checkPropType = (propType, value, propName = 'testProp') => {
  const props = { [propName]: value };
  const propTypes = { [propName]: propType };

  // Capture console.error to detect PropTypes warnings
  const originalError = console.error;
  let errorMessage = null;
  console.error = (msg) => {
    errorMessage = msg;
  };

  PropTypes.checkPropTypes(propTypes, props, propName, 'TestComponent');

  console.error = originalError;
  return errorMessage;
};

describe('propTypes exports', () => {
  it('exports TimeWindowPropType', () => {
    expect(TimeWindowPropType).toBeDefined();
  });

  it('exports TimeWindowErrorsPropType', () => {
    expect(TimeWindowErrorsPropType).toBeDefined();
  });

  it('exports TriggerErrorsPropType', () => {
    expect(TriggerErrorsPropType).toBeDefined();
  });

  it('exports TriggerPropType', () => {
    expect(TriggerPropType).toBeDefined();
  });

  it('exports ActionPropType', () => {
    expect(ActionPropType).toBeDefined();
  });

  it('exports PatternPropType', () => {
    expect(PatternPropType).toBeDefined();
  });

  it('exports DateRangePropType', () => {
    expect(DateRangePropType).toBeDefined();
  });

  it('exports PatternSelectionPropType', () => {
    expect(PatternSelectionPropType).toBeDefined();
  });

  it('exports SchedulePropType', () => {
    expect(SchedulePropType).toBeDefined();
  });
});

describe('TimeWindowPropType', () => {
  it('accepts valid time window', () => {
    const validTimeWindow = {
      start_time: '21:00',
      end_time: '05:00',
      start_offset_minutes: 30,
      end_offset_minutes: 0,
    };
    const error = checkPropType(TimeWindowPropType, validTimeWindow);
    expect(error).toBeNull();
  });

  it('accepts partial time window', () => {
    const partialTimeWindow = {
      start_time: '21:00',
      end_time: '05:00',
    };
    const error = checkPropType(TimeWindowPropType, partialTimeWindow);
    expect(error).toBeNull();
  });

  it('accepts null/undefined', () => {
    const error = checkPropType(TimeWindowPropType, null);
    expect(error).toBeNull();
  });
});

describe('TimeWindowErrorsPropType', () => {
  it('accepts valid time window errors', () => {
    const validTimeWindowErrors = {
      start_time: 'Invalid start time format',
      end_time: 'End time must be after start time',
      general: 'Time window is required',
    };
    const error = checkPropType(TimeWindowErrorsPropType, validTimeWindowErrors);
    expect(error).toBeNull();
  });

  it('accepts partial time window errors', () => {
    const partialErrors = {
      start_time: 'Invalid format',
    };
    const error = checkPropType(TimeWindowErrorsPropType, partialErrors);
    expect(error).toBeNull();
  });

  it('accepts empty error object', () => {
    const error = checkPropType(TimeWindowErrorsPropType, {});
    expect(error).toBeNull();
  });

  it('accepts null/undefined', () => {
    const error = checkPropType(TimeWindowErrorsPropType, null);
    expect(error).toBeNull();
  });
});

describe('TriggerErrorsPropType', () => {
  it('accepts valid error object', () => {
    const validErrors = {
      trigger_type: 'Please select a trigger type',
      interval_minutes: 'Must be at least 1 minute',
    };
    const error = checkPropType(TriggerErrorsPropType, validErrors);
    expect(error).toBeNull();
  });

  it('accepts empty error object', () => {
    const error = checkPropType(TriggerErrorsPropType, {});
    expect(error).toBeNull();
  });

  it('accepts nested time_window errors', () => {
    const errorsWithTimeWindow = {
      interval_minutes: 'Required',
      time_window: {
        start_time: 'Invalid format',
        end_time: 'Must be after start',
        general: 'Time window is required',
      },
    };
    const error = checkPropType(TriggerErrorsPropType, errorsWithTimeWindow);
    expect(error).toBeNull();
  });
});

describe('TriggerPropType', () => {
  it('accepts interval trigger', () => {
    const intervalTrigger = {
      trigger_type: 'interval',
      interval_minutes: 60,
      time_window: {
        start_time: '21:00',
        end_time: '05:00',
      },
      days_of_week: [0, 1, 2, 3, 4],
    };
    const error = checkPropType(TriggerPropType, intervalTrigger);
    expect(error).toBeNull();
  });

  it('accepts solar trigger', () => {
    const solarTrigger = {
      trigger_type: 'solar',
      solar_event: 'sunset',
      offset_minutes: 30,
    };
    const error = checkPropType(TriggerPropType, solarTrigger);
    expect(error).toBeNull();
  });

  it('accepts moon_phase trigger', () => {
    const moonPhaseTrigger = {
      trigger_type: 'moon_phase',
      moon_phase: 'full',
      time_of_day: '21:00',
      offset_days: 2,
    };
    const error = checkPropType(TriggerPropType, moonPhaseTrigger);
    expect(error).toBeNull();
  });

  it('accepts fixed_time trigger', () => {
    const fixedTimeTrigger = {
      trigger_type: 'fixed_time',
      time_of_day: '21:00',
      days_of_week: [0, 1, 2, 3, 4, 5, 6],
    };
    const error = checkPropType(TriggerPropType, fixedTimeTrigger);
    expect(error).toBeNull();
  });

  it('accepts sensor trigger', () => {
    const sensorTrigger = {
      trigger_type: 'sensor',
      sensor_type: 'motion',
      comparison: 'gt',
      threshold: 0.5,
      cooldown_minutes: 5,
    };
    const error = checkPropType(TriggerPropType, sensorTrigger);
    expect(error).toBeNull();
  });

  it('rejects invalid trigger_type', () => {
    const invalidTrigger = {
      trigger_type: 'invalid_type',
    };
    const error = checkPropType(TriggerPropType, invalidTrigger);
    expect(error).not.toBeNull();
  });
});

describe('ActionPropType', () => {
  it('accepts valid action with all fields', () => {
    const validAction = {
      action_id: 'action-123',
      type: 'gpio',
      parameters: { pin: 'uv_on' },
    };
    const error = checkPropType(ActionPropType, validAction);
    expect(error).toBeNull();
  });

  it('accepts action without action_id', () => {
    const actionWithoutId = {
      type: 'camera',
      parameters: {},
    };
    const error = checkPropType(ActionPropType, actionWithoutId);
    expect(error).toBeNull();
  });

  it('rejects action without type', () => {
    const actionWithoutType = {
      action_id: 'action-123',
      parameters: {},
    };
    const error = checkPropType(ActionPropType, actionWithoutType);
    expect(error).not.toBeNull();
  });
});

describe('PatternPropType', () => {
  it('accepts valid pattern', () => {
    const validPattern = {
      pattern_id: 'pattern-123',
      name: 'UV Capture Cycle',
      description: 'Turn on UV, capture photo, turn off UV',
      actions: [
        { action_id: '1', type: 'gpio', parameters: { pin: 'uv_on' } },
        { action_id: '2', type: 'camera', parameters: {} },
      ],
      category: 'user',
      tags: ['uv', 'capture'],
    };
    const error = checkPropType(PatternPropType, validPattern);
    expect(error).toBeNull();
  });

  it('accepts pattern with minimal required fields', () => {
    const minimalPattern = {
      name: 'Simple Pattern',
      actions: [{ type: 'camera' }],
    };
    const error = checkPropType(PatternPropType, minimalPattern);
    expect(error).toBeNull();
  });

  it('rejects pattern without name', () => {
    const patternWithoutName = {
      pattern_id: 'pattern-123',
      actions: [{ type: 'camera' }],
    };
    const error = checkPropType(PatternPropType, patternWithoutName);
    expect(error).not.toBeNull();
  });

  it('rejects pattern without actions', () => {
    const patternWithoutActions = {
      pattern_id: 'pattern-123',
      name: 'Empty Pattern',
    };
    const error = checkPropType(PatternPropType, patternWithoutActions);
    expect(error).not.toBeNull();
  });
});

describe('DateRangePropType', () => {
  it('accepts valid date range', () => {
    const validDateRange = {
      start_date: '2024-06-01',
      end_date: '2024-08-31',
    };
    const error = checkPropType(DateRangePropType, validDateRange);
    expect(error).toBeNull();
  });

  it('accepts partial date range', () => {
    const partialDateRange = {
      start_date: '2024-06-01',
    };
    const error = checkPropType(DateRangePropType, partialDateRange);
    expect(error).toBeNull();
  });
});

describe('PatternSelectionPropType', () => {
  it('accepts library pattern selection', () => {
    const librarySelection = {
      source: 'library',
      pattern: {
        pattern_id: '123',
        name: 'UV Cycle',
        actions: [{ type: 'gpio' }],
      },
    };
    const error = checkPropType(PatternSelectionPropType, librarySelection);
    expect(error).toBeNull();
  });

  it('accepts custom pattern selection', () => {
    const customSelection = {
      source: 'custom',
      pattern: {
        name: 'My Custom Pattern',
        actions: [{ type: 'camera' }],
      },
    };
    const error = checkPropType(PatternSelectionPropType, customSelection);
    expect(error).toBeNull();
  });

  it('rejects invalid source', () => {
    const invalidSelection = {
      source: 'invalid',
      pattern: {
        name: 'Test',
        actions: [{ type: 'camera' }],
      },
    };
    const error = checkPropType(PatternSelectionPropType, invalidSelection);
    expect(error).not.toBeNull();
  });
});

describe('SchedulePropType', () => {
  it('accepts valid schedule', () => {
    const validSchedule = {
      schedule_id: 'sched-123',
      name: 'Summer Moth Survey',
      description: 'Nightly moth capture from June to August',
      trigger: {
        trigger_type: 'solar',
        solar_event: 'sunset',
        offset_minutes: 30,
      },
      event_patterns: [
        {
          pattern_id: 'pattern-1',
          name: 'UV Capture',
          actions: [{ type: 'gpio' }],
        },
      ],
      date_range: {
        start_date: '2024-06-01',
        end_date: '2024-08-31',
      },
    };
    const error = checkPropType(SchedulePropType, validSchedule);
    expect(error).toBeNull();
  });

  it('accepts partial schedule', () => {
    const partialSchedule = {
      name: 'Basic Schedule',
    };
    const error = checkPropType(SchedulePropType, partialSchedule);
    expect(error).toBeNull();
  });
});
