import { useState, useCallback } from 'react'
import { useFieldArray, useWatch } from 'react-hook-form'
import type { Control, UseFormRegister } from 'react-hook-form'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'
import { METADATA_VALIDATION } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataCustomFieldsProps {
  control: Control<MetadataFormData>
  register: UseFormRegister<MetadataFormData>
  disabled?: boolean
}

export default function MetadataCustomFields({
  control,
  register,
  disabled = false,
}: MetadataCustomFieldsProps) {
  const [keyError, setKeyError] = useState<string | null>(null)
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'custom',
  })

  // Watch all custom field keys for duplicate detection
  const watchedCustom = useWatch({ control, name: 'custom' })

  const canAddMore = fields.length < METADATA_VALIDATION.MAX_CUSTOM_FIELDS

  // Check for duplicate keys on change (runs alongside register's onChange)
  const checkDuplicateKey = useCallback((index: number, newKey: string) => {
    if (!newKey) {
      setKeyError(null)
      return
    }
    const isDuplicate = (watchedCustom || []).some(
      (f, i) => i !== index && f?.key === newKey
    )
    setKeyError(isDuplicate ? `Key "${newKey}" already exists` : null)
  }, [watchedCustom])

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
    // Clear local error — if a real duplicate remains, the schema-level superRefine
    // will catch it on the next save attempt
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
                {...register(`custom.${index}.key` as const, {
                  onChange: (e) => checkDuplicateKey(index, e.target.value),
                })}
                placeholder="Field name"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <input
                type="text"
                {...register(`custom.${index}.value` as const)}
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
          <span className="text-gray-400">(max {METADATA_VALIDATION.MAX_CUSTOM_FIELDS})</span>
        )}
      </button>
    </div>
  )
}
