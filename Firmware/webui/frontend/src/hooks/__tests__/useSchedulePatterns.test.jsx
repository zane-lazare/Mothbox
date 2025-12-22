/**
 * Tests for useSchedulePatterns hooks (Issue #223)
 *
 * Comprehensive test suite following TDD approach - tests written BEFORE implementation.
 * Tests React Query hooks for Schedule Pattern operations (utility hooks and composite hooks).
 *
 * This file tests:
 * - useTriggerDescription: Human-readable trigger descriptions
 * - useIntervalTriggerDefaults: Default interval trigger config
 * - useSolarTriggerDefaults: Default solar trigger config
 * - useMoonPhaseTriggerDefaults: Default moon phase trigger config
 * - useSchedulePatternOperations: Combined create/update/delete mutations
 * - useDuplicateSchedule: Clone schedule with new name
 * - useScheduleFromTemplate: Create from built-in template
 * - Re-exports from useSchedules.js
 *
 * Reference: useSchedules.test.jsx, useEventPatterns.test.jsx for testing patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useTriggerDescription,
  useIntervalTriggerDefaults,
  useSolarTriggerDefaults,
  useMoonPhaseTriggerDefaults,
  useSchedulePatternOperations,
  useDuplicateSchedule,
  useScheduleFromTemplate,
  // Re-exports from useSchedules.js
  useSchedules,
  useSchedule,
  useActiveSchedule,
  useSchedulePreview,
  useBuiltinSchedules,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useActivateSchedule,
  useDeactivateSchedule,
  useValidateSchedule,
} from '../useSchedulePatterns';
import * as schedulerApi from '../../utils/schedulerApi';

// Mock the API module
vi.mock('../../utils/schedulerApi');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// =============================================================================
// useTriggerDescription Tests
// =============================================================================

describe('useTriggerDescription', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns formatted description for interval trigger', () => {
    const schedule = {
      name: 'Hourly Survey',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: {
            type: 'interval',
            interval_minutes: 60,
            time_window: {
              start_time: '06:00',
              end_time: '18:00'
            }
          }
        }
      ]
    };

    const { result } = renderHook(() => useTriggerDescription(schedule), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('Every 60 minutes from 06:00 to 18:00');
  });

  it('returns formatted description for solar trigger', () => {
    const schedule = {
      name: 'Sunset Capture',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: {
            type: 'solar',
            solar_event: 'sunset',
            offset_minutes: 30
          }
        }
      ]
    };

    const { result } = renderHook(() => useTriggerDescription(schedule), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('At sunset +30 minutes');
  });

  it('returns formatted description for moon phase trigger', () => {
    const schedule = {
      name: 'Full Moon Capture',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: {
            type: 'moon_phase',
            phases: ['full'],
            offset_days: 2
          }
        }
      ]
    };

    const { result } = renderHook(() => useTriggerDescription(schedule), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('On full moon ±2 days');
  });

  it('returns "Unknown trigger" for unrecognized type', () => {
    const schedule = {
      name: 'Custom Schedule',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: {
            type: 'custom_sensor'
          }
        }
      ]
    };

    const { result } = renderHook(() => useTriggerDescription(schedule), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('Unknown trigger');
  });

  it('returns "Unknown trigger" for schedule with no events', () => {
    const schedule = {
      name: 'Empty Schedule',
      events: []
    };

    const { result } = renderHook(() => useTriggerDescription(schedule), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('Unknown trigger');
  });

  it('returns "Unknown trigger" for null schedule', () => {
    const { result } = renderHook(() => useTriggerDescription(null), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('Unknown trigger');
  });

  it('handles solar trigger with negative offset', () => {
    const schedule = {
      name: 'Before Sunrise',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: {
            type: 'solar',
            solar_event: 'sunrise',
            offset_minutes: -15
          }
        }
      ]
    };

    const { result } = renderHook(() => useTriggerDescription(schedule), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe('At sunrise -15 minutes');
  });
});

// =============================================================================
// Trigger Defaults Tests
// =============================================================================

describe('useIntervalTriggerDefaults', () => {
  it('returns default interval trigger config', () => {
    const { result } = renderHook(() => useIntervalTriggerDefaults(), {
      wrapper: createWrapper()
    });

    expect(result.current).toEqual({
      interval_minutes: 60,
      time_window: {
        start_time: '21:00',
        end_time: '05:00'
      }
    });
  });

  it('returns same object reference across rerenders (memoized)', () => {
    const { result, rerender } = renderHook(() => useIntervalTriggerDefaults(), {
      wrapper: createWrapper()
    });

    const firstResult = result.current;
    rerender();

    expect(result.current).toBe(firstResult);
  });
});

describe('useSolarTriggerDefaults', () => {
  it('returns default solar trigger config', () => {
    const { result } = renderHook(() => useSolarTriggerDefaults(), {
      wrapper: createWrapper()
    });

    expect(result.current).toEqual({
      solar_event: 'sunset',
      offset_minutes: 30,
      days_of_week: null
    });
  });

  it('returns same object reference across rerenders (memoized)', () => {
    const { result, rerender } = renderHook(() => useSolarTriggerDefaults(), {
      wrapper: createWrapper()
    });

    const firstResult = result.current;
    rerender();

    expect(result.current).toBe(firstResult);
  });
});

describe('useMoonPhaseTriggerDefaults', () => {
  it('returns default moon phase trigger config', () => {
    const { result } = renderHook(() => useMoonPhaseTriggerDefaults(), {
      wrapper: createWrapper()
    });

    expect(result.current).toEqual({
      phases: ['full'],
      offset_days: 0,
      time_window: null
    });
  });

  it('returns same object reference across rerenders (memoized)', () => {
    const { result, rerender } = renderHook(() => useMoonPhaseTriggerDefaults(), {
      wrapper: createWrapper()
    });

    const firstResult = result.current;
    rerender();

    expect(result.current).toBe(firstResult);
  });
});

// =============================================================================
// useSchedulePatternOperations Tests
// =============================================================================

describe('useSchedulePatternOperations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns combined mutation objects', () => {
    schedulerApi.createSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });
    schedulerApi.updateSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });
    schedulerApi.deleteSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });

    const { result } = renderHook(() => useSchedulePatternOperations(), {
      wrapper: createWrapper()
    });

    expect(result.current).toHaveProperty('create');
    expect(result.current).toHaveProperty('update');
    expect(result.current).toHaveProperty('delete');
    expect(result.current).toHaveProperty('isPending');
    expect(result.current).toHaveProperty('errors');

    expect(result.current.create).toHaveProperty('mutate');
    expect(result.current.update).toHaveProperty('mutate');
    expect(result.current.delete).toHaveProperty('mutate');
  });

  it('isPending is true when create mutation is pending', async () => {
    // Set up a delayed response to keep mutation pending
    schedulerApi.createSchedule.mockReturnValue(
      new Promise((resolve) => setTimeout(() => resolve({ data: { id: 'schedule_1' } }), 1000))
    );
    schedulerApi.updateSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });
    schedulerApi.deleteSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });

    const { result } = renderHook(() => useSchedulePatternOperations(), {
      wrapper: createWrapper()
    });

    expect(result.current.isPending).toBe(false);

    result.current.create.mutate({ name: 'Test Schedule', events: [] });

    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    });
  });

  it('isPending is true when any mutation is pending', async () => {
    schedulerApi.createSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });
    schedulerApi.updateSchedule.mockReturnValue(
      new Promise((resolve) => setTimeout(() => resolve({ data: { id: 'schedule_1' } }), 1000))
    );
    schedulerApi.deleteSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });

    const { result } = renderHook(() => useSchedulePatternOperations(), {
      wrapper: createWrapper()
    });

    expect(result.current.isPending).toBe(false);

    result.current.update.mutate({ id: 'schedule_1', data: { name: 'Updated' } });

    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    });
  });

  it('errors collected from mutations', async () => {
    const mockError = new Error('Create failed');
    schedulerApi.createSchedule.mockRejectedValue(mockError);
    schedulerApi.updateSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });
    schedulerApi.deleteSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });

    const { result } = renderHook(() => useSchedulePatternOperations(), {
      wrapper: createWrapper()
    });

    result.current.create.mutate({ name: 'Test Schedule', events: [] });

    await waitFor(() => {
      expect(result.current.errors).toContain(mockError);
    });
  });

  it('collects errors from all mutations', async () => {
    const createError = new Error('Create failed');
    const updateError = new Error('Update failed');
    schedulerApi.createSchedule.mockRejectedValue(createError);
    schedulerApi.updateSchedule.mockRejectedValue(updateError);
    schedulerApi.deleteSchedule.mockResolvedValue({ data: { id: 'schedule_1' } });

    const { result } = renderHook(() => useSchedulePatternOperations(), {
      wrapper: createWrapper()
    });

    result.current.create.mutate({ name: 'Test Schedule', events: [] });
    await waitFor(() => {
      expect(result.current.errors).toContain(createError);
    });

    result.current.update.mutate({ id: 'schedule_1', data: { name: 'Updated' } });
    await waitFor(() => {
      expect(result.current.errors).toContain(updateError);
      expect(result.current.errors.length).toBe(2);
    });
  });
});

// =============================================================================
// useDuplicateSchedule Tests
// =============================================================================

describe('useDuplicateSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates copy with new name', async () => {
    const sourceSchedule = {
      id: 'schedule_1',
      schedule_id: 'schedule_1',
      name: 'Original Schedule',
      description: 'Test description',
      created_at: '2024-01-01T00:00:00Z',
      modified_at: '2024-01-01T00:00:00Z',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: { type: 'fixed_time', time: '06:00:00' }
        }
      ]
    };

    const expectedCopy = {
      name: 'Copy of Original Schedule',
      description: 'Test description',
      events: [
        {
          name: 'capture',
          action: 'take_photo',
          trigger: { type: 'fixed_time', time: '06:00:00' }
        }
      ]
    };

    schedulerApi.getSchedule.mockResolvedValue({ data: sourceSchedule });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_2', message: 'Schedule created' }
    });

    const { result } = renderHook(() => useDuplicateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ sourceId: 'schedule_1', newName: 'Copy of Original Schedule' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(schedulerApi.getSchedule).toHaveBeenCalledWith('schedule_1');
    expect(schedulerApi.createSchedule).toHaveBeenCalledWith(expectedCopy);
  });

  it('invalidates schedules cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.getSchedule.mockResolvedValue({
      data: {
        id: 'schedule_1',
        schedule_id: 'schedule_1',
        name: 'Original',
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        events: []
      }
    });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_2', message: 'Created' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDuplicateSchedule(), { wrapper });

    result.current.mutate({ sourceId: 'schedule_1', newName: 'Copy' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });

  it('handles API error from getSchedule', async () => {
    const mockError = new Error('Schedule not found');
    schedulerApi.getSchedule.mockRejectedValue(mockError);
    schedulerApi.createSchedule.mockResolvedValue({ data: { id: 'schedule_2' } });

    const { result } = renderHook(() => useDuplicateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ sourceId: 'nonexistent', newName: 'Copy' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
    expect(schedulerApi.createSchedule).not.toHaveBeenCalled();
  });

  it('handles API error from createSchedule', async () => {
    const mockError = new Error('Create failed');
    schedulerApi.getSchedule.mockResolvedValue({
      data: {
        id: 'schedule_1',
        schedule_id: 'schedule_1',
        name: 'Original',
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        events: []
      }
    });
    schedulerApi.createSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useDuplicateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ sourceId: 'schedule_1', newName: 'Copy' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });

  it('omits id, schedule_id, created_at, and modified_at from duplicated schedule', async () => {
    const sourceSchedule = {
      id: 'schedule_1',
      schedule_id: 'schedule_1',
      name: 'Original',
      description: 'Test',
      created_at: '2024-01-01T00:00:00Z',
      modified_at: '2024-01-01T00:00:00Z',
      events: []
    };

    schedulerApi.getSchedule.mockResolvedValue({ data: sourceSchedule });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_2', message: 'Created' }
    });

    const { result } = renderHook(() => useDuplicateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ sourceId: 'schedule_1', newName: 'Copy' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const createCall = schedulerApi.createSchedule.mock.calls[0][0];
    expect(createCall).not.toHaveProperty('id');
    expect(createCall).not.toHaveProperty('schedule_id');
    expect(createCall).not.toHaveProperty('created_at');
    expect(createCall).not.toHaveProperty('modified_at');
  });

  it('omits category field from duplicated schedule', async () => {
    const sourceSchedule = {
      id: 'schedule_1',
      schedule_id: 'schedule_1',
      name: 'Built-in Schedule',
      category: 'built-in',
      description: 'Test',
      created_at: '2024-01-01T00:00:00Z',
      modified_at: '2024-01-01T00:00:00Z',
      events: []
    };

    schedulerApi.getSchedule.mockResolvedValue({ data: sourceSchedule });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_2', message: 'Created' }
    });

    const { result } = renderHook(() => useDuplicateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ sourceId: 'schedule_1', newName: 'Copy' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const createCall = schedulerApi.createSchedule.mock.calls[0][0];
    expect(createCall).not.toHaveProperty('category');
  });
});

// =============================================================================
// useScheduleFromTemplate Tests
// =============================================================================

describe('useScheduleFromTemplate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates schedule from built-in template', async () => {
    const template = {
      id: 'sunset_moths',
      schedule_id: 'sunset_moths',
      name: 'Sunset Moths',
      category: 'built-in',
      description: 'Capture moths at sunset',
      created_at: '2024-01-01T00:00:00Z',
      modified_at: '2024-01-01T00:00:00Z',
      events: [
        {
          name: 'sunset_capture',
          action: 'take_photo',
          trigger: { type: 'solar', solar_event: 'sunset', offset_minutes: 30 }
        }
      ]
    };

    const expectedSchedule = {
      name: 'My Sunset Moths',
      description: 'Capture moths at sunset',
      events: [
        {
          name: 'sunset_capture',
          action: 'take_photo',
          trigger: { type: 'solar', solar_event: 'sunset', offset_minutes: 30 }
        }
      ]
    };

    schedulerApi.getSchedule.mockResolvedValue({ data: template });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_new', message: 'Schedule created' }
    });

    const { result } = renderHook(() => useScheduleFromTemplate(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ templateId: 'sunset_moths', customizations: { name: 'My Sunset Moths' } });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(schedulerApi.getSchedule).toHaveBeenCalledWith('sunset_moths');
    expect(schedulerApi.createSchedule).toHaveBeenCalledWith(expectedSchedule);
  });

  it('invalidates cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.getSchedule.mockResolvedValue({
      data: {
        id: 'template_1',
        schedule_id: 'template_1',
        name: 'Template',
        category: 'built-in',
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        events: []
      }
    });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_new', message: 'Created' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useScheduleFromTemplate(), { wrapper });

    result.current.mutate({ templateId: 'template_1', customizations: { name: 'My Schedule' } });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });

  it('handles API error from template fetch', async () => {
    const mockError = new Error('Template not found');
    schedulerApi.getSchedule.mockRejectedValue(mockError);
    schedulerApi.createSchedule.mockResolvedValue({ data: { id: 'schedule_new' } });

    const { result } = renderHook(() => useScheduleFromTemplate(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ templateId: 'nonexistent', customizations: { name: 'My Schedule' } });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
    expect(schedulerApi.createSchedule).not.toHaveBeenCalled();
  });

  it('omits id, schedule_id, created_at, modified_at, and category from created schedule', async () => {
    const template = {
      id: 'template_1',
      schedule_id: 'template_1',
      name: 'Template',
      category: 'built-in',
      description: 'Test',
      created_at: '2024-01-01T00:00:00Z',
      modified_at: '2024-01-01T00:00:00Z',
      events: []
    };

    schedulerApi.getSchedule.mockResolvedValue({ data: template });
    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_new', message: 'Created' }
    });

    const { result } = renderHook(() => useScheduleFromTemplate(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ templateId: 'template_1', customizations: { name: 'My Schedule' } });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const createCall = schedulerApi.createSchedule.mock.calls[0][0];
    expect(createCall).not.toHaveProperty('id');
    expect(createCall).not.toHaveProperty('schedule_id');
    expect(createCall).not.toHaveProperty('created_at');
    expect(createCall).not.toHaveProperty('modified_at');
    expect(createCall).not.toHaveProperty('category');
  });
});

// =============================================================================
// Re-export Tests
// =============================================================================

describe('Module re-exports', () => {
  it('exports all expected hooks', () => {
    expect(useSchedules).toBeDefined();
    expect(useSchedule).toBeDefined();
    expect(useActiveSchedule).toBeDefined();
    expect(useSchedulePreview).toBeDefined();
    expect(useBuiltinSchedules).toBeDefined();
    expect(useCreateSchedule).toBeDefined();
    expect(useUpdateSchedule).toBeDefined();
    expect(useDeleteSchedule).toBeDefined();
    expect(useActivateSchedule).toBeDefined();
    expect(useDeactivateSchedule).toBeDefined();
    expect(useValidateSchedule).toBeDefined();
  });

  it('re-exported hooks are callable', () => {
    schedulerApi.listSchedules.mockResolvedValue({ data: { schedules: [], total: 0 } });
    schedulerApi.getSchedule.mockResolvedValue({ data: {} });
    schedulerApi.getActiveSchedule.mockResolvedValue({ data: { active_schedule: null } });
    schedulerApi.getSchedulePreview.mockResolvedValue({ data: { executions: [], total: 0 } });
    schedulerApi.listBuiltinSchedules.mockResolvedValue({ data: { schedules: [], total: 0 } });

    // Test query hooks
    const { result: result1 } = renderHook(() => useSchedules(), {
      wrapper: createWrapper()
    });
    expect(result1.current).toBeDefined();

    const { result: result2 } = renderHook(() => useSchedule('schedule_1'), {
      wrapper: createWrapper()
    });
    expect(result2.current).toBeDefined();

    const { result: result3 } = renderHook(() => useActiveSchedule(), {
      wrapper: createWrapper()
    });
    expect(result3.current).toBeDefined();

    const { result: result4 } = renderHook(() => useSchedulePreview('schedule_1'), {
      wrapper: createWrapper()
    });
    expect(result4.current).toBeDefined();

    const { result: result5 } = renderHook(() => useBuiltinSchedules(), {
      wrapper: createWrapper()
    });
    expect(result5.current).toBeDefined();

    // Test mutation hooks
    const { result: result6 } = renderHook(() => useCreateSchedule(), {
      wrapper: createWrapper()
    });
    expect(result6.current).toBeDefined();
    expect(result6.current.mutate).toBeInstanceOf(Function);

    const { result: result7 } = renderHook(() => useUpdateSchedule(), {
      wrapper: createWrapper()
    });
    expect(result7.current).toBeDefined();
    expect(result7.current.mutate).toBeInstanceOf(Function);

    const { result: result8 } = renderHook(() => useDeleteSchedule(), {
      wrapper: createWrapper()
    });
    expect(result8.current).toBeDefined();
    expect(result8.current.mutate).toBeInstanceOf(Function);

    const { result: result9 } = renderHook(() => useActivateSchedule(), {
      wrapper: createWrapper()
    });
    expect(result9.current).toBeDefined();
    expect(result9.current.mutate).toBeInstanceOf(Function);

    const { result: result10 } = renderHook(() => useDeactivateSchedule(), {
      wrapper: createWrapper()
    });
    expect(result10.current).toBeDefined();
    expect(result10.current.mutate).toBeInstanceOf(Function);

    const { result: result11 } = renderHook(() => useValidateSchedule(), {
      wrapper: createWrapper()
    });
    expect(result11.current).toBeDefined();
    expect(result11.current.mutate).toBeInstanceOf(Function);
  });
});
