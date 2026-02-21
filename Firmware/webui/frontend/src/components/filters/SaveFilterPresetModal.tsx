import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { filterPresetNameSchema, type FilterPresetNameData } from '../../schemas/preset'
import { FormField } from '../form/FormField'
import { Z_INDEX } from '../../constants/config'

interface SaveFilterPresetModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (name: string) => void | Promise<void>
  isSaving?: boolean
}

export function SaveFilterPresetModal({
  isOpen,
  onClose,
  onSave,
  isSaving = false,
}: SaveFilterPresetModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isDirty },
  } = useForm<FilterPresetNameData>({
    resolver: zodResolver(filterPresetNameSchema),
    defaultValues: { name: '' },
    mode: 'onBlur',
  })

  // Reset form when modal opens (useForm persists state across renders)
  useEffect(() => {
    if (isOpen) {
      reset()
    }
  }, [isOpen, reset])

  // Document-level Escape handler (works regardless of focus position)
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const onSubmit = async (data: FilterPresetNameData) => {
    try {
      await onSave(data.name)
      onClose()
    } catch (error) {
      console.error('Error saving preset:', error)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(onSubmit)()
    }
  }

  return (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} overflow-y-auto`}>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
        data-testid="modal-backdrop"
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
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              name="name"
              label="Preset Name *"
              error={errors.name}
              helperText="Choose a descriptive name for this filter combination"
            >
              <input
                type="text"
                {...register('name')}
                onKeyDown={handleKeyDown}
                placeholder="e.g., Moths from June 2024"
                disabled={isSaving}
                autoFocus
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white dark:border-gray-600 ${
                  errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                } disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed`}
              />
            </FormField>

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
                disabled={isSaving || !isValid || !isDirty}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {isSaving ? (
                  <>
                    <span className="inline-block animate-spin mr-2">&#x231B;</span>
                    Saving...
                  </>
                ) : (
                  'Save Preset'
                )}
              </button>
            </div>
          </form>

          {/* Info */}
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs text-blue-800 dark:text-blue-300">
              <span className="font-semibold">&#x2139;&#xFE0F; Note:</span> This will save your current filter
              settings. You can load this preset later to quickly apply these filters.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SaveFilterPresetModal
