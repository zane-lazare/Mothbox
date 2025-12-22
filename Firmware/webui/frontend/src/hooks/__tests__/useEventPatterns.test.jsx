/**
 * Tests for useEventPatterns hooks (Issue #222)
 *
 * Comprehensive test suite following TDD approach - tests written BEFORE implementation.
 * Tests React Query hooks for Event Pattern operations.
 *
 * Reference: useSchedules.test.jsx for testing patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useBuiltinPatterns,
  useValidatePattern,
  usePatternDuration,
} from '../useEventPatterns';
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
// useBuiltinPatterns Tests
// =============================================================================

describe('useBuiltinPatterns', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches built-in patterns successfully', async () => {
    const mockBuiltinPatterns = {
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

    schedulerApi.listBuiltinPatterns.mockResolvedValue({ data: mockBuiltinPatterns });

    const { result } = renderHook(() => useBuiltinPatterns(), {
      wrapper: createWrapper()
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBuiltinPatterns);
    expect(schedulerApi.listBuiltinPatterns).toHaveBeenCalledTimes(1);
  });

  it('handles empty patterns list', async () => {
    schedulerApi.listBuiltinPatterns.mockResolvedValue({
      data: { patterns: [], total: 0 }
    });

    const { result } = renderHook(() => useBuiltinPatterns(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.patterns).toEqual([]);
    expect(result.current.data.total).toBe(0);
  });

  it('handles fetch error', async () => {
    const mockError = new Error('Failed to fetch built-in patterns');
    schedulerApi.listBuiltinPatterns.mockRejectedValue(mockError);

    const { result } = renderHook(() => useBuiltinPatterns(), {
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

    schedulerApi.listBuiltinPatterns.mockResolvedValue({
      data: { patterns: [], total: 0 }
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useBuiltinPatterns(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify the correct query key is used in the cache
    const cachedQueries = queryClient.getQueryCache().findAll({
      queryKey: QUERY_KEYS.BUILTIN_PATTERNS
    });
    expect(cachedQueries).toHaveLength(1);
    expect(cachedQueries[0].queryKey).toEqual(QUERY_KEYS.BUILTIN_PATTERNS);
  });

  it('accepts custom queryOptions', async () => {
    schedulerApi.listBuiltinPatterns.mockResolvedValue({
      data: { patterns: [], total: 0 }
    });

    // Test that queryOptions are passed through
    const { result } = renderHook(
      () => useBuiltinPatterns({ staleTime: 1000 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(schedulerApi.listBuiltinPatterns).toHaveBeenCalledTimes(1);
  });
});

// =============================================================================
// useValidatePattern Tests
// =============================================================================

describe('useValidatePattern', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('validates pattern successfully', async () => {
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

    schedulerApi.validatePattern.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidatePattern(), {
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
    expect(schedulerApi.validatePattern).toHaveBeenCalledWith({
      name: 'Test Pattern',
      description: 'A test pattern',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 0 }
      ]
    });
  });

  it('returns validation errors for invalid pattern', async () => {
    const mockResponse = {
      valid: false,
      error: 'Pattern name is required'
    };

    schedulerApi.validatePattern.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidatePattern(), {
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
    schedulerApi.validatePattern.mockRejectedValue(mockError);

    const { result } = renderHook(() => useValidatePattern(), {
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

    schedulerApi.validatePattern.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useValidatePattern(), {
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
// usePatternDuration Tests
// =============================================================================

describe('usePatternDuration', () => {
  it('returns 0 for null pattern', () => {
    const { result } = renderHook(() => usePatternDuration(null), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(0);
  });

  it('returns 0 for undefined pattern', () => {
    const { result } = renderHook(() => usePatternDuration(undefined), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(0);
  });

  it('returns 0 for pattern with no actions property', () => {
    const { result } = renderHook(() => usePatternDuration({ name: 'test' }), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(0);
  });

  it('returns 0 for pattern with empty actions array', () => {
    const { result } = renderHook(
      () => usePatternDuration({ name: 'test', actions: [] }),
      { wrapper: createWrapper() }
    );

    expect(result.current).toBe(0);
  });

  it('calculates duration from single action', () => {
    const pattern = {
      name: 'Single Action',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10 }
      ]
    };

    const { result } = renderHook(() => usePatternDuration(pattern), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(10);
  });

  it('calculates max offset from multiple actions', () => {
    const pattern = {
      name: 'UV Capture Cycle',
      actions: [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
        { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
      ]
    };

    const { result } = renderHook(() => usePatternDuration(pattern), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(15);
  });

  it('handles undefined offset_minutes (defaults to 0)', () => {
    const pattern = {
      name: 'Missing Offset',
      actions: [
        { action_type: 'camera', action_name: 'takephoto' },
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 5 }
      ]
    };

    const { result } = renderHook(() => usePatternDuration(pattern), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(5);
  });

  it('memoizes result correctly - same pattern returns same value', () => {
    const pattern = {
      name: 'Test Pattern',
      actions: [
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10 }
      ]
    };

    const { result, rerender } = renderHook(
      ({ pattern }) => usePatternDuration(pattern),
      { wrapper: createWrapper(), initialProps: { pattern } }
    );

    const firstResult = result.current;

    // Rerender with same pattern object
    rerender({ pattern });

    expect(result.current).toBe(firstResult);
    expect(result.current).toBe(10);
  });

  it('handles decimal offset_minutes values', () => {
    const pattern = {
      name: 'Decimal Offsets',
      actions: [
        { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 5.5 },
        { action_type: 'camera', action_name: 'takephoto', offset_minutes: 10.3 },
        { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 7.8 }
      ]
    };

    const { result } = renderHook(() => usePatternDuration(pattern), {
      wrapper: createWrapper()
    });

    expect(result.current).toBe(10.3);
  });
});
