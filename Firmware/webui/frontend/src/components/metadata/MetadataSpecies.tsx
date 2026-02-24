import { useState, useMemo } from 'react'
import { Controller, useWatch } from 'react-hook-form'
import type { Control, UseFormRegister, UseFormSetValue, FieldErrors } from 'react-hook-form'
import { MagnifyingGlassIcon, LinkIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'
import useSpecies from '../../hooks/useSpecies'
import { METADATA_VALIDATION, SPECIES_CONFIG, Z_INDEX } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataSpeciesProps {
  control: Control<MetadataFormData>
  register: UseFormRegister<MetadataFormData>
  setValue: UseFormSetValue<MetadataFormData>
  errors: FieldErrors<MetadataFormData>
  disabled?: boolean
}

export default function MetadataSpecies({
  control,
  register,
  setValue,
  errors,
  disabled = false,
}: MetadataSpeciesProps) {
  const [showSuggestions, setShowSuggestions] = useState(false)

  const [speciesValue = '', referenceUrlValue = ''] = useWatch({ control, name: ['species', 'referenceUrl'] })

  const { species: speciesData } = useSpecies({ sort: 'count', order: 'desc', limit: 20 })

  // Memoize filtered suggestions to avoid recalculation on every render
  const suggestions = useMemo(() =>
    speciesData
      ?.filter((s: { name: string }) => s.name.toLowerCase().includes(speciesValue.toLowerCase()))
      ?.slice(0, 5) || []
  , [speciesData, speciesValue])

  // Check if referenceUrl has a Zod validation error
  const urlError = errors.referenceUrl?.message ?? ''

  // Local URL check for external link icon — doesn't depend on onBlur error state
  const isValidUrl = !!referenceUrlValue && /^https?:\/\/.+/.test(referenceUrlValue)

  return (
    <div className="space-y-3">
      {/* Species Name with Autocomplete */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Scientific Name
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />
          </div>
          <Controller
            name="species"
            control={control}
            render={({ field }) => (
              <input
                type="text"
                role="combobox"
                aria-expanded={showSuggestions && suggestions.length > 0 && !!field.value}
                aria-controls="species-suggestions"
                aria-autocomplete="list"
                aria-haspopup="listbox"
                value={field.value ?? ''}
                onChange={(e) => {
                  field.onChange(e.target.value)
                  setShowSuggestions(true)
                }}
                onBlur={() => {
                  setShowSuggestions(false)
                  field.onBlur()
                }}
                onFocus={() => setShowSuggestions(true)}
                placeholder="e.g., Actias luna"
                disabled={disabled}
                maxLength={METADATA_VALIDATION.MAX_SPECIES_LENGTH}
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
            )}
          />

          {showSuggestions && suggestions.length > 0 && speciesValue && (
            <ul
              id="species-suggestions"
              role="listbox"
              aria-label="Species suggestions"
              className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-800 dark:border-gray-600 max-h-48 overflow-auto`}
            >
              {suggestions.map((s: { name: string; count: number }) => (
                <li
                  key={s.name}
                  role="option"
                  aria-selected={false}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    setValue('species', s.name, { shouldDirty: true, shouldValidate: true })
                    setShowSuggestions(false)
                  }}
                  className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {s.name} <span className="text-gray-400">({s.count})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Common Name */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Common Name
        </label>
        <input
          type="text"
          {...register('commonName')}
          placeholder="e.g., Luna Moth"
          disabled={disabled}
          maxLength={METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
        />
      </div>

      {/* Confidence Level */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Confidence
        </label>
        <select
          {...register('confidence')}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
        >
          {SPECIES_CONFIG.CONFIDENCE_OPTIONS.map((opt: { value: string; label: string }) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Reference URL */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Reference Link
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LinkIcon className="w-4 h-4 text-gray-400" />
          </div>
          <input
            type="url"
            {...register('referenceUrl')}
            placeholder="https://inaturalist.org/..."
            disabled={disabled}
            maxLength={METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH}
            className={`w-full pl-9 ${isValidUrl ? 'pr-10' : 'pr-3'} py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 ${
              urlError ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            }`}
          />
          {isValidUrl && (
            <a
              href={referenceUrlValue}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-blue-500 hover:text-blue-700"
              aria-label="Visit reference link"
            >
              <ArrowTopRightOnSquareIcon className="w-4 h-4" />
            </a>
          )}
        </div>
        {urlError && (
          <p className="mt-1 text-xs text-red-500">{urlError}</p>
        )}
      </div>
    </div>
  )
}
