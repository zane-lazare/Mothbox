/**
 * React Query hooks for Export Presets (Issue #125)
 *
 * Provides hooks for managing export presets:
 * - useExportPresets: List all presets (built-in + user) with optional format filter
 * - useExportPreset: Get single preset details
 * - useCreateExportPreset: Create new user preset
 * - useDeleteExportPreset: Delete user preset (built-in presets are protected)
 *
 * Presets are reusable export configurations that store:
 * - Export format (darwin_core, inaturalist, json, csv)
 * - Photo filter criteria (date range, tags, species, etc.)
 * - Format-specific options
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listExportPresets,
  getExportPreset,
  createExportPreset,
  deleteExportPreset,
} from '../utils/exportApi'
import type { ExportPreset } from '../types'

type ExportFormat = 'darwin_core' | 'inaturalist' | 'json' | 'csv'

interface ExportPresetsData {
  presets: ExportPreset[]
  counts: {
    'built-in': number
    user: number
  }
}

interface ExportPresetDetail extends ExportPreset {
  display_name?: string
  category?: string
  filter?: Record<string, unknown>
  options?: Record<string, unknown>
}

interface CreateExportPresetParams {
  name: string
  display_name: string
  export_format: ExportFormat
  description?: string
  filter?: Record<string, unknown>
  options?: Record<string, unknown>
}

/**
 * List all available export presets (built-in + user)
 *
 * @param formatFilter - Filter by export format (darwin_core, inaturalist, json, csv)
 * @returns React Query result
 *
 * @example
 * // Get all presets
 * const { data, isLoading } = useExportPresets()
 * if (data) {
 *   console.log(`Total presets: ${data.presets.length}`)
 *   console.log(`Built-in: ${data.counts['built-in']}, User: ${data.counts.user}`)
 * }
 *
 * @example
 * // Filter by format
 * const { data } = useExportPresets('darwin_core')
 * if (data) {
 *   data.presets.forEach(preset => console.log(preset.display_name))
 * }
 */
export function useExportPresets(formatFilter?: ExportFormat): UseQueryResult<ExportPresetsData, Error> {
  return useQuery({
    queryKey: formatFilter
      ? [...QUERY_KEYS.EXPORT_PRESETS, { format: formatFilter }]
      : QUERY_KEYS.EXPORT_PRESETS,
    queryFn: async () => {
      const response = await listExportPresets(formatFilter)
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - presets don't change often
  })
}

/**
 * Get specific export preset by name
 *
 * @param name - Preset name (without .json extension), null to disable query
 * @returns React Query result
 *
 * @example
 * const { data, isLoading } = useExportPreset('gbif_biodiversity')
 * if (data) {
 *   console.log(`Format: ${data.export_format}`)
 *   console.log(`Filter: ${JSON.stringify(data.filter)}`)
 *   console.log(`Category: ${data.category}`)
 * }
 */
export function useExportPreset(name: string | null): UseQueryResult<ExportPresetDetail, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.EXPORT_PRESET(name!),
    queryFn: async () => {
      const response = await getExportPreset(name!)
      return response.data
    },
    enabled: !!name, // Disable query if name is null/undefined
    staleTime: 5 * 60 * 1000, // 5 minutes - preset details don't change often
  })
}

/**
 * Create new user export preset mutation
 *
 * Invalidates preset list cache on success to show new preset.
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useCreateExportPreset()
 *
 * const handleCreate = () => {
 *   mutate({
 *     name: 'my_preset',
 *     display_name: 'My Preset',
 *     export_format: 'json',
 *     description: 'My custom preset',
 *     filter: {
 *       has_species: true,
 *       tags: ['moth']
 *     },
 *     options: {}
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Preset created:', response.data.name)
 *     },
 *     onError: (error) => {
 *       console.error('Failed:', error.message)
 *     }
 *   })
 * }
 */
export function useCreateExportPreset(): UseMutationResult<unknown, Error, CreateExportPresetParams> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createExportPreset,
    onSuccess: () => {
      // Invalidate preset list to show new preset
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_PRESETS })
    },
  })
}

/**
 * Delete user export preset mutation
 *
 * Built-in presets are protected and cannot be deleted.
 * Invalidates preset cache and preset list on success.
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useDeleteExportPreset()
 *
 * const handleDelete = (presetName) => {
 *   if (confirm(`Delete preset "${presetName}"?`)) {
 *     mutate(presetName, {
 *       onSuccess: () => {
 *         console.log('Preset deleted')
 *       },
 *       onError: (error) => {
 *         if (error.response?.status === 400) {
 *           console.error('Cannot delete built-in preset')
 *         }
 *       }
 *     })
 *   }
 * }
 */
export function useDeleteExportPreset(): UseMutationResult<unknown, Error, string> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (name: string) => deleteExportPreset(name),
    onSuccess: (_response, name) => {
      // Invalidate specific preset cache
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_PRESET(name) })
      // Invalidate preset list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_PRESETS })
    },
  })
}
