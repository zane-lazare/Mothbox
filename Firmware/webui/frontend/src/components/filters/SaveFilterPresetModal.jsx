import { useState } from 'react'
import PropTypes from 'prop-types'
import { Z_INDEX } from '../../constants/config'

/**
 * SaveFilterPresetModal Component
 *
 * Modal dialog for saving current filter state as a named preset.
 * Handles input validation and provides feedback to the user.
 *
 * @component
 * @example
 * <SaveFilterPresetModal
 *   isOpen={showModal}
 *   onClose={() => setShowModal(false)}
 *   onSave={handleSave}
 *   isSaving={false}
 * />
 */
export function SaveFilterPresetModal({ isOpen, onClose, onSave, isSaving = false }) {
  const [presetName, setPresetName] = useState('')
  const [nameError, setNameError] = useState('')

  if (!isOpen) return null

  const validateName = (name) => {
    if (!name || !name.trim()) {
      return 'Preset name is required'
    }
    if (name.trim().length < 3) {
      return 'Name must be at least 3 characters'
    }
    if (name.trim().length > 50) {
      return 'Name must be less than 50 characters'
    }
    return ''
  }

  const handleNameChange = (e) => {
    const name = e.target.value
    setPresetName(name)
    setNameError(validateName(name))
  }

  const handleSave = async () => {
    const error = validateName(presetName)
    if (error) {
      setNameError(error)
      return
    }

    try {
      await onSave(presetName.trim())
      // Reset form on success
      setPresetName('')
      setNameError('')
      onClose()
    } catch (error) {
      // Error is handled by parent component
      console.error('Error saving preset:', error)
    }
  }

  const handleClose = () => {
    setPresetName('')
    setNameError('')
    onClose()
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      handleClose()
    }
  }

  return (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} overflow-y-auto`}>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div
          className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          {/* Header */}
          <div className="mb-4">
            <h3
              id="modal-title"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              Save Filter Preset
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Save your current filter settings for quick access later
            </p>
          </div>

          {/* Form */}
          <div className="space-y-4">
            {/* Name Input */}
            <div>
              <label
                htmlFor="preset-name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Preset Name <span className="text-red-500">*</span>
              </label>
              <input
                id="preset-name"
                type="text"
                value={presetName}
                onChange={handleNameChange}
                onKeyDown={handleKeyPress}
                placeholder="e.g., Moths from June 2024"
                disabled={isSaving}
                autoFocus
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white dark:border-gray-600 ${
                  nameError ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                } disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed`}
              />
              {nameError && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
                  {nameError}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Choose a descriptive name for this filter combination
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSaving}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !!nameError || !presetName.trim()}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {isSaving ? (
                <>
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Saving...
                </>
              ) : (
                'Save Preset'
              )}
            </button>
          </div>

          {/* Info */}
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs text-blue-800 dark:text-blue-300">
              <span className="font-semibold">ℹ️ Note:</span> This will save your current filter
              settings. You can load this preset later to quickly apply these filters.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

SaveFilterPresetModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  isSaving: PropTypes.bool,
}

export default SaveFilterPresetModal
