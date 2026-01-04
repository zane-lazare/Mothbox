/**
 * Tests for useRoutines hooks (Issue #222, #322)
 *
 * Comprehensive test suite following TDD approach - tests written BEFORE implementation.
 * Tests React Query hooks for Routine operations.
 *
 * Reference: useSchedules.test.jsx for testing patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useBuiltinRoutines,
  useValidateRoutine,
  useRoutineDuration,
} from '../useRoutines';
import * as schedulerApi from '../../utils/schedulerApi';
import { QUERY_KEYS } from '../../utils/queryKeys';

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
// useBuiltinRoutines Tests
// =============================================================================

describe('useBuiltinRoutines', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches built-in routines successfully', async () => {
    const mockBuiltinRoutines = {
      patterns: [
        {
          pattern_id: 'uv-capture-cycle',
          name: 'UV Capture Cycle',
          category: 'built-in',
          description: 'Turn on UV, capture photo, turn off',
          actions: [
            { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
            { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
            { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
          ],
          duration_minutes: 15
        },
        {
          pattern_id: 'flash-capture',
          name: 'Flash Capture',
          category: 'built-in',
          description: 'Use flash for capture',
          actions: [
            { action_type: 'gpio', action_name: 'flash_on', offset_minutes: 0 },
            { action_type: 'camera', action_name: 'takephoto', offset_minutes: 1 },
            { action_type: 'gpio', action_name: 'flash_off', offset_minutes: 2 }
          ],
          duration_minutes: 2
        }
      ],
      total: 2
    };

    schedulerApi.listBuiltinRoutines.mockResolvedValue({ data: mockBuiltinRoutines });

    const { result } = renderHook(() => useBuiltinRoutines(), {
      wrapper: createWrapper()
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBuiltinRoutines);
    expect(schedulerApi.listBuiltinRoutines).toHaveBeenCalledTimes(1);
  });

  it('handles empty routines list', async () => {
    schedulerApi.listBuiltinRoutines.mockResolvedValue({
      data: { patterns: [], total: 0 }
    });

    const { result } = renderHook(() => useBuiltinRoutines(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.patterns).toEqual([]);
    expect(result.current.data.total).toBe(0);
  });

  it('handles fetch error', async () => {
    const mockError = new Error('Failed to fetch built-in routines');
    schedulerApi.listBuiltinRoutines.mockRejectedValue(mockError);

    const { result } = renderHook(() => useBuiltinRoutines(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });

  it('uses correct query key', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    schedulerApi.listBuiltinRoutines.mockResolvedValue({
      data: { patterns: [], total: 0 }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useBuiltinRoutines(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify the correct query key is used in the cache
    const cachedQueries = queryClient.getQueryCache().findAll({
      queryKey: QUERY_KEYS.BUILTIN_ROUTINES
    });
    expect(cachedQueries).toHaveLength(1);
    expect(cachedQueries[0].queryKey).toEqual(QUERY_KEYS.BUILTIN_ROUTINES);
  });

  it('accepts custom queryOptions', async () => {
    schedulerApi.listBuiltinRoutines.mockResolvedValue({
      data: { patterns: [], total: 0 }
    });

    // Test that queryOptions are passed through
    const { result } = renderHook(
      () => useBuiltinRoutines({ staleTime: 1000 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(schedulerApi.listBuiltinRoutines).toHaveBeenCalledTimes(1);
  });
});

// =============================================================================
// useValidateRoutine Tests
// =============================================================================

describe('useValidateRoutine', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('validates routine successfully', async () => {
    const mockResponse = {
      valid: true,
      pattern: {
        pattern_id: 'test-pattern',
        name: 'Test Pattern',
        description: 'A test pattern',
        actions: [
          { action_type: 'camera', action_name: 'takephoto', offset_minutes: 0 }
        ],
        category: 'user',
        duration_minutes: 0
      }
    };

    schedulerApi.validateRoutine.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidateRoutine(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      name: 'Test Pattern',
      description: 'A test pattern',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 0 }
      ]
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(schedulerApi.validateRoutine).toHaveBeenCalledWith({
      name: 'Test Pattern',
      description: 'A test pattern',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 0 }
      ]
    });
  });

  it('returns validation errors for invalid routine', async () => {
    const mockResponse = {
      valid: false,
      error: 'Pattern name is required'
    };

    schedulerApi.validateRoutine.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidateRoutine(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      name: '',
      actions: []
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data.valid).toBe(false);
    expect(result.current.data.data.error).toBe('Pattern name is required');
  });

  it('handles API error', async () => {
    const mockError = new Error('Pattern validation failed');
    schedulerApi.validateRoutine.mockRejectedValue(mockError);

    const { result } = renderHook(() => useValidateRoutine(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ name: 'test', actions: [] });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });

  it('handles missing required fields in response', async () => {
    const mockResponse = {
      valid: false,
      error: 'Missing required field: name'
    };

    schedulerApi.validateRoutine.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidateRoutine(), {
      wrapper: createWrapper()
    });

    result.current.mutate({ actions: [] });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data.valid).toBe(false);
  });
});

// =============================================================================
// useRoutineDuration Tests
// =============================================================================

describe('useRoutineDuration', () => {
  it('returns 0 for null routine', () => {
    const { result } = renderHook(() => useRoutineDuration(null), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(0);
  });

  it('returns 0 for undefined routine', () => {
    const { result } = renderHook(() => useRoutineDuration(undefined), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(0);
  });

  it('returns 0 for routine with no actions property', () => {
    const { result } = renderHook(() => useRoutineDuration({ name: 'test' }), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(0);
  });

  it('returns 0 for routine with empty actions array', () => {
    const { result } = renderHook(
      () => useRoutineDuration({ name: 'test', actions: [] }),
      { wrapper: createWrapper() }
    );

    expect(result.current).toBe(0);
  });

  it('calculates duration from single action', () => {
    const routine = {
      name: 'Single Action',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10 }
      ]
    };

    const { result } = renderHook(() => useRoutineDuration(routine), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(10);
  });

  it('calculates max offset from multiple actions', () => {
    const routine = {
      name: 'UV Capture Cycle',
      actions: [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
        { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
      ]
    };

    const { result } = renderHook(() => useRoutineDuration(routine), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(15);
  });

  it('handles undefined offset_minutes (defaults to 0)', () => {
    const routine = {
      name: 'Missing Offset',
      actions: [
        { action_type: 'camera', action_name: 'takephoto' },
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 5 }
      ]
    };

    const { result } = renderHook(() => useRoutineDuration(routine), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(5);
  });

  it('memoizes result correctly - same routine returns same value', () => {
    const routine = {
      name: 'Test Pattern',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10 }
      ]
    };

    const { result, rerender } = renderHook(
      ({ routine }) => useRoutineDuration(routine),
      { wrapper: createWrapper(), initialProps: { routine } }
    );

    const firstResult = result.current;

    // Rerender with same routine object
    rerender({ routine });

    expect(result.current).toBe(firstResult);
    expect(result.current).toBe(10);
  });

  it('handles decimal offset_minutes values', () => {
    const routine = {
      name: 'Decimal Offsets',
      actions: [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 5.5 },
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10.3 },
        { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 7.8 }
      ]
    };

    const { result } = renderHook(() => useRoutineDuration(routine), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(10.3);
  });
});
