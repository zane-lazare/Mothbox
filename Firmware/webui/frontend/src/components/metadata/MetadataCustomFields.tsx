import { useState } from 'react'
import { useFieldArray } from 'react-hook-form'
import type { Control } from 'react-hook-form'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataCustomFieldsProps {
  control: Control<MetadataFormData>
  disabled?: boolean
}

const MAX_FIELDS = 100

export default function MetadataCustomFields({
  control,
  disabled = false,
}: MetadataCustomFieldsProps) {
  const [keyError, setKeyError] = useState<string | null>(null)
  const { fields, append, remove, update } = useFieldArray({
    control,
    name: 'custom',
  })

  const canAddMore = fields.length < MAX_FIELDS

  const handleKeyChange = (index: number, newKey: string) => {
    const currentKey = fields[index].key
    if (
      newKey &&
      newKey !== currentKey &&
      fields.some((f, i) => i !== index && f.key === newKey)
    ) {
      setKeyError(`Key "${newKey}" already exists`)
      return
    }
    setKeyError(null)
    update(index, { key: newKey, value: fields[index].value })
  }

  const handleValueChange = (index: number, newValue: string) => {
    update(index, { key: fields[index].key, value: newValue })
  }

  const handleAdd = () => {
    if (!canAddMore) return
    let tempKey = 'field_1'
    let i = 1
    while (fields.some((f) => f.key === tempKey)) {
      i++
      tempKey = `field_${i}`
    }
    append({ key: tempKey, value: '' })
  }

  const handleDelete = (index: number) => {
    remove(index)
    setKeyError(null)
  }

  return (
    <div className="space-y-2">
      {fields.length === 0 ? (
        <p className="text-sm text-gray-500">No custom fields</p>
      ) : (
        <div className="space-y-2">
          {fields.map((field, index) => (
            <div key={field.id} className="flex gap-2 items-start">
              <input
                type="text"
                value={field.key}
                onChange={(e) => handleKeyChange(index, e.target.value)}
                placeholder="Field name"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <input
                type="text"
                value={field.value}
                onChange={(e) => handleValueChange(index, e.target.value)}
                placeholder="Value"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <button
                type="button"
                onClick={() => handleDelete(index)}
                disabled={disabled}
                className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
                aria-label={`Delete field ${field.key}`}
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {keyError && <p className="text-xs text-red-500">{keyError}</p>}

      <button
        type="button"
        onClick={handleAdd}
        disabled={disabled || !canAddMore}
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <PlusIcon className="w-4 h-4" />
        Add custom field
        {!canAddMore && (
          <span className="text-gray-400">(max {MAX_FIELDS})</span>
        )}
      </button>
    </div>
  )
}
