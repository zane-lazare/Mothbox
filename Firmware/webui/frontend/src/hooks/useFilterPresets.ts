/**
 * useFilterPresets Hook
 *
 * Provides a convenient API for managing saved filter presets via localStorage.
 * Enables users to save, load, rename, and delete filter configurations for
 * quick access to frequently used filter combinations.
 *
 * Features:
 * - Persistent storage via localStorage
 * - Automatic unique ID generation
 * - Duplicate name handling with auto-numbering
 * - Max 20 presets with automatic cleanup
 * - Sort presets by creation date (newest first)
 *
 * @module useFilterPresets
 */

import { useState, useCallback, useEffect } from 'react'
import type { FilterState } from '../types'

const STORAGE_KEY = 'mothbox-filter-presets'
const MAX_PRESETS = 20

interface FilterPreset {
  id: string
  name: string
  filters: Partial<FilterState>
  createdAt: string
}

interface SaveResult {
  preset: FilterPreset
  success: boolean
  error?: string
}

interface OperationResult {
  success: boolean
  error?: string
}

/**
 * Generate a unique preset ID
 * Uses timestamp + random suffix for uniqueness
 *
 * @returns Unique preset ID
 */
function generatePresetId(): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 9)
  return `preset_${timestamp}_${random}`
}

/**
 * Load presets from localStorage
 * Handles parsing errors gracefully
 *
 * @returns Array of preset objects
 */
function loadPresetsFromStorage(): FilterPreset[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const presets = JSON.parse(stored)
      // Validate and filter valid presets
      if (Array.isArray(presets)) {
        return presets.filter(
          (p): p is FilterPreset =>
            p &&
            typeof p === 'object' &&
            p.id &&
            p.name &&
            p.filters &&
            p.createdAt
        )
      }
    }
  } catch (e) {
    console.warn('Failed to load filter presets from localStorage:', e)
  }
  return []
}

/**
 * Save presets to localStorage
 * Handles storage errors gracefully and returns status
 *
 * @param presets - Array of preset objects
 * @returns Status object
 */
function savePresetsToStorage(presets: FilterPreset[]): OperationResult {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets))
    return { success: true }
  } catch (e) {
    console.error('Failed to save filter presets to localStorage:', e)
    if (e instanceof Error && e.name === 'QuotaExceededError') {
      return {
        success: false,
        error: 'Storage quota exceeded. Please delete old presets.',
      }
    }
    return { success: false, error: 'Failed to save preset' }
  }
}

/**
 * Check if preset name already exists (case-insensitive)
 *
 * @param presets - Current presets array
 * @param name - Name to check
 * @param excludeId - Optional preset ID to exclude from check (for rename)
 * @returns True if name exists
 */
function presetNameExists(
  presets: FilterPreset[],
  name: string,
  excludeId: string | null = null
): boolean {
  const lowerName = name.toLowerCase().trim()
  return presets.some(
    (p) => p.id !== excludeId && p.name.toLowerCase().trim() === lowerName
  )
}

/**
 * Generate unique name by appending number if needed
 *
 * @param presets - Current presets array
 * @param baseName - Base name to make unique
 * @param excludeId - Optional preset ID to exclude from check
 * @returns Unique name
 */
function generateUniqueName(
  presets: FilterPreset[],
  baseName: string,
  excludeId: string | null = null
): string {
  let name = baseName.trim()
  let counter = 2

  while (presetNameExists(presets, name, excludeId)) {
    name = `${baseName.trim()} (${counter})`
    counter++
  }

  return name
}

/**
 * Sort presets by creation date (newest first)
 *
 * @param presets - Presets to sort
 * @returns Sorted presets
 */
function sortPresets(presets: FilterPreset[]): FilterPreset[] {
  return [...presets].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  )
}

interface UseFilterPresetsResult {
  presets: FilterPreset[]
  savePreset: (name: string, filterState: Partial<FilterState>) => SaveResult
  loadPreset: (presetId: string) => Partial<FilterState> | null
  deletePreset: (presetId: string) => OperationResult
  renamePreset: (presetId: string, newName: string) => OperationResult
  isLoading: boolean
}

