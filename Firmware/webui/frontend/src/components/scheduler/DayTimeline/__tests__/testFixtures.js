/**
 * Shared test fixtures for DayTimeline components (Issue #326)
 *
 * Consolidates mock data used across test files to reduce duplication
 * and ensure consistency in test scenarios.
 *
 * @module components/scheduler/DayTimeline/__tests__/testFixtures
 */

/**
 * Standard date used across tests (YYYY-MM-DD format)
 */
export const mockDate = '2025-12-17'

/**
 * Standard execution objects for testing
 */
export const mockExecutions = [
  {
    pattern_id: 'routine-1',
    pattern_name: 'Photo Capture',
    start_time: '2025-12-17T18:00:00',
    actions: [
      {
        time: '2025-12-17T18:00:00',
        action_name: 'Take Photo',
        action_type: 'camera',
        offset_minutes: 0,
      },
    ],
  },
  {
    pattern_id: 'routine-2',
    pattern_name: 'Attract On',
    start_time: '2025-12-17T18:15:00',
    actions: [
      {
        time: '2025-12-17T18:15:00',
        action_name: 'Attract On',
        action_type: 'gpio',
        offset_minutes: 0,
      },
    ],
  },
  {
    pattern_id: 'routine-3',
    pattern_name: 'Evening Photo',
    start_time: '2025-12-17T19:00:00',
    actions: [
      {
        time: '2025-12-17T19:00:00',
        action_name: 'Take Photo',
        action_type: 'camera',
        offset_minutes: 0,
      },
    ],
  },
  {
    pattern_id: 'routine-4',
    pattern_name: 'HDR Shot',
    start_time: '2025-12-17T19:00:00',
    actions: [
      {
        time: '2025-12-17T19:00:00',
        action_name: 'HDR Bracket',
        action_type: 'camera',
        offset_minutes: 0,
      },
    ],
  },
]

/**
 * Single execution for simple component tests
 */
export const mockExecution = mockExecutions[0]

/**
 * Error conflict (blocking - time collision)
 */
export const mockErrorConflict = {
  id: 'c1',
  conflict_type: 'time_overlap',
  severity: 'error',
  event1_id: 'routine-3',
  event1_name: 'Evening Photo',
  event2_id: 'routine-4',
  event2_name: 'HDR Shot',
  start_time: '2025-12-17T19:00:00',
  end_time: '2025-12-17T19:15:00',
  message: 'camera busy',
}

/**
 * Warning conflict (non-blocking - GPIO state)
 */
export const mockWarningConflict = {
  id: 'c2',
  conflict_type: 'gpio_state_conflict',
  severity: 'warning',
  event1_id: 'routine-2',
  event1_name: 'Attract On',
  start_time: '2025-12-17T18:15:00',
  message: 'unexpected GPIO state',
}

/**
 * Array containing the error conflict for standard tests
 */
export const mockConflicts = [mockErrorConflict]

/**
 * Array containing both error and warning conflicts
 */
export const mockMixedConflicts = [mockErrorConflict, mockWarningConflict]

/**
 * Execution with HDR action for testing HDR color styling
 */
export const mockHdrExecution = {
  pattern_id: 'routine-hdr',
  pattern_name: 'HDR Capture',
  start_time: '2025-12-17T20:00:00',
  actions: [
    {
      time: '2025-12-17T20:00:00',
      action_name: 'HDR Bracket',
      action_type: 'camera',
      offset_minutes: 0,
    },
  ],
}

/**
 * Execution with GPIO action for testing GPIO color styling
 */
export const mockGpioExecution = {
  pattern_id: 'routine-gpio',
  pattern_name: 'Flash On',
  start_time: '2025-12-17T21:00:00',
  actions: [
    {
      time: '2025-12-17T21:00:00',
      action_name: 'Flash On',
      action_type: 'gpio',
      offset_minutes: 0,
    },
  ],
}

/**
 * Execution with GPS sync action
 */
export const mockGpsSyncExecution = {
  pattern_id: 'routine-gps',
  pattern_name: 'GPS Sync',
  start_time: '2025-12-17T12:00:00',
  actions: [
    {
      time: '2025-12-17T12:00:00',
      action_name: 'Sync GPS',
      action_type: 'gps_sync',
      offset_minutes: 0,
    },
  ],
}

/**
 * Execution with service action
 */
export const mockServiceExecution = {
  pattern_id: 'routine-service',
  pattern_name: 'Restart Service',
  start_time: '2025-12-17T00:00:00',
  actions: [
    {
      time: '2025-12-17T00:00:00',
      action_name: 'Restart Camera',
      action_type: 'service',
      offset_minutes: 0,
    },
  ],
}

/**
 * Factory function to create custom execution objects
 * @param {Object} overrides - Properties to override
 * @returns {Object} Execution object
 */
export function createExecution(overrides = {}) {
  return {
    pattern_id: 'routine-custom',
    pattern_name: 'Custom Execution',
    start_time: '2025-12-17T18:00:00',
    actions: [
      {
        time: '2025-12-17T18:00:00',
        action_name: 'Custom Action',
        action_type: 'camera',
        offset_minutes: 0,
      },
    ],
    ...overrides,
  }
}

/**
 * Factory function to create custom conflict objects
 * @param {Object} overrides - Properties to override
 * @returns {Object} Conflict object
 */
export function createConflict(overrides = {}) {
  return {
    id: 'custom-conflict',
    conflict_type: 'time_overlap',
    severity: 'error',
    event1_id: 'routine-1',
    event1_name: 'Routine 1',
    event2_id: 'routine-2',
    event2_name: 'Routine 2',
    start_time: '2025-12-17T18:00:00',
    end_time: '2025-12-17T18:15:00',
    message: 'Test conflict message',
    ...overrides,
  }
}
