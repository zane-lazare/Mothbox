import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { cameraPresetFormSchema, type CameraPresetFormData, WORKFLOW_VALUES } from '../schemas/camera-preset'
import { FormField } from './form/FormField'
import { validatePresetSettings, type SettingsValidationError } from '../utils/presetValidation'
import { Z_INDEX } from '../constants/config'

interface SavePresetModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: {
    name: string
    description: string
    workflow: typeof WORKFLOW_VALUES[number]
    from_current: boolean
  }) => void | Promise<void>
  isSaving?: boolean
  defaultWorkflow?: typeof WORKFLOW_VALUES[number]
  currentSettings?: Record<string, unknown>
}

export function SavePresetModal({
  isOpen,
  onClose,
  onSave,
  isSaving = false,
  defaultWorkflow = 'both',
  currentSettings = {},
}: SavePresetModalProps) {
  const [settingsErrors, setSettingsErrors] = useState<SettingsValidationError[]>([])

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isValid },
  } = useForm<CameraPresetFormData>({
    resolver: zodResolver(cameraPresetFormSchema),
    defaultValues: { name: '', description: '', workflow: defaultWorkflow },
    mode: 'onChange',
  })

  const nameValue = watch('name')
  const descriptionValue = watch('description')
  const workflowValue = watch('workflow')

  // Clear stale settings errors when workflow changes
  useEffect(() => {
    setSettingsErrors([])
  }, [workflowValue])

  const onSubmit = async (data: CameraPresetFormData) => {
    // Validate liveview settings when workflow includes liveview
    if (data.workflow !== 'photo') {
      const settingsValidationErrors = validatePresetSettings(currentSettings)
      if (settingsValidationErrors.length > 0) {
        setSettingsErrors(settingsValidationErrors)
        return
      }
    }

    try {
      await onSave({
        name: data.name,
        description: data.description.trim(),
        workflow: data.workflow,
        from_current: true,
      })
      // Reset form on success
      reset({ name: '', description: '', workflow: defaultWorkflow })
      setSettingsErrors([])
    } catch (error) {
      console.error('Error saving preset:', error)
    }
  }

  // Explicit Enter handler — happy-dom doesn't support implicit form submission
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(onSubmit)()
    }
  }

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      reset({ name: '', description: '', workflow: defaultWorkflow })
      setSettingsErrors([])
    }
  }, [isOpen, defaultWorkflow, reset])

  // Document-level Escape handler
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSaving) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, isSaving, onClose])

  if (!isOpen) return null

  return createPortal(
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center overflow-y-auto p-4`}>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={isSaving ? undefined : onClose}
        aria-hidden="true"
        data-testid="modal-backdrop"
      />

      {/* Modal */}
      <div
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all"
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-camera-preset-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3
              id="save-camera-preset-title"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              Save Current Settings as Preset
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Create a reusable preset from your current camera and live view settings
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <XMarkIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name Input */}
          <FormField
            name="name"
            label="Preset Name *"
            error={errors.name}
            helperText="Use only letters, numbers, and underscores"
            extraDescribedBy="name-counter"
          >
            <input
              type="text"
              {...register('name')}
              onKeyDown={handleKeyDown}
              aria-required="true"
              placeholder="e.g., my_field_setup"
              maxLength={50}
              disabled={isSaving}
              autoFocus
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white dark:border-gray-600 ${
                errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              } disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed`}
            />
          </FormField>
          <p
            id="name-counter"
            aria-live="polite"
            className="text-xs text-gray-500 dark:text-gray-400"
          >
            {nameValue.length}/50 characters
          </p>

          {/* Description Input */}
          <FormField
            name="description"
            label="Description (optional)"
            error={errors.description}
            extraDescribedBy="description-counter"
          >
            <textarea
              {...register('description')}
              placeholder="Describe when to use this preset..."
              rows={3}
              disabled={isSaving}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed"
            />
          </FormField>
          <p
            id="description-counter"
            aria-live="polite"
            className="text-xs text-gray-500 dark:text-gray-400"
          >
            {descriptionValue.length}/200 characters
          </p>

          {/* Workflow Selection */}
          <fieldset>
            <legend className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Workflow Type <span className="text-red-500">*</span>
            </legend>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  {...register('workflow')}
                  value="photo"
                  disabled={isSaving}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  <strong>Photo</strong> (Capture only)
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  {...register('workflow')}
                  value="liveview"
                  disabled={isSaving}
                  className="w-4 h-4 text-green-600 focus:ring-green-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  <strong>Live View</strong> (Stream only)
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  {...register('workflow')}
                  value="both"
                  disabled={isSaving}
                  className="w-4 h-4 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  <strong>Both</strong> (Photo & Live View)
                </span>
              </label>
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Choose which workflow this preset is designed for
            </p>
          </fieldset>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !isValid}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {isSaving ? (
                <>
                  <span className="inline-block animate-spin mr-2" aria-hidden="true">&#x231B;</span>
                  Saving...
                </>
              ) : (
                'Save Preset'
              )}
            </button>
          </div>
        </form>

        {/* Settings errors render outside <form> — these are read-only context
            validation results, not user-editable field errors */}
        {settingsErrors.length > 0 && (
          <div
            role="alert"
            aria-live="polite"
            className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-lg max-h-48 overflow-y-auto"
          >
            <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">
              Invalid Settings ({settingsErrors.length} error{settingsErrors.length > 1 ? 's' : ''})
            </p>
            <div className="space-y-1">
              {settingsErrors.slice(0, 5).map((error) => (
                <div key={error.key} className="text-xs text-red-700 dark:text-red-400">
                  <span className="font-mono bg-red-100 dark:bg-red-900/40 px-1 rounded">{error.key}</span>
                  {' = '}
                  <span className="font-mono bg-red-100 dark:bg-red-900/40 px-1 rounded">{String(error.value)}</span>
                  <div className="ml-2 text-red-600 dark:text-red-400">{error.message}</div>
                </div>
              ))}
              {settingsErrors.length > 5 && (
                <p className="text-xs text-red-600 dark:text-red-400 italic mt-2">
                  ... and {settingsErrors.length - 5} more error{settingsErrors.length - 5 > 1 ? 's' : ''}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Info */}
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
          <p className="text-xs text-blue-800 dark:text-blue-300">
            <span className="font-semibold">Note:</span> This will capture all current camera and live view settings.
            You can apply this preset later to quickly switch between configurations.
          </p>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default SavePresetModal
