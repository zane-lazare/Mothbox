import { useState, useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/24/outline'
import TagChip from './TagChip'
import useTags from '../../hooks/useTags'
import { Z_INDEX } from '../../constants/config'

const MODES = [
  { value: 'add', label: 'Add tags', description: 'Add to existing tags' },
  { value: 'replace', label: 'Replace tags', description: 'Replace all existing tags', warning: true },
  { value: 'remove', label: 'Remove tags', description: 'Remove these tags from photos' }
]

/**
 * BulkTagModal Component
 *
 * Modal for bulk tag operations (add, replace, remove) on multiple photos.
 *
 * @component
 * @example
 * <BulkTagModal
 *   isOpen={true}
 *   onClose={() => setIsOpen(false)}
 *   onApply={({ tags, mode }) => console.log('Apply', tags, mode)}
 *   selectedCount={5}
 * />
 */
export default function BulkTagModal({
  isOpen,
  onClose,
  onApply,
  selectedCount,
  isLoading = false,
  error = null
}) {
  const [mode, setMode] = useState('add')
  const [tags, setTags] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef(null)

  // Fetch available tags for autocomplete (same as MetadataTags)
  const { data: tagsData } = useTags({ sort: 'count', order: 'desc', limit: 20 })

  // Filter suggestions based on input value
  const suggestions = useMemo(() =>
    tagsData?.tags
      ?.filter((t) => t.name.toLowerCase().includes(inputValue.toLowerCase()))
      ?.filter((t) => !tags.some((existing) => existing.toLowerCase() === t.name.toLowerCase()))
      ?.slice(0, 8) || []
  , [tagsData, inputValue, tags])

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setMode('add')
      setTags([])
      setInputValue('')
      setShowSuggestions(false)
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

  const handleAddTag = (tag) => {
    const trimmed = tag.trim()
    if (!trimmed) return
    // Case-insensitive duplicate check
    if (tags.some((t) => t.toLowerCase() === trimmed.toLowerCase())) return
    setTags([...tags, trimmed])
    setInputValue('')
    setShowSuggestions(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === ',' || e.key === 'Enter') {
      e.preventDefault()
      handleAddTag(inputValue)
    }
  }

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(t => t !== tagToRemove))
  }

  const handleApply = () => {
    if (tags.length > 0) {
      onApply({ tags, mode })
    }
  }

  const getModeLabel = () => {
    if (mode === 'add') return 'Add'
    if (mode === 'replace') return 'Replace'
    return 'Remove'
  }

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
        aria-labelledby="bulk-tag-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 id="bulk-tag-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {getModeLabel()} tags for {selectedCount} photo{selectedCount !== 1 ? 's' : ''}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Mode selector */}
        <div className="mb-4" role="radiogroup" aria-label="Tag operation mode">
          {MODES.map(m => (
            <label
              key={m.value}
              className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer mb-2
                         ${mode === m.value
                  ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
            >
              <input
                type="radio"
                name="tag-mode"
                value={m.value}
                checked={mode === m.value}
                onChange={() => setMode(m.value)}
                className="mt-1"
                aria-label={m.label}
              />
              <div>
                <span className="font-medium text-gray-900 dark:text-gray-100">{m.label}</span>
                <p className={`text-sm ${m.warning ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500 dark:text-gray-400'}`}>
                  {m.description}
                </p>
              </div>
            </label>
          ))}
        </div>

        {/* Tag input */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100">Tags</label>
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value)
                setShowSuggestions(true)
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder="Type to search or create tags..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
            />

            {/* Suggestions Dropdown - shows existing tags */}
            {showSuggestions && suggestions.length > 0 && (
              <ul className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-700 dark:border-gray-600 max-h-48 overflow-auto`}>
                {suggestions.map((suggestion) => (
                  <li
                    key={suggestion.name}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      handleAddTag(suggestion.name)
                    }}
                    className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 flex justify-between items-center text-gray-900 dark:text-gray-100"
                  >
                    <span>{suggestion.name}</span>
                    <span className="text-gray-400 text-sm">({suggestion.count})</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Press Enter or comma to add tags
          </p>
        </div>

        {/* Selected tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {tags.map(tag => (
              <TagChip
                key={tag}
                tag={tag}
                removable
                onRemove={() => handleRemoveTag(tag)}
              />
            ))}
          </div>
        )}

        {/* Error message */}
        {error && (
          <p className="text-red-600 dark:text-red-400 text-sm mb-4">{error}</p>
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
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
            disabled={tags.length === 0 || isLoading}
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

BulkTagModal.propTypes = {
  /** Whether the modal is open */
  isOpen: PropTypes.bool.isRequired,
  /** Close handler */
  onClose: PropTypes.func.isRequired,
  /** Apply handler - receives { tags: string[], mode: 'add' | 'replace' | 'remove' } */
  onApply: PropTypes.func.isRequired,
  /** Number of selected photos */
  selectedCount: PropTypes.number.isRequired,
  /** Loading state */
  isLoading: PropTypes.bool,
  /** Error message */
  error: PropTypes.string
}
