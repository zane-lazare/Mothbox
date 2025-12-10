import { useState } from 'react'
import PropTypes from 'prop-types'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function MetadataCustomFields({
  fields = {},
  onChange,
  maxFields = 100,
  disabled = false
}) {
  const [keyError, setKeyError] = useState(null)

  const entries = Object.entries(fields)
  const canAddMore = entries.length < maxFields

  const handleKeyChange = (oldKey, newKey) => {
    // Check for duplicate keys
    if (newKey && newKey !== oldKey && Object.prototype.hasOwnProperty.call(fields, newKey)) {
      setKeyError(`Key "${newKey}" already exists`)
      return
    }
    setKeyError(null)

    const newFields = { ...fields }
    const value = newFields[oldKey]
    delete newFields[oldKey]
    if (newKey) {
      newFields[newKey] = value
    }
    onChange(newFields)
  }

  const handleValueChange = (key, value) => {
    onChange({ ...fields, [key]: value })
  }

  const handleAdd = () => {
    if (!canAddMore) return
    // Generate unique temp key
    let tempKey = 'field_1'
    let i = 1
    while (Object.prototype.hasOwnProperty.call(fields, tempKey)) {
      i++
      tempKey = `field_${i}`
    }
    onChange({ ...fields, [tempKey]: '' })
  }

  const handleDelete = (key) => {
    const newFields = { ...fields }
    delete newFields[key]
    onChange(newFields)
    setKeyError(null)
  }

  return (
    <div className="space-y-2">
      {entries.length === 0 ? (
        <p className="text-sm text-gray-500">No custom fields</p>
      ) : (
        <div className="space-y-2">
          {entries.map(([key, value], index) => (
            <div key={index} className="flex gap-2 items-start">
              <input
                type="text"
                value={key}
                onChange={(e) => handleKeyChange(key, e.target.value)}
                placeholder="Field name"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <input
                type="text"
                value={value}
                onChange={(e) => handleValueChange(key, e.target.value)}
                placeholder="Value"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <button
                type="button"
                onClick={() => handleDelete(key)}
                disabled={disabled}
                className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
                aria-label={`Delete field ${key}`}
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {keyError && (
        <p className="text-xs text-red-500">{keyError}</p>
      )}

      <button
        type="button"
        onClick={handleAdd}
        disabled={disabled || !canAddMore}
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <PlusIcon className="w-4 h-4" />
        Add custom field
        {!canAddMore && <span className="text-gray-400">(max {maxFields})</span>}
      </button>
    </div>
  )
}

MetadataCustomFields.propTypes = {
  fields: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  maxFields: PropTypes.number,
  disabled: PropTypes.bool,
}
