import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { speciesSchema, type SpeciesFormData } from '../../schemas/species'
import { SPECIES_CONFIG, Z_INDEX } from '../../constants/config'

interface BulkSpeciesModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Apply handler - receives { species, species_common_name?, species_confidence } */
  onApply: (data: { species: string; species_common_name?: string; species_confidence: string }) => void
  /** Number of selected photos */
  selectedCount: number
  /** Loading state */
  isLoading?: boolean
  /** Error message */
  error?: string | null
}

export default function BulkSpeciesModal({
  isOpen,
  onClose,
  onApply,
  selectedCount,
  isLoading = false,
  error = null,
}: BulkSpeciesModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors: formErrors },
  } = useForm<SpeciesFormData>({
    resolver: zodResolver(speciesSchema),
    defaultValues: { species: '', commonName: '', confidence: 'probable' },
    mode: 'onBlur',
  })

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      reset({ species: '', commonName: '', confidence: 'probable' })
    }
  }, [isOpen, reset])

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, isLoading, onClose])

  if (!isOpen) return null

  const onSubmit = (data: SpeciesFormData) => {
    const species = data.species ?? ''
    const commonName = data.commonName ?? ''

    if (!species) return

    const payload: { species: string; species_common_name?: string; species_confidence: string } = {
      species,
      species_confidence: data.confidence,
    }

    if (commonName) {
      payload.species_common_name = commonName
    }

    onApply(payload)
  }

  const speciesValue = watch('species')
  const isApplyDisabled = !(speciesValue ?? '').trim() || isLoading

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close (guarded during loading) */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => { if (!isLoading) onClose() }}
      />

      {/* Modal content */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-species-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 id="bulk-species-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Set species for {selectedCount} photo{selectedCount !== 1 ? 's' : ''}
          </h2>
          <button
            onClick={() => { if (!isLoading) onClose() }}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
            disabled={isLoading}
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Species Name Input (Required) */}
          <div>
            <label
              htmlFor="species-name"
              className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
            >
              Species Name <span className="text-red-500">*</span>
            </label>
            <input
              id="species-name"
              type="text"
              {...register('species')}
              placeholder="e.g., Danaus plexippus"
              aria-invalid={!!formErrors.species}
              aria-describedby={formErrors.species ? 'species-name-error' : undefined}
              className={`w-full px-3 py-2 border rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         ${formErrors.species ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}`}
            />
            {formErrors.species?.message && (
              <p id="species-name-error" role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">
                {formErrors.species.message}
              </p>
            )}
          </div>

          {/* Common Name Input (Optional) */}
          <div>
            <label
              htmlFor="common-name"
              className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
            >
              Common Name
            </label>
            <input
              id="common-name"
              type="text"
              {...register('commonName')}
              placeholder="e.g., Monarch Butterfly"
              aria-invalid={!!formErrors.commonName}
              aria-describedby={formErrors.commonName ? 'common-name-error' : undefined}
              className={`w-full px-3 py-2 border rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         ${formErrors.commonName ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}`}
            />
            {formErrors.commonName?.message && (
              <p id="common-name-error" role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">
                {formErrors.commonName.message}
              </p>
            )}
          </div>

          {/* Confidence Dropdown */}
          <div>
            <label
              htmlFor="confidence"
              className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
            >
              Confidence
            </label>
            <select
              id="confidence"
              {...register('confidence')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {SPECIES_CONFIG.CONFIDENCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Error message */}
          {error && (
            <p role="alert" className="text-red-600 dark:text-red-400 text-sm">
              {error}
            </p>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 mt-6">
            <button
              type="button"
              onClick={() => { if (!isLoading) onClose() }}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                         hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                         disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isApplyDisabled}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Applying...' : 'Apply'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
