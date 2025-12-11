import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'

/**
 * SavePresetModal Component
 *
 * Modal for naming and saving new filter presets.
 * Provides input validation and keyboard shortcuts.
 *
 * @component
 * @example
 * <SavePresetModal
 *   isOpen={true}
 *   onClose={() => setIsOpen(false)}
 *   onSave={(name) => savePreset(name)}
 *   defaultName="My Preset"
 * />
 */
export default function SavePresetModal({
  isOpen,
  onClose,
  onSave,
  defaultName = ''
}) {
  const [name, setName] = useState(defaultName)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setName(defaultName)
      setError('')
    }
  }, [isOpen, defaultName])

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Set default name when it changes
  useEffect(() => {
    if (defaultName && isOpen) {
      setName(defaultName)
    }
  }, [defaultName, isOpen])

  if (!isOpen) return null

  const validateName = (value) => {
    if (!value.trim()) {
      return 'Preset name is required'
    }
    if (value.length > 50) {
      return 'Name must be 50 characters or less'
    }
    return ''
  }

  const handleNameChange = (e) => {
    const value = e.target.value
    setName(value)
    setError(validateName(value))
  }

  const handleSave = () => {
    const validationError = validateName(name)
    if (validationError) {
      setError(validationError)
      return
    }

    onSave(name.trim())
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSave()
    }
  }

  const handleClose = () => {
    setName(defaultName)
    setError('')
    onClose()
  }

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
        data-testid="modal-backdrop"
      />

      {/* Modal content */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-preset-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2
            id="save-preset-title"
            className="text-lg font-semibold text-gray-900 dark:text-gray-100"
          >
            Save Filter Preset
          </h2>
          <button
            onClick={handleClose}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <XMarkIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Name input */}
        <div className="mb-6">
          <label
            htmlFor="preset-name"
            className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
          >
            Preset Name
          </label>
          <input
            ref={inputRef}
            id="preset-name"
            type="text"
            value={name}
            onChange={handleNameChange}
            onKeyDown={handleKeyDown}
            placeholder="Enter preset name..."
            maxLength={50}
            aria-invalid={!!error}
            aria-describedby={error ? 'name-error' : undefined}
            className={`w-full px-3 py-2 border rounded-md
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       ${error
                         ? 'border-red-500 dark:border-red-500'
                         : 'border-gray-300 dark:border-gray-600'
                       }`}
          />
          {error && (
            <p
              id="name-error"
              className="text-red-600 dark:text-red-400 text-sm mt-1"
              role="alert"
            >
              {error}
            </p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {name.length}/50 characters
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!!error || !name.trim()}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}

SavePresetModal.propTypes = {
  /** Whether the modal is open */
  isOpen: PropTypes.bool.isRequired,
  /** Close handler */
  onClose: PropTypes.func.isRequired,
  /** Save handler - receives preset name as string */
  onSave: PropTypes.func.isRequired,
  /** Optional default name to populate input */
  defaultName: PropTypes.string
}
