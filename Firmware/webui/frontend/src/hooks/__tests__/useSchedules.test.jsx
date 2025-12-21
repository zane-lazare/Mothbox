/**
 * Tests for useSchedules hooks (Issue #221)
 *
 * Comprehensive test suite following TDD approach - tests written BEFORE implementation.
 * Tests React Query hooks for Scheduler UI API integration.
 *
 * Event pattern hook tests are in useEventPatterns.test.jsx (Issue #222).
 *
 * Reference: useDeployments.test.jsx for testing patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
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
} from '../useSchedules';
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

describe('useSchedules', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches schedules list successfully', async () => {
    const mockSchedules = {
      schedules: [
        {
          id: 'schedule_1',
          name: 'Evening Moths',
          category: 'user',
          description: 'Capture moths after sunset',
          events: []
        },
        {
          id: 'schedule_2',
          name: 'Morning Survey',
          category: 'user',
          description: 'Early morning biodiversity survey',
          events: []
        }
      ],
      total: 2
    };

    schedulerApi.listSchedules.mockResolvedValue({ data: mockSchedules });

    const { result } = renderHook(() => useSchedules(), {
      wrapper: createWrapper()
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockSchedules);
    expect(schedulerApi.listSchedules).toHaveBeenCalledTimes(1);
    expect(schedulerApi.listSchedules).toHaveBeenCalledWith({});
  });

  it('includes built-in schedules when requested', async () => {
    const mockSchedules = {
      schedules: [
        {
          id: 'user_schedule',
          name: 'My Schedule',
          category: 'user',
          events: []
        },
        {
          id: 'sunset_moths',
          name: 'Sunset Moths',
          category: 'builtin',
          events: []
        }
      ],
      total: 2
    };

    schedulerApi.listSchedules.mockResolvedValue({ data: mockSchedules });

    // New API: separate params and queryOptions
    const { result } = renderHook(
      () => useSchedules({ include_builtin: true }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockSchedules);
    expect(schedulerApi.listSchedules).toHaveBeenCalledWith({ include_builtin: true });
  });

  it('accepts separate queryOptions parameter', async () => {
    schedulerApi.listSchedules.mockResolvedValue({
      data: { schedules: [], total: 0 }
    });

    // Test that queryOptions are passed through by using a different staleTime
    const { result } = renderHook(
      () => useSchedules({ include_builtin: false }, { staleTime: 1000 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify API was called with correct params
    expect(schedulerApi.listSchedules).toHaveBeenCalledWith({ include_builtin: false });
  });

  it('handles fetch error', async () => {
    const mockError = new Error('Failed to fetch schedules');
    schedulerApi.listSchedules.mockRejectedValue(mockError);

    const { result } = renderHook(() => useSchedules(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });

  it('returns empty array when no schedules exist', async () => {
    schedulerApi.listSchedules.mockResolvedValue({ data: { schedules: [], total: 0 } });

    const { result } = renderHook(() => useSchedules(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.schedules).toEqual([]);
    expect(result.current.data.total).toBe(0);
  });
});

describe('useSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches single schedule by ID', async () => {
    const mockSchedule = {
      id: 'schedule_1',
      name: 'Evening Moths',
      category: 'user',
      description: 'Capture moths after sunset',
      events: [
        {
          name: 'evening_capture',
          action: 'take_photo',
          trigger: { type: 'solar', solar_event: 'sunset', offset_minutes: 30 }
        }
      ],
      created_at: '2024-12-01T10:00:00Z',
      modified_at: '2024-12-15T14:30:00Z'
    };

    schedulerApi.getSchedule.mockResolvedValue({ data: mockSchedule });

    const { result } = renderHook(() => useSchedule('schedule_1'), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockSchedule);
    expect(schedulerApi.getSchedule).toHaveBeenCalledWith('schedule_1');
  });

  it('does not fetch when id is null', () => {
    schedulerApi.getSchedule.mockResolvedValue({ data: {} });

    const { result } = renderHook(() => useSchedule(null), {
      wrapper: createWrapper()
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(schedulerApi.getSchedule).not.toHaveBeenCalled();
  });

  it('handles 404 error for non-existent schedule', async () => {
    const mockError = new Error('Schedule not found');
    mockError.response = { status: 404 };
    schedulerApi.getSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useSchedule('nonexistent'), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

describe('useActiveSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches active schedule successfully', async () => {
    const mockActiveSchedule = {
      active_schedule: {
        id: 'schedule_1',
        name: 'Evening Moths',
        activated_at: '2024-12-15T10:00:00Z',
        events: []
      }
    };

    schedulerApi.getActiveSchedule.mockResolvedValue({ data: mockActiveSchedule });

    const { result } = renderHook(() => useActiveSchedule(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockActiveSchedule);
    expect(schedulerApi.getActiveSchedule).toHaveBeenCalledTimes(1);
  });

  it('handles no active schedule (null response)', async () => {
    schedulerApi.getActiveSchedule.mockResolvedValue({ data: { active_schedule: null } });

    const { result } = renderHook(() => useActiveSchedule(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.active_schedule).toBeNull();
  });

  it('handles fetch error', async () => {
    const mockError = new Error('Failed to fetch active schedule');
    schedulerApi.getActiveSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useActiveSchedule(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

describe('useSchedulePreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches preview with default params', async () => {
    const mockPreview = {
      schedule_id: 'schedule_1',
      preview_days: 7,
      executions: [
        {
          event_name: 'evening_capture',
          action: 'take_photo',
          scheduled_time: '2024-12-15T18:30:00Z',
          trigger_info: {}
        }
      ],
      total: 1
    };

    schedulerApi.getSchedulePreview.mockResolvedValue({ data: mockPreview });

    const { result } = renderHook(() => useSchedulePreview('schedule_1'), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPreview);
    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledWith('schedule_1', {});
  });

  it('passes custom params (days, lat, lon, tz)', async () => {
    const mockPreview = {
      schedule_id: 'schedule_1',
      preview_days: 14,
      executions: [],
      total: 0
    };

    const customParams = {
      days: 14,
      lat: 35.9606,
      lon: -83.9207,
      tz: 'America/New_York'
    };

    schedulerApi.getSchedulePreview.mockResolvedValue({ data: mockPreview });

    const { result } = renderHook(
      () => useSchedulePreview('schedule_1', customParams),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledWith('schedule_1', customParams);
  });

  it('does not fetch when id is null', () => {
    schedulerApi.getSchedulePreview.mockResolvedValue({ data: {} });

    const { result } = renderHook(() => useSchedulePreview(null), {
      wrapper: createWrapper()
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(schedulerApi.getSchedulePreview).not.toHaveBeenCalled();
  });

  it('creates separate cache entries for different params', async () => {
    const mockPreview7 = {
      schedule_id: 'schedule_1',
      preview_days: 7,
      executions: [{ event_name: 'capture_7' }],
      total: 1
    };

    const mockPreview14 = {
      schedule_id: 'schedule_1',
      preview_days: 14,
      executions: [{ event_name: 'capture_14' }],
      total: 1
    };

    // First call with 7 days
    schedulerApi.getSchedulePreview.mockResolvedValueOnce({ data: mockPreview7 });
    // Second call with 14 days
    schedulerApi.getSchedulePreview.mockResolvedValueOnce({ data: mockPreview14 });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, staleTime: 60000 } // Long stale time to verify caching
      }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    // Fetch with 7 days
    const { result: result7 } = renderHook(
      () => useSchedulePreview('schedule_1', { days: 7 }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result7.current.isSuccess).toBe(true);
    });

    expect(result7.current.data.preview_days).toBe(7);

    // Fetch with 14 days - should make new API call, not use cached 7-day data
    const { result: result14 } = renderHook(
      () => useSchedulePreview('schedule_1', { days: 14 }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result14.current.isSuccess).toBe(true);
    });

    expect(result14.current.data.preview_days).toBe(14);

    // Verify both API calls were made (different params = different cache entries)
    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledTimes(2);
    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledWith('schedule_1', { days: 7 });
    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledWith('schedule_1', { days: 14 });
  });

  it('accepts separate queryOptions parameter', async () => {
    const mockPreview = {
      schedule_id: 'schedule_1',
      preview_days: 7,
      executions: [],
      total: 0
    };

    schedulerApi.getSchedulePreview.mockResolvedValue({ data: mockPreview });

    // New API: params and queryOptions are separate
    // Test that queryOptions are passed through by using a different staleTime
    const { result } = renderHook(
      () => useSchedulePreview('schedule_1', { days: 7 }, { staleTime: 1000 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify API was called with correct params
    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledWith('schedule_1', { days: 7 });
  });

  it('excludes undefined params from query key to avoid cache misses', async () => {
    const mockPreview = {
      schedule_id: 'schedule_1',
      preview_days: 7,
      executions: [],
      total: 0
    };

    // First call with days only
    schedulerApi.getSchedulePreview.mockResolvedValueOnce({ data: mockPreview });
    // Second call - should use same cache since undefined params are filtered
    schedulerApi.getSchedulePreview.mockResolvedValueOnce({ data: mockPreview });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, staleTime: 60000 }
      }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    // First render with days: 7 only
    const { result: result1 } = renderHook(
      () => useSchedulePreview('schedule_1', { days: 7 }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result1.current.isSuccess).toBe(true);
    });

    // Second render with same days, but explicitly undefined lat/lon
    const { result: result2 } = renderHook(
      () => useSchedulePreview('schedule_1', { days: 7, lat: undefined, lon: undefined }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result2.current.isSuccess).toBe(true);
    });

    // Should only make one API call (cache hit for second render)
    expect(schedulerApi.getSchedulePreview).toHaveBeenCalledTimes(1);
  });
});

describe('useBuiltinSchedules', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches built-in schedules successfully', async () => {
    const mockBuiltinSchedules = {
      schedules: [
        {
          id: 'sunset_moths',
          name: 'Sunset Moths',
          category: 'builtin',
          description: 'Capture moths at dusk',
          events: []
        },
        {
          id: 'hourly_survey',
          name: 'Hourly Survey',
          category: 'builtin',
          description: 'Take photos every hour',
          events: []
        }
      ],
      total: 2
    };

    schedulerApi.listBuiltinSchedules.mockResolvedValue({ data: mockBuiltinSchedules });

    const { result } = renderHook(() => useBuiltinSchedules(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBuiltinSchedules);
    expect(schedulerApi.listBuiltinSchedules).toHaveBeenCalledTimes(1);
  });

  it('handles fetch error', async () => {
    const mockError = new Error('Failed to fetch built-in schedules');
    schedulerApi.listBuiltinSchedules.mockRejectedValue(mockError);

    const { result } = renderHook(() => useBuiltinSchedules(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

// Note: useBuiltinPatterns tests are in useEventPatterns.test.jsx (Issue #222)

describe('useCreateSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates schedule successfully', async () => {
    const newSchedule = {
      name: 'New Survey',
      description: 'Test survey schedule',
      events: [
        {
          name: 'morning_capture',
          action: 'take_photo',
          trigger: { type: 'fixed_time', time: '06:00:00' }
        }
      ]
    };

    const mockResponse = {
      id: 'schedule_123',
      message: 'Schedule created',
      schedule: { ...newSchedule, id: 'schedule_123' }
    };

    schedulerApi.createSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useCreateSchedule(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      result.current.mutate(newSchedule);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.createSchedule).toHaveBeenCalledWith(newSchedule);
  });

  it('invalidates schedules cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.createSchedule.mockResolvedValue({
      data: { id: 'schedule_123', message: 'Created' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateSchedule(), { wrapper });

    result.current.mutate({
      name: 'Test Schedule',
      events: []
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });

  it('handles validation error (400)', async () => {
    const mockError = new Error('Validation failed');
    mockError.response = { status: 400, data: { errors: ['name is required'] } };
    schedulerApi.createSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useCreateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      name: '',
      events: []
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });

  it('returns new schedule with ID', async () => {
    const newSchedule = {
      name: 'Test Schedule',
      events: []
    };

    const mockResponse = {
      id: 'new_schedule_id',
      message: 'Schedule created',
      schedule: { ...newSchedule, id: 'new_schedule_id' }
    };

    schedulerApi.createSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useCreateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate(newSchedule);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data.id).toBe('new_schedule_id');
    expect(result.current.data.data.schedule.id).toBe('new_schedule_id');
  });
});

describe('useUpdateSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('updates schedule successfully', async () => {
    const updates = {
      description: 'Updated description',
      events: []
    };

    const mockResponse = {
      id: 'schedule_1',
      message: 'Schedule updated',
      schedule: { id: 'schedule_1', name: 'Test', ...updates }
    };

    schedulerApi.updateSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useUpdateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      id: 'schedule_1',
      data: updates
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.updateSchedule).toHaveBeenCalledWith('schedule_1', updates);
  });

  it('invalidates both schedule and list caches', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.updateSchedule.mockResolvedValue({
      data: { id: 'schedule_1', message: 'Updated' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useUpdateSchedule(), { wrapper });

    result.current.mutate({
      id: 'schedule_1',
      data: { description: 'Updated' }
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should invalidate both the specific schedule and the list
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules', 'schedule_1'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });

  it('handles 403 for built-in schedules', async () => {
    const mockError = new Error('Cannot modify built-in schedule');
    mockError.response = { status: 403 };
    schedulerApi.updateSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useUpdateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      id: 'sunset_moths',
      data: { description: 'Updated' }
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
    expect(result.current.error.response.status).toBe(403);
  });

  it('handles 404 not found', async () => {
    const mockError = new Error('Schedule not found');
    mockError.response = { status: 404 };
    schedulerApi.updateSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useUpdateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      id: 'nonexistent',
      data: { description: 'Updated' }
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
    expect(result.current.error.response.status).toBe(404);
  });
});

describe('useDeleteSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('deletes schedule successfully', async () => {
    const mockResponse = {
      message: 'Schedule deleted',
      id: 'schedule_1'
    };

    schedulerApi.deleteSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useDeleteSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate('schedule_1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.deleteSchedule).toHaveBeenCalledWith('schedule_1');
  });

  it('invalidates schedules cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.deleteSchedule.mockResolvedValue({
      data: { message: 'Deleted', id: 'schedule_1' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDeleteSchedule(), { wrapper });

    result.current.mutate('schedule_1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should invalidate both the specific schedule and the list
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules', 'schedule_1'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });

  it('handles 403 for built-in schedules', async () => {
    const mockError = new Error('Cannot delete built-in schedule');
    mockError.response = { status: 403 };
    schedulerApi.deleteSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useDeleteSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate('sunset_moths');

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
    expect(result.current.error.response.status).toBe(403);
  });
});

describe('useActivateSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('activates schedule successfully', async () => {
    const mockResponse = {
      message: 'Schedule activated',
      schedule_id: 'schedule_1',
      deployment_created: false
    };

    schedulerApi.activateSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useActivateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ id: 'schedule_1', options: {} });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.activateSchedule).toHaveBeenCalledWith('schedule_1', {});
  });

  it('invalidates active schedule cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.activateSchedule.mockResolvedValue({
      data: { message: 'Activated', schedule_id: 'schedule_1' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useActivateSchedule(), { wrapper });

    result.current.mutate({ id: 'schedule_1', options: {} });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules', 'active'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });

  it('handles 409 conflict error (schedule already active)', async () => {
    const mockError = new Error('Another schedule is already active');
    mockError.response = { status: 409 };
    schedulerApi.activateSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useActivateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ id: 'schedule_1', options: {} });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
    expect(result.current.error.response.status).toBe(409);
  });
});

describe('useDeactivateSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('deactivates current schedule successfully', async () => {
    const mockResponse = {
      message: 'Schedule deactivated',
      schedule_id: 'schedule_1'
    };

    schedulerApi.deactivateSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useDeactivateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.deactivateSchedule).toHaveBeenCalledTimes(1);
  });

  it('invalidates active schedule cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    schedulerApi.deactivateSchedule.mockResolvedValue({
      data: { message: 'Deactivated', schedule_id: 'schedule_1' }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDeactivateSchedule(), { wrapper });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules', 'active'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['schedules'] });
  });
});

describe('useValidateSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('validates schedule successfully', async () => {
    const mockResponse = {
      valid: true,
      errors: [],
      warnings: []
    };

    schedulerApi.validateSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ id: 'schedule_1', data: { name: 'Test Schedule' } });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.validateSchedule).toHaveBeenCalledWith('schedule_1', { name: 'Test Schedule' });
  });

  it('returns validation errors', async () => {
    const mockResponse = {
      valid: false,
      errors: ['Name is required', 'At least one event is required'],
      warnings: ['Solar events require GPS coordinates']
    };

    schedulerApi.validateSchedule.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ id: 'schedule_1', data: {} });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data.valid).toBe(false);
    expect(result.current.data.data.errors).toHaveLength(2);
    expect(result.current.data.data.warnings).toHaveLength(1);
  });

  it('handles API error', async () => {
    const mockError = new Error('Validation service unavailable');
    schedulerApi.validateSchedule.mockRejectedValue(mockError);

    const { result } = renderHook(() => useValidateSchedule(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ id: 'schedule_1', data: { name: 'Test' } });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

// Note: useValidatePattern tests are in useEventPatterns.test.jsx (Issue #222)
