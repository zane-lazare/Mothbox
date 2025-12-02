import { useState, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'

function TagAutocomplete({
  tags = [],
  selectedTags = [],
  onSelect,
  onCreate,
  placeholder = 'Search or create tags...',
  disabled = false,
  className = '',
}) {
  const [inputValue, setInputValue] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  // Filter tags based on input (case-insensitive substring match)
  const filteredTags = tags.filter(
    (tag) =>
      tag.name.toLowerCase().includes(inputValue.toLowerCase()) &&
      !selectedTags.includes(tag.name)
  )

  // Check if exact match exists
  const exactMatch = tags.some(
    (t) => t.name.toLowerCase() === inputValue.toLowerCase()
  )
  const showCreateOption =
    inputValue.trim() && !exactMatch && !selectedTags.includes(inputValue.trim())

  // Total number of options (filtered tags + create option if shown)
  const totalOptions = filteredTags.length + (showCreateOption ? 1 : 0)

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        if (inputValue.trim()) {
          setIsOpen(true)
        }
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex((prev) => {
          if (prev === -1) return 0
          return (prev + 1) % totalOptions
        })
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex((prev) => {
          if (prev === -1) return totalOptions - 1
          return (prev - 1 + totalOptions) % totalOptions
        })
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0 && highlightedIndex < totalOptions) {
          if (highlightedIndex < filteredTags.length) {
            handleSelect(filteredTags[highlightedIndex].name)
          } else if (showCreateOption) {
            handleCreate()
          }
        } else if (showCreateOption) {
          handleCreate()
        }
        break
      case 'Escape':
        setIsOpen(false)
        setHighlightedIndex(-1)
        break
    }
  }

  const handleSelect = (tag) => {
    onSelect(tag)
    setInputValue('')
    setIsOpen(false)
    setHighlightedIndex(-1)
    inputRef.current?.focus()
  }

  const handleCreate = () => {
    const newTag = inputValue.trim()
    if (newTag && !selectedTags.includes(newTag)) {
      onCreate(newTag)
      setInputValue('')
      setIsOpen(false)
      setHighlightedIndex(-1)
    }
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    setInputValue(value)
    if (value.trim()) {
      setIsOpen(true)
    } else {
      setIsOpen(false)
    }
    setHighlightedIndex(-1)
  }

  const handleFocus = () => {
    if (inputValue.trim()) {
      setIsOpen(true)
    }
  }

  const handleBlur = () => {
    // Delay to allow click events on dropdown items to fire
    setTimeout(() => {
      setIsOpen(false)
    }, 150)
  }

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls="tag-listbox"
        aria-activedescendant={
          highlightedIndex >= 0 ? `tag-option-${highlightedIndex}` : undefined
        }
        aria-autocomplete="list"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                   focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                   bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                   placeholder-gray-500 dark:placeholder-gray-400
                   disabled:opacity-50 disabled:cursor-not-allowed"
      />

      {isOpen && totalOptions > 0 && (
        <ul
          id="tag-listbox"
          role="listbox"
          ref={listRef}
          className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border
                     border-gray-300 dark:border-gray-600 rounded-md shadow-lg
                     max-h-60 overflow-auto"
        >
          {filteredTags.map((tag, index) => (
            <li
              key={tag.name}
              id={`tag-option-${index}`}
              role="option"
              aria-selected={highlightedIndex === index}
              className={`px-3 py-2 cursor-pointer flex justify-between items-center
                         ${
                           highlightedIndex === index
                             ? 'bg-blue-100 dark:bg-blue-900'
                             : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                         }`}
              onClick={() => handleSelect(tag.name)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              <span>{tag.name}</span>
              <span className="text-gray-500 text-sm">({tag.count})</span>
            </li>
          ))}

          {showCreateOption && (
            <li
              id={`tag-option-${filteredTags.length}`}
              role="option"
              aria-selected={highlightedIndex === filteredTags.length}
              className={`px-3 py-2 cursor-pointer flex items-center gap-2
                         ${
                           highlightedIndex === filteredTags.length
                             ? 'bg-green-100 dark:bg-green-900'
                             : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                         }`}
              onClick={handleCreate}
              onMouseEnter={() => setHighlightedIndex(filteredTags.length)}
            >
              <span className="text-green-600 dark:text-green-400">
                + Create
              </span>
              <span className="font-medium">&quot;{inputValue.trim()}&quot;</span>
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

TagAutocomplete.propTypes = {
  tags: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    })
  ),
  selectedTags: PropTypes.arrayOf(PropTypes.string),
  onSelect: PropTypes.func.isRequired,
  onCreate: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  className: PropTypes.string,
}

export default TagAutocomplete
