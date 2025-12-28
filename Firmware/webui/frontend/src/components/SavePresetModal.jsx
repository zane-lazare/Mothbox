import { useState, useEffect } from 'react'
import { Z_INDEX } from '../constants/config'
import { validatePresetSettings } from '../utils/presetValidation'

export default function SavePresetModal({ isOpen, onClose, onSave, isSaving, defaultWorkflow = 'both', currentSettings = {} }) {
  const [presetName, setPresetName] = useState('')
  const [description, setDescription] = useState('')
  const [workflow, setWorkflow] = useState(defaultWorkflow)
  const [nameError, setNameError] = useState('')
  const [validationErrors, setValidationErrors] = useState([])

  // Clear stale validation errors when modal opens
  useEffect(() => {
    if (isOpen) {
      setValidationErrors([])
    }
  }, [isOpen])

  if (!isOpen) return null

  const validateName = (name) => {
    if (!name) {
      return 'Preset name is required'
    }
    if (!/^[a-zA-Z0-9_]+$/.test(name)) {
      return 'Name can only contain letters, numbers, and underscores'
    }
    if (name.length < 3) {
      return 'Name must be at least 3 characters'
    }
    if (name.length > 50) {
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
    // Validate preset name
    const error = validateName(presetName)
    if (error) {
      setNameError(error)
      return
    }

    // Validate settings values
    const settingsErrors = validatePresetSettings(currentSettings)
    if (settingsErrors.length > 0) {
      setValidationErrors(settingsErrors)
      return
    }

    const presetData = {
      name: presetName,
      description: description.trim(),
      workflow: workflow,
      from_current: true
    }

    try {
      await onSave(presetData)
      // Reset form on success
      setPresetName('')
      setDescription('')
      setWorkflow(defaultWorkflow)
      setNameError('')
      setValidationErrors([])
    } catch (error) {
      // Error is handled by the mutation in parent component
      console.error('Error saving preset:', error)
    }
  }

  const handleClose = () => {
    setPresetName('')
    setDescription('')
    setWorkflow(defaultWorkflow)
    setNameError('')
    setValidationErrors([])
    onClose()
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSave()
    }
  }

  return (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} overflow-y-auto`}>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all">
          {/* Header */}
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <span className="mr-2">💾</span>
              Save Current Settings as Preset
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Create a reusable preset from your current camera and live view settings
            </p>
          </div>

          {/* Form */}
          <div className="space-y-4">
            {/* Name Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Preset Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={presetName}
                onChange={handleNameChange}
                onKeyPress={handleKeyPress}
                placeholder="e.g., my_field_setup"
                disabled={isSaving}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  nameError ? 'border-red-500' : 'border-gray-300'
                } disabled:bg-gray-100 disabled:cursor-not-allowed`}
              />
              {nameError && (
                <p className="mt-1 text-sm text-red-600">
                  {nameError}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Use only letters, numbers, and underscores
              </p>
            </div>

            {/* Description Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe when to use this preset..."
                rows="3"
                disabled={isSaving}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <p className="mt-1 text-xs text-gray-500">
                {description.length}/200 characters
              </p>
            </div>

            {/* Workflow Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Workflow Type <span className="text-red-500">*</span>
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="workflow"
                    value="photo"
                    checked={workflow === 'photo'}
                    onChange={(e) => setWorkflow(e.target.value)}
                    disabled={isSaving}
                    className="w-4 h-4 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    📸 <strong>Photo</strong> (Capture only)
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="workflow"
                    value="liveview"
                    checked={workflow === 'liveview' || workflow === 'video'}
                    onChange={() => setWorkflow('liveview')}
                    disabled={isSaving}
                    className="w-4 h-4 text-green-600 focus:ring-green-500 disabled:opacity-50"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    🎥 <strong>Live View</strong> (Stream only)
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="workflow"
                    value="both"
                    checked={workflow === 'both'}
                    onChange={(e) => setWorkflow(e.target.value)}
                    disabled={isSaving}
                    className="w-4 h-4 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    🔄 <strong>Both</strong> (Photo & Live View)
                  </span>
                </label>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Choose which workflow this preset is designed for
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSaving}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !!nameError || !presetName}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
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

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div
              role="alert"
              aria-live="polite"
              className="mt-4 p-3 bg-red-50 border border-red-300 rounded-lg max-h-48 overflow-y-auto"
            >
              <p className="text-sm font-semibold text-red-800 mb-2">
                ⚠️ Invalid Settings ({validationErrors.length} error{validationErrors.length > 1 ? 's' : ''})
              </p>
              <div className="space-y-1">
                {validationErrors.slice(0, 5).map((error, index) => (
                  <div key={index} className="text-xs text-red-700">
                    <span className="font-mono bg-red-100 px-1 rounded">{error.key}</span>
                    {' = '}
                    <span className="font-mono bg-red-100 px-1 rounded">{error.value}</span>
                    <div className="ml-2 text-red-600">{error.message}</div>
                  </div>
                ))}
                {validationErrors.length > 5 && (
                  <p className="text-xs text-red-600 italic mt-2">
                    ... and {validationErrors.length - 5} more error{validationErrors.length - 5 > 1 ? 's' : ''}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Info */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-800">
              <span className="font-semibold">ℹ️ Note:</span> This will capture all current camera and live view settings.
              You can apply this preset later to quickly switch between configurations.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
