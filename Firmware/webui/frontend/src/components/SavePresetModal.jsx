import { useState } from 'react'
import toast from 'react-hot-toast'

export default function SavePresetModal({ isOpen, onClose, onSave, isSaving, defaultWorkflow = 'both' }) {
  const [presetName, setPresetName] = useState('')
  const [description, setDescription] = useState('')
  const [workflow, setWorkflow] = useState(defaultWorkflow)
  const [nameError, setNameError] = useState('')

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
    const error = validateName(presetName)
    if (error) {
      setNameError(error)
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
    onClose()
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSave()
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
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
                    onChange={(e) => setWorkflow('liveview')}
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
