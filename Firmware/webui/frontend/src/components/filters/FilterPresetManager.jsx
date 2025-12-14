import { useState } from 'react'
import PropTypes from 'prop-types'
import { useFilterPresets } from '../../hooks/useFilterPresets'
import { useFilterContext } from '../../contexts/FilterContext'
import SaveFilterPresetModal from './SaveFilterPresetModal'
import ConfirmDialog from '../common/ConfirmDialog'

/**
 * FilterPresetManager Component
 *
 * Manages filter presets in the filter drawer footer.
 * Displays saved presets and allows users to save, load, and delete them.
 *
 * @component
 * @example
 * <FilterPresetManager />
 */
export function FilterPresetManager() {
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [presetToDelete, setPresetToDelete] = useState(null)

  const {
    presets,
    savePreset,
    loadPreset,
    deletePreset,
    isLoading: isLoadingPresets,
  } = useFilterPresets()

  const {
    dateRange,
    tags,
    species,
    fileTypes,
    cameraSettings,
    notes,
    customFields,
    hasActiveFilters,
    loadState,
  } = useFilterContext()

  /**
   * Handle saving a new preset
   */
  const handleSavePreset = async (presetName) => {
    setIsSaving(true)
    try {
      const filterState = {
        dateRange,
        tags,
        species,
        fileTypes,
        cameraSettings,
        notes,
        customFields,
      }

      savePreset(presetName, filterState)
      setShowSaveModal(false)
    } catch (error) {
      console.error('Error saving preset:', error)
      // In a real app, you might show a toast notification here
      alert(`Failed to save preset: ${error.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  /**
   * Handle loading a preset
   */
  const handleLoadPreset = (presetId) => {
    try {
      const filterState = loadPreset(presetId)
      if (filterState) {
        loadState(filterState)
      }
    } catch (error) {
      console.error('Error loading preset:', error)
      alert(`Failed to load preset: ${error.message}`)
    }
  }

  /**
   * Handle initiating preset deletion (opens confirm dialog)
   */
  const handleDeletePreset = (presetId, e) => {
    e.stopPropagation() // Prevent triggering the load action

    const preset = presets.find((p) => p.id === presetId)
    if (!preset) return

    setPresetToDelete(preset)
    setShowDeleteConfirm(true)
  }

  /**
   * Handle confirming preset deletion
   */
  const handleConfirmDelete = () => {
    if (!presetToDelete) return

    try {
      deletePreset(presetToDelete.id)
    } catch (error) {
      console.error('Error deleting preset:', error)
      alert(`Failed to delete preset: ${error.message}`)
    } finally {
      setShowDeleteConfirm(false)
      setPresetToDelete(null)
    }
  }

  if (isLoadingPresets) {
    return (
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-center">
          <div className="animate-spin h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full" />
          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
            Loading presets...
          </span>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4 space-y-3">
        {/* Presets List */}
        {presets.length > 0 ? (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
              Saved Presets
            </h4>
            <div className="flex flex-wrap gap-2">
              {presets.map((preset) => (
                <div
                  key={preset.id}
                  className="group relative inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-100 dark:bg-indigo-900/30 hover:bg-indigo-200 dark:hover:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-full text-sm font-medium transition-colors cursor-pointer"
                  onClick={() => handleLoadPreset(preset.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleLoadPreset(preset.id)
                    }
                  }}
                  aria-label={`Load preset: ${preset.name}`}
                  title={`Load preset: ${preset.name}`}
                >
                  <span className="truncate max-w-[150px]">{preset.name}</span>
                  <button
                    onClick={(e) => handleDeletePreset(preset.id, e)}
                    className="opacity-0 group-hover:opacity-100 ml-1 text-indigo-600 dark:text-indigo-400 hover:text-red-600 dark:hover:text-red-400 transition-opacity"
                    aria-label={`Delete preset: ${preset.name}`}
                    title="Delete preset"
                  >
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              No saved presets yet
            </p>
          </div>
        )}

        {/* Save Button */}
        <div>
          <button
            onClick={() => setShowSaveModal(true)}
            disabled={!hasActiveFilters}
            className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
            aria-label="Save current filters as preset"
            title={
              hasActiveFilters
                ? 'Save current filters as preset'
                : 'Apply some filters first to save a preset'
            }
          >
            <svg
              className="inline-block w-4 h-4 mr-2 -mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
              />
            </svg>
            Save as Preset
          </button>
          {!hasActiveFilters && (
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-center">
              Apply filters to save a preset
            </p>
          )}
        </div>
      </div>

      {/* Save Modal */}
      <SaveFilterPresetModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSave={handleSavePreset}
        isSaving={isSaving}
      />

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => {
          setShowDeleteConfirm(false)
          setPresetToDelete(null)
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Preset?"
        message={`Are you sure you want to delete "${presetToDelete?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
      />
    </>
  )
}

FilterPresetManager.propTypes = {}

export default FilterPresetManager
