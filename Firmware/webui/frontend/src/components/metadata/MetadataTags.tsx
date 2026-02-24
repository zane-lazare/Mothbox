import { useState, useRef, useMemo, useCallback } from 'react'
import { useWatch } from 'react-hook-form'
import type { Control, UseFormSetValue } from 'react-hook-form'
import { XMarkIcon, ClipboardDocumentIcon } from '@heroicons/react/24/outline'
import useTags from '../../hooks/useTags'
import { METADATA_VALIDATION, Z_INDEX } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataTagsProps {
  control: Control<MetadataFormData>
  setValue: UseFormSetValue<MetadataFormData>
  onCopyToNext?: () => void
  disabled?: boolean
}

export default function MetadataTags({
  control,
  setValue,
  onCopyToNext,
  disabled = false,
}: MetadataTagsProps) {
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const watchedTags = useWatch({ control, name: 'tags' })
  const tags = useMemo(() => watchedTags ?? [], [watchedTags])

  // Fetch available tags for autocomplete
  const { data: tagsData } = useTags({ sort: 'count', order: 'desc', limit: 20 })

  // Memoize filtered suggestions to avoid expensive filtering on every render
  const suggestions = useMemo(() =>
    tagsData?.tags
      ?.filter((t: { name: string }) => t.name.toLowerCase().includes(inputValue.toLowerCase()))
      ?.filter((t: { name: string }) => !tags.some((existing: string) => existing.toLowerCase() === t.name.toLowerCase()))
      ?.slice(0, 5) || []
  , [tagsData, inputValue, tags])

  const addTag = useCallback((tag: string) => {
    const trimmed = tag.trim()
    // Reject empty/whitespace tags
    if (!trimmed) return
    // Prevent duplicates (case-insensitive)
    if (tags.some((t: string) => t.toLowerCase() === trimmed.toLowerCase())) return

    setValue('tags', [...tags, trimmed], { shouldDirty: true })
    setInputValue('')
    setShowSuggestions(false)
  }, [tags, setValue])

  const removeTag = useCallback((index: number) => {
    setValue('tags', tags.filter((_: string, i: number) => i !== index), { shouldDirty: true })
  }, [tags, setValue])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === ',' || e.key === 'Enter') {
      e.preventDefault()
      addTag(inputValue)
    }
  }, [addTag, inputValue])

  return (
    <div className="space-y-2">
      {/* Tag Chips */}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag: string, index: number) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full dark:bg-blue-900 dark:text-blue-200"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              disabled={disabled}
              className="hover:text-blue-600 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={`Remove tag ${tag}`}
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </span>
        ))}
        {tags.length === 0 && (
          <span className="text-gray-400 text-sm">Add tags...</span>
        )}
      </div>

      {/* Input with Autocomplete */}
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
          onBlur={() => setShowSuggestions(false)}
          placeholder="Type to add tags..."
          disabled={disabled}
          maxLength={METADATA_VALIDATION.MAX_TAG_LENGTH}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        />

        {/* Suggestions Dropdown */}
        {showSuggestions && suggestions.length > 0 && inputValue && !disabled && (
          <ul className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-800 dark:border-gray-600 max-h-60 overflow-auto`}>
            {suggestions.map((suggestion: { name: string; count: number }) => (
              <li
                key={suggestion.name}
                onMouseDown={(e) => {
                  e.preventDefault() // Prevents blur before selection
                  addTag(suggestion.name)
                }}
                className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 flex justify-between items-center"
              >
                <span>{suggestion.name}</span>
                <span className="text-gray-400 text-sm">({suggestion.count})</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Copy to Next Button */}
      {onCopyToNext && (
        <button
          type="button"
          onClick={onCopyToNext}
          disabled={disabled || tags.length === 0}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ClipboardDocumentIcon className="w-4 h-4" />
          Copy tags to next photo
        </button>
      )}
    </div>
  )
}
