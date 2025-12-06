import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { SPECIES_CONFIG, Z_INDEX } from '@/constants/config'

/**
 * BulkSpeciesModal Component
 *
 * Modal for bulk species assignment with species name, common name, and confidence level.
 *
 * @component
 * @example
 * <BulkSpeciesModal
 *   isOpen={true}
 *   onClose={() => setIsOpen(false)}
 *   onApply={({ species, commonName, confidence }) => console.log('Apply', species, commonName, confidence)}
 *   selectedCount={5}
 * />
 */
export default function BulkSpeciesModal({
  isOpen,
  onClose,
  onApply,
  selectedCount,
  isLoading = false,
  error = null
}) {
  const [species, setSpecies] = useState('')
  const [commonName, setCommonName] = useState('')
  const [confidence, setConfidence] = useState('probable')

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setSpecies('')
      setCommonName('')
      setConfidence('probable')
    }
  }, [isOpen])

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleApply = () => {
    const trimmedSpecies = species.trim()
    const trimmedCommonName = commonName.trim()

    if (trimmedSpecies) {
      const data = {
        species: trimmedSpecies,
        confidence
      }

      // Only include commonName if it has content after trimming
      if (trimmedCommonName) {
        data.commonName = trimmedCommonName
      }

      onApply(data)
    }
  }

  const isApplyDisabled = !species.trim() || isLoading

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
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
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="space-y-4">
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
              value={species}
              onChange={(e) => setSpecies(e.target.value)}
              placeholder="e.g., Danaus plexippus"
              required
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
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
              value={commonName}
              onChange={(e) => setCommonName(e.target.value)}
              placeholder="e.g., Monarch Butterfly"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
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
              value={confidence}
              onChange={(e) => setConfidence(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {SPECIES_CONFIG.CONFIDENCE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <p role="alert" className="text-red-600 dark:text-red-400 text-sm mt-4">
            {error}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={isApplyDisabled}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Applying...' : 'Apply'}
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}

BulkSpeciesModal.propTypes = {
  /** Whether the modal is open */
  isOpen: PropTypes.bool.isRequired,
  /** Close handler */
  onClose: PropTypes.func.isRequired,
  /** Apply handler - receives { species: string, commonName?: string, confidence: 'certain' | 'probable' | 'possible' | 'unknown' } */
  onApply: PropTypes.func.isRequired,
  /** Number of selected photos */
  selectedCount: PropTypes.number.isRequired,
  /** Loading state */
  isLoading: PropTypes.bool,
  /** Error message */
  error: PropTypes.string
}
