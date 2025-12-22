import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import ActionList from './ActionList'
import OffsetTimeline from './OffsetTimeline'
import { useValidatePattern, usePatternDuration } from '@/hooks/useEventPatterns'

/**
 * Main container component for editing event patterns.
 * Combines form inputs, action management, and timeline preview.
 *
 * @param {Object} props
 * @param {Object} [props.pattern] - Pattern to edit (undefined for create mode)
 * @param {Function} props.onSave - Called when pattern is saved
 * @param {Function} props.onCancel - Called when editing is cancelled
 */
const PatternEditor = ({ pattern, onSave, onCancel }) => {
  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [actions, setActions] = useState([])
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')

  // Validation state
  const [nameError, setNameError] = useState('')
  const [validationError, setValidationError] = useState('')

  // Hooks
  const { mutateAsync: validatePattern, isPending: isValidating } = useValidatePattern()
  const { data: duration = 0 } = usePatternDuration(actions)

  // Determine mode
  const isEditMode = Boolean(pattern?.pattern_id)

  // Initialize form from pattern prop
  useEffect(() => {
    if (pattern) {
      setName(pattern.name || '')
      setDescription(pattern.description || '')
      setActions(pattern.actions || [])
      setTags(pattern.tags || [])
    }
  }, [pattern])

  // Clear name error when user types
  useEffect(() => {
    if (name.trim()) {
      setNameError('')
    }
  }, [name])

  // Handle name change with max length
  const handleNameChange = (e) => {
    const value = e.target.value
    if (value.length <= 200) {
      setName(value)
    }
  }

  // Handle description change with max length
  const handleDescriptionChange = (e) => {
    const value = e.target.value
    if (value.length <= 2000) {
      setDescription(value)
    }
  }

  // Handle tag input
  const handleTagInputChange = (e) => {
    setTagInput(e.target.value)
  }

  // Handle tag input key press
  const handleTagInputKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddTag()
    }
  }

  // Add new tag
  const handleAddTag = () => {
    const trimmedTag = tagInput.trim()
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag])
      setTagInput('')
    }
  }

  // Remove tag
  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(t => t !== tagToRemove))
  }

  // Handle save
  const handleSave = async () => {
    // Clear previous errors
    setNameError('')
    setValidationError('')

    // Validate name
    if (!name.trim()) {
      setNameError('Pattern name is required')
      return
    }

    // Build pattern object
    const patternData = {
      pattern_id: pattern?.pattern_id || crypto.randomUUID(),
      name: name.trim(),
      description: description.trim(),
      actions,
      tags,
      category: pattern?.category
    }

    try {
      // Validate with backend
      const validationResult = await validatePattern(patternData)

      if (validationResult.valid) {
        // Call onSave with validated pattern
        onSave(patternData)
      } else {
        // Show validation errors
        const errorMessage = validationResult.errors?.join(', ') || 'Validation failed'
        setValidationError(errorMessage)
      }
    } catch (error) {
      setValidationError(error.message || 'An error occurred during validation')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
          {isEditMode ? 'Edit Pattern' : 'Create Pattern'}
        </h2>
      </div>

      {/* Form */}
      <div className="space-y-4">
        {/* Name */}
        <div>
          <label
            htmlFor="pattern-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Pattern Name *
          </label>
          <input
            id="pattern-name"
            type="text"
            value={name}
            onChange={handleNameChange}
            maxLength={200}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter pattern name"
          />
          {nameError && (
            <p className="mt-1 text-sm text-red-500">{nameError}</p>
          )}
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {name.length}/200 characters
          </p>
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="pattern-description"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Description
          </label>
          <textarea
            id="pattern-description"
            value={description}
            onChange={handleDescriptionChange}
            maxLength={2000}
            rows={3}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
            placeholder="Optional description"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {description.length}/2000 characters
          </p>
        </div>

        {/* Tags */}
        <div>
          <label
            htmlFor="pattern-tags"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Tags
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2 py-1 text-sm
                           bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300
                           rounded-full"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  aria-label={`Remove tag ${tag}`}
                  className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400
                             dark:hover:text-gray-200"
                >
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </span>
            ))}
          </div>
          <input
            id="pattern-tags"
            type="text"
            value={tagInput}
            onChange={handleTagInputChange}
            onKeyPress={handleTagInputKeyPress}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Add tag..."
          />
        </div>
      </div>

      {/* Actions Section */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
          Actions
        </h3>
        <ActionList
          actions={actions}
          onActionsChange={setActions}
        />
      </div>

      {/* Timeline Preview */}
      <div>
        <div className="flex items-baseline justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Timeline Preview
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Duration: {duration} minutes
          </p>
        </div>
        <OffsetTimeline actions={actions} />
      </div>

      {/* Validation Error */}
      {validationError && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <p className="text-sm text-red-800 dark:text-red-200">
            {validationError}
          </p>
        </div>
      )}

      {/* Buttons */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600
                     text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50
                     dark:hover:bg-gray-800 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={isValidating}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isValidating ? 'Saving...' : 'Save Pattern'}
        </button>
      </div>
    </div>
  )
}

PatternEditor.propTypes = {
  pattern: PropTypes.shape({
    pattern_id: PropTypes.string,
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    actions: PropTypes.arrayOf(PropTypes.object),
    tags: PropTypes.arrayOf(PropTypes.string),
    category: PropTypes.string
  }),
  onSave: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired
}

export default PatternEditor
