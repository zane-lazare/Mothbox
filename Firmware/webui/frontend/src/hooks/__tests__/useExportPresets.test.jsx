import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  useExportPresets,
  useExportPreset,
  useCreateExportPreset,
  useDeleteExportPreset,
} from '../useExportPresets'
import * as exportApi from '../../utils/exportApi'

// Create wrapper for react-query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useExportPresets', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches export presets list successfully', async () => {
    const mockPresets = {
      presets: [
        {
          name: 'gbif_biodiversity',
          display_name: 'GBIF Biodiversity',
          export_format: 'darwin_core',
          category: 'built-in',
        },
        {
          name: 'my_preset',
          display_name: 'My Preset',
          export_format: 'json',
          category: 'user',
        },
      ],
      counts: {
        'built-in': 6,
        user: 1,
      },
    }

    vi.spyOn(exportApi, 'listExportPresets').mockResolvedValue({ data: mockPresets })

    const { result } = renderHook(() => useExportPresets(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockPresets)
    expect(exportApi.listExportPresets).toHaveBeenCalledWith(undefined)
  })

  it('filters presets by format', async () => {
    const mockPresets = {
      presets: [
        {
          name: 'gbif_biodiversity',
          display_name: 'GBIF Biodiversity',
          export_format: 'darwin_core',
          category: 'built-in',
        },
      ],
      counts: {
        'built-in': 1,
        user: 0,
      },
    }

    vi.spyOn(exportApi, 'listExportPresets').mockResolvedValue({ data: mockPresets })

    const { result } = renderHook(() => useExportPresets('darwin_core'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockPresets)
    expect(exportApi.listExportPresets).toHaveBeenCalledWith('darwin_core')
  })

  it('handles empty preset list', async () => {
    const mockPresets = {
      presets: [],
      counts: {
        'built-in': 0,
        user: 0,
      },
    }

    vi.spyOn(exportApi, 'listExportPresets').mockResolvedValue({ data: mockPresets })

    const { result } = renderHook(() => useExportPresets(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data.presets).toHaveLength(0)
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Network error')
    vi.spyOn(exportApi, 'listExportPresets').mockRejectedValue(mockError)

    const { result } = renderHook(() => useExportPresets(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useExportPreset', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches single preset successfully', async () => {
    const mockPreset = {
      name: 'gbif_biodiversity',
      display_name: 'GBIF Biodiversity',
      export_format: 'darwin_core',
      description: 'Export for GBIF submission',
      category: 'built-in',
      filter: {
        has_species: true,
      },
      options: {},
    }

    vi.spyOn(exportApi, 'getExportPreset').mockResolvedValue({ data: mockPreset })

    const { result } = renderHook(() => useExportPreset('gbif_biodiversity'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockPreset)
    expect(exportApi.getExportPreset).toHaveBeenCalledWith('gbif_biodiversity')
  })

  it('is disabled when name is null', () => {
    const { result } = renderHook(() => useExportPreset(null), {
      wrapper: createWrapper(),
    })

    expect(result.current.data).toBeUndefined()
    expect(result.current.isLoading).toBe(false)
  })

  it('handles preset not found error', async () => {
    const mockError = new Error('Preset not found')
    vi.spyOn(exportApi, 'getExportPreset').mockRejectedValue(mockError)

    const { result } = renderHook(() => useExportPreset('nonexistent'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Network error')
    vi.spyOn(exportApi, 'getExportPreset').mockRejectedValue(mockError)

    const { result } = renderHook(() => useExportPreset('gbif_biodiversity'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useCreateExportPreset', () => {
  let queryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates export preset successfully', async () => {
    const mockPresetData = {
      name: 'my_preset',
      display_name: 'My Preset',
      export_format: 'json',
      description: 'My custom preset',
      filter: {
        has_species: true,
      },
      options: {},
    }

    const mockResponse = {
      success: true,
      message: 'Preset created',
      name: 'my_preset',
    }

    vi.spyOn(exportApi, 'createExportPreset').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCreateExportPreset(), { wrapper })

    result.current.mutate(mockPresetData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(exportApi.createExportPreset).toHaveBeenCalled()
    expect(exportApi.createExportPreset.mock.calls[0][0]).toEqual(mockPresetData)
    expect(result.current.data.data).toEqual(mockResponse)
  })

  it('invalidates preset list cache on success', async () => {
    const mockPresetData = {
      name: 'my_preset',
      display_name: 'My Preset',
      export_format: 'json',
    }

    const mockResponse = {
      success: true,
      message: 'Preset created',
      name: 'my_preset',
    }

    vi.spyOn(exportApi, 'createExportPreset').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateExportPreset(), { wrapper })

    result.current.mutate(mockPresetData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-presets'],
    })
  })

  it('handles validation errors', async () => {
    const mockError = new Error('Preset name is required')
    vi.spyOn(exportApi, 'createExportPreset').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCreateExportPreset(), { wrapper })

    result.current.mutate({ export_format: 'json' })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })

  it('handles duplicate preset name error', async () => {
    const mockError = new Error('Preset already exists')
    vi.spyOn(exportApi, 'createExportPreset').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCreateExportPreset(), { wrapper })

    result.current.mutate({
      name: 'my_preset',
      display_name: 'My Preset',
      export_format: 'json',
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useDeleteExportPreset', () => {
  let queryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deletes export preset successfully', async () => {
    const mockResponse = {
      success: true,
      message: 'Preset deleted',
    }

    vi.spyOn(exportApi, 'deleteExportPreset').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDeleteExportPreset(), { wrapper })

    result.current.mutate('my_preset')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(exportApi.deleteExportPreset).toHaveBeenCalledWith('my_preset')
    expect(result.current.data.data).toEqual(mockResponse)
  })

  it('invalidates preset and preset list cache on success', async () => {
    const mockResponse = {
      success: true,
      message: 'Preset deleted',
    }

    vi.spyOn(exportApi, 'deleteExportPreset').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useDeleteExportPreset(), { wrapper })

    result.current.mutate('my_preset')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-presets', 'my_preset'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-presets'],
    })
  })

  it('handles delete of built-in preset error', async () => {
    const mockError = new Error('Cannot delete built-in preset')
    vi.spyOn(exportApi, 'deleteExportPreset').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDeleteExportPreset(), { wrapper })

    result.current.mutate('gbif_biodiversity')

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })

  it('handles preset not found error', async () => {
    const mockError = new Error('Preset not found')
    vi.spyOn(exportApi, 'deleteExportPreset').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDeleteExportPreset(), { wrapper })

    result.current.mutate('nonexistent')

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})