/**
 * Main filter presets hook
 *
 * @returns Preset management functions and state
 */
export function useFilterPresets(): UseFilterPresetsResult {
  const [presets, setPresets] = useState<FilterPreset[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Load presets on mount
  useEffect(() => {
    const loaded = loadPresetsFromStorage()
    setPresets(sortPresets(loaded))
    setIsLoading(false)
  }, [])

  /**
   * Save a new filter preset
   *
   * @param name - Preset name
   * @param filterState - Complete filter state to save
   * @returns Result object with preset and status
   */
  const savePreset = useCallback(
    (name: string, filterState: Partial<FilterState>): SaveResult => {
      if (!name || typeof name !== 'string' || !name.trim()) {
        throw new Error('Preset name is required')
      }

      if (!filterState || typeof filterState !== 'object') {
        throw new Error('Filter state is required')
      }

      const uniqueName = generateUniqueName(presets, name)

      const newPreset: FilterPreset = {
        id: generatePresetId(),
        name: uniqueName,
        filters: filterState,
        createdAt: new Date().toISOString(),
      }

      let updatedPresets = [...presets, newPreset]

      // Enforce max presets limit (remove oldest)
      if (updatedPresets.length > MAX_PRESETS) {
        const sorted = sortPresets(updatedPresets)
        updatedPresets = sorted.slice(0, MAX_PRESETS)
      } else {
        updatedPresets = sortPresets(updatedPresets)
      }

      setPresets(updatedPresets)
      const result = savePresetsToStorage(updatedPresets)

      return { preset: newPreset, ...result }
    },
    [presets]
  )

  /**
   * Load a preset by ID
   *
   * @param presetId - Preset ID to load
   * @returns Filter state object or null if not found
   */
  const loadPreset = useCallback(
    (presetId: string): Partial<FilterState> | null => {
      if (!presetId || typeof presetId !== 'string') {
        throw new Error('Preset ID is required')
      }

      const preset = presets.find((p) => p.id === presetId)

      if (!preset) {
        return null
      }

      return preset.filters
    },
    [presets]
  )

  /**
   * Delete a preset by ID
   *
   * @param presetId - Preset ID to delete
   * @returns Status object
   */
  const deletePreset = useCallback(
    (presetId: string): OperationResult => {
      if (!presetId || typeof presetId !== 'string') {
        throw new Error('Preset ID is required')
      }

      const updatedPresets = presets.filter((p) => p.id !== presetId)
      setPresets(updatedPresets)
      return savePresetsToStorage(updatedPresets)
    },
    [presets]
  )

  /**
   * Rename a preset
   *
   * @param presetId - Preset ID to rename
   * @param newName - New preset name
   * @returns Status object
   */
  const renamePreset = useCallback(
    (presetId: string, newName: string): OperationResult => {
      if (!presetId || typeof presetId !== 'string') {
        throw new Error('Preset ID is required')
      }

      if (!newName || typeof newName !== 'string' || !newName.trim()) {
        throw new Error('New preset name is required')
      }

      const presetIndex = presets.findIndex((p) => p.id === presetId)

      if (presetIndex === -1) {
        throw new Error('Preset not found')
      }

      // Check if new name is different from current name
      const currentName = presets[presetIndex].name
      if (currentName.toLowerCase().trim() === newName.toLowerCase().trim()) {
        // No change needed
        return { success: true }
      }

      // Generate unique name if needed (excluding current preset)
      const uniqueName = presetNameExists(presets, newName, presetId)
        ? generateUniqueName(presets, newName, presetId)
        : newName.trim()

      const updatedPresets = [...presets]
      updatedPresets[presetIndex] = {
        ...updatedPresets[presetIndex],
        name: uniqueName,
      }

      setPresets(updatedPresets)
      return savePresetsToStorage(updatedPresets)
    },
    [presets]
  )

  return {
    presets,
    savePreset,
    loadPreset,
    deletePreset,
    renamePreset,
    isLoading,
  }
}
