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

const STORAGE_KEY = 'mothbox-filter-presets'
const MAX_PRESETS = 20

/**
 * Generate a unique preset ID
 * Uses timestamp + random suffix for uniqueness
 *
 * @returns {string} Unique preset ID
 */
function generatePresetId() {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 9)
  return `preset_${timestamp}_${random}`
}

/**
 * Load presets from localStorage
 * Handles parsing errors gracefully
 *
 * @returns {Array} Array of preset objects
 */
function loadPresetsFromStorage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const presets = JSON.parse(stored)
      // Validate and filter valid presets
      if (Array.isArray(presets)) {
        return presets.filter(
          (p) =>
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
 * @param {Array} presets - Array of preset objects
 * @returns {{success: boolean, error?: string}} Status object
 */
function savePresetsToStorage(presets) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets))
    return { success: true }
  } catch (e) {
    console.error('Failed to save filter presets to localStorage:', e)
    if (e.name === 'QuotaExceededError') {
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
 * @param {Array} presets - Current presets array
 * @param {string} name - Name to check
 * @param {string} excludeId - Optional preset ID to exclude from check (for rename)
 * @returns {boolean} True if name exists
 */
function presetNameExists(presets, name, excludeId = null) {
  const lowerName = name.toLowerCase().trim()
  return presets.some(
    (p) => p.id !== excludeId && p.name.toLowerCase().trim() === lowerName
  )
}

/**
 * Generate unique name by appending number if needed
 *
 * @param {Array} presets - Current presets array
 * @param {string} baseName - Base name to make unique
 * @param {string} excludeId - Optional preset ID to exclude from check
 * @returns {string} Unique name
 */
function generateUniqueName(presets, baseName, excludeId = null) {
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
 * @param {Array} presets - Presets to sort
 * @returns {Array} Sorted presets
 */
function sortPresets(presets) {
  return [...presets].sort(
    (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
  )
}

/**
 * Main filter presets hook
 *
 * @returns {Object} Preset management functions and state
 */
export function useFilterPresets() {
  const [presets, setPresets] = useState([])
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
   * @param {string} name - Preset name
   * @param {Object} filterState - Complete filter state to save
   * @returns {{preset: Object, success: boolean, error?: string}} Result object with preset and status
   */
  const savePreset = useCallback(
    (name, filterState) => {
      if (!name || typeof name !== 'string' || !name.trim()) {
        throw new Error('Preset name is required')
      }

      if (!filterState || typeof filterState !== 'object') {
        throw new Error('Filter state is required')
      }

      const uniqueName = generateUniqueName(presets, name)

      const newPreset = {
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
   * @param {string} presetId - Preset ID to load
   * @returns {Object|null} Filter state object or null if not found
   */
  const loadPreset = useCallback(
    (presetId) => {
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
   * @param {string} presetId - Preset ID to delete
   * @returns {{success: boolean, error?: string}} Status object
   */
  const deletePreset = useCallback(
    (presetId) => {
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
   * @param {string} presetId - Preset ID to rename
   * @param {string} newName - New preset name
   * @returns {{success: boolean, error?: string}|undefined} Status object, or undefined if no change needed
   */
  const renamePreset = useCallback(
    (presetId, newName) => {
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
