import { useState, useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import TagChip from './TagChip'
import useTags from '../../hooks/useTags'
import { bulkTagSchema, TAG_MODES, TAG_MAX_LENGTH, TAG_MAX_COUNT, type BulkTagFormData } from '../../schemas/tag'
import { Z_INDEX } from '../../constants/config'

const MODES = [
  { value: 'add' as const, label: 'Add tags', description: 'Add to existing tags' },
  { value: 'replace' as const, label: 'Replace tags', description: 'Replace all existing tags', warning: true },
  { value: 'remove' as const, label: 'Remove tags', description: 'Remove these tags from photos' },
]

const MODE_LABELS: Record<typeof TAG_MODES[number], string> = {
  add: 'Add', replace: 'Replace', remove: 'Remove',
}

interface BulkTagModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Apply handler - receives { tags: string[], mode: 'add' | 'replace' | 'remove' } */
  onApply: (data: { tags: string[]; mode: typeof TAG_MODES[number] }) => void
  /** Number of selected photos */
  selectedCount: number
  /** Loading state */
  isLoading?: boolean
  /** Error message */
  error?: string | null
}

export default function BulkTagModal({
  isOpen,
  onClose,
  onApply,
  selectedCount,
  isLoading = false,
  error = null,
}: BulkTagModalProps) {
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const blurTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors },
  } = useForm<BulkTagFormData>({
    resolver: zodResolver(bulkTagSchema),
    defaultValues: { tags: [], mode: 'add' },
    mode: 'onBlur',
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'tags',
  })

  const mode = watch('mode')

  // Clear blur timeout on unmount to prevent state updates after teardown
  useEffect(() => {
    return () => {
      if (blurTimeoutRef.current) clearTimeout(blurTimeoutRef.current)
    }
  }, [])

  // Fetch available tags for autocomplete
  const { data: tagsData } = useTags({ sort: 'count', order: 'desc', limit: 20 })

  // Filter suggestions based on input value
  const suggestions = useMemo(() =>
    tagsData?.tags
      ?.filter((t) => t.name.toLowerCase().includes(inputValue.toLowerCase()))
      ?.filter((t) => !fields.some((existing) => existing.value.toLowerCase() === t.name.toLowerCase()))
      ?.slice(0, 8) || []
  , [tagsData, inputValue, fields])

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      reset({ tags: [], mode: 'add' })
      setInputValue('')
      setShowSuggestions(false)
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

  const handleAddTag = (tag: string) => {
    const trimmed = tag.trim()
    if (!trimmed) return
    if (trimmed.length > TAG_MAX_LENGTH) return
    if (fields.length >= TAG_MAX_COUNT) return
    // Case-insensitive duplicate check
    if (fields.some((t) => t.value.toLowerCase() === trimmed.toLowerCase())) return
    append({ value: trimmed })
    setInputValue('')
    setShowSuggestions(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ',' || e.key === 'Enter') {
      e.preventDefault()
      handleAddTag(inputValue)
    }
  }

  const onSubmit = (data: BulkTagFormData) => {
    // Auto-commit any uncommitted input before submitting.
    // Mirrors handleAddTag guards (empty, length, count, duplicate) rather
    // than routing through Zod, because append() is async and handleSubmit
    // already captured the form snapshot. Invalid input is intentionally
    // discarded — the hint text communicates the Enter/comma convention.
    const pendingTag = inputValue.trim()
    const canAddPending =
      pendingTag &&
      pendingTag.length <= TAG_MAX_LENGTH &&
      data.tags.length < TAG_MAX_COUNT &&
      !data.tags.some(t => t.value.toLowerCase() === pendingTag.toLowerCase())

    const tagStrings = data.tags.map(t => t.value)
    onApply({ tags: canAddPending ? [...tagStrings, pendingTag] : tagStrings, mode: data.mode })
  }

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
        aria-labelledby="bulk-tag-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 id="bulk-tag-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {MODE_LABELS[mode]} tags for {selectedCount} photo{selectedCount !== 1 ? 's' : ''}
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

        <form onSubmit={handleSubmit(onSubmit)}>
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
                  {...register('mode')}
                  value={m.value}
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
            <label htmlFor="bulk-tag-input" className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100">Tags</label>
            <div className="relative">
              <input
                id="bulk-tag-input"
                type="text"
                autoFocus
                value={inputValue}
                onChange={(e) => {
                  setInputValue(e.target.value)
                  setShowSuggestions(true)
                }}
                onKeyDown={handleKeyDown}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => { blurTimeoutRef.current = setTimeout(() => setShowSuggestions(false), 150) }}
                placeholder="Type to search or create tags..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              />

              {/* Suggestions Dropdown */}
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
          {fields.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {fields.map((field, index) => (
                <TagChip
                  key={field.id}
                  tag={field.value}
                  removable
                  onRemove={() => remove(index)}
                />
              ))}
            </div>
          )}

          {/* Array-level validation errors (e.g. "Too many tags").
             Individual tag errors are suppressed — handleAddTag prevents
             invalid entries from reaching the field array. The disabled
             submit button preempts the "At least one tag" error. */}
          {errors.tags?.root && (
            <p role="alert" className="text-red-600 dark:text-red-400 text-sm mb-4">{errors.tags.root.message}</p>
          )}

          {/* Error message */}
          {error && (
            <p role="alert" className="text-red-600 dark:text-red-400 text-sm mb-4">{error}</p>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
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
              disabled={fields.length === 0 || isLoading}
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
