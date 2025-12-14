import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useDeployments,
  useDeployment,
  useCreateDeployment,
  useUpdateDeployment,
  useDeleteDeployment
} from '../useDeployments';
import * as deploymentApi from '../../utils/deploymentApi';

// Mock the API module
vi.mock('../../utils/deploymentApi');

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

describe('useDeployments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches deployments list successfully', async () => {
    const mockDeployments = {
      deployments: [
        { directory: '/photos/deployment1', name: 'Oak Ridge Survey' },
        { directory: '/photos/deployment2', name: 'Smoky Mountains Study' }
      ],
      total: 2
    };

    deploymentApi.listDeployments.mockResolvedValue({ data: mockDeployments });

    const { result } = renderHook(() => useDeployments(), {
      wrapper: createWrapper()
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockDeployments);
    expect(deploymentApi.listDeployments).toHaveBeenCalledTimes(1);
  });

  it('handles fetch error', async () => {
    const mockError = new Error('Failed to fetch deployments');
    deploymentApi.listDeployments.mockRejectedValue(mockError);

    const { result } = renderHook(() => useDeployments(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });

  it('returns empty array when no deployments exist', async () => {
    deploymentApi.listDeployments.mockResolvedValue({ data: { deployments: [], total: 0 } });

    const { result } = renderHook(() => useDeployments(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.deployments).toEqual([]);
    expect(result.current.data.total).toBe(0);
  });
});

describe('useDeployment', () => {
  it('fetches single deployment successfully', async () => {
    const mockDeployment = {
      deployment_name: 'Oak Ridge Survey',
      location_name: 'Oak Ridge, TN',
      latitude: 35.9606,
      longitude: -83.9207
    };

    deploymentApi.getDeployment.mockResolvedValue({ data: mockDeployment });

    const { result } = renderHook(() => useDeployment('/photos/deployment1'), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockDeployment);
    expect(deploymentApi.getDeployment).toHaveBeenCalledWith('/photos/deployment1');
  });

  it('does not fetch when directory is null', () => {
    deploymentApi.getDeployment.mockResolvedValue({ data: {} });

    const { result } = renderHook(() => useDeployment(null), {
      wrapper: createWrapper()
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(deploymentApi.getDeployment).not.toHaveBeenCalled();
  });

  it('handles fetch error for single deployment', async () => {
    const mockError = new Error('Deployment not found');
    deploymentApi.getDeployment.mockRejectedValue(mockError);

    const { result } = renderHook(() => useDeployment('/photos/nonexistent'), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

describe('useCreateDeployment', () => {
  it('creates deployment successfully', async () => {
    const newDeployment = {
      deployment_name: 'New Survey',
      location_name: 'Test Location'
    };

    const mockResponse = {
      message: 'Deployment metadata created',
      directory: '/photos/new-deployment'
    };

    deploymentApi.createDeployment.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useCreateDeployment(), {
      wrapper: createWrapper()
    });

    await waitFor(() => {
      result.current.mutate({
        directory: '/photos/new-deployment',
        data: newDeployment
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(deploymentApi.createDeployment).toHaveBeenCalledWith(
      '/photos/new-deployment',
      newDeployment
    );
  });

  it('invalidates deployments cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    deploymentApi.createDeployment.mockResolvedValue({ data: { message: 'Created' } });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateDeployment(), { wrapper });

    result.current.mutate({
      directory: '/photos/test',
      data: { deployment_name: 'Test' }
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['deployments'] });
  });

  it('handles create error', async () => {
    const mockError = new Error('Validation failed');
    deploymentApi.createDeployment.mockRejectedValue(mockError);

    const { result } = renderHook(() => useCreateDeployment(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      directory: '/photos/test',
      data: { deployment_name: '' }
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

describe('useUpdateDeployment', () => {
  it('updates deployment successfully', async () => {
    const updates = {
      end_date: '2024-12-31'
    };

    const mockResponse = {
      message: 'Deployment metadata updated',
      directory: '/photos/deployment1'
    };

    deploymentApi.updateDeployment.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useUpdateDeployment(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      directory: '/photos/deployment1',
      data: updates
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(deploymentApi.updateDeployment).toHaveBeenCalledWith(
      '/photos/deployment1',
      updates
    );
  });

  it('invalidates deployment cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    deploymentApi.updateDeployment.mockResolvedValue({ data: { message: 'Updated' } });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useUpdateDeployment(), { wrapper });

    result.current.mutate({
      directory: '/photos/test',
      data: { end_date: '2024-12-31' }
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should invalidate both the specific deployment and the list
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['deployment', '/photos/test'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['deployments'] });
  });

  it('handles update error', async () => {
    const mockError = new Error('Update failed');
    deploymentApi.updateDeployment.mockRejectedValue(mockError);

    const { result } = renderHook(() => useUpdateDeployment(), {
      wrapper: createWrapper()
    });

    result.current.mutate({
      directory: '/photos/test',
      data: { end_date: '2024-12-31' }
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});

describe('useDeleteDeployment', () => {
  it('deletes deployment successfully', async () => {
    const mockResponse = {
      message: 'Deployment metadata deleted',
      directory: '/photos/deployment1'
    };

    deploymentApi.deleteDeployment.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useDeleteDeployment(), {
      wrapper: createWrapper()
    });

    result.current.mutate('/photos/deployment1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.data).toEqual(mockResponse);
    expect(deploymentApi.deleteDeployment).toHaveBeenCalledWith('/photos/deployment1');
  });

  it('invalidates caches on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    deploymentApi.deleteDeployment.mockResolvedValue({ data: { message: 'Deleted' } });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDeleteDeployment(), { wrapper });

    result.current.mutate('/photos/test');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['deployment', '/photos/test'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['deployments'] });
  });

  it('handles delete error', async () => {
    const mockError = new Error('Delete failed');
    deploymentApi.deleteDeployment.mockRejectedValue(mockError);

    const { result } = renderHook(() => useDeleteDeployment(), {
      wrapper: createWrapper()
    });

    result.current.mutate('/photos/test');

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(mockError);
  });
});
