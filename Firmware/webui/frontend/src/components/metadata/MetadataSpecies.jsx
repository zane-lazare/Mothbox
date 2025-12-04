import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { MagnifyingGlassIcon, LinkIcon } from '@heroicons/react/24/outline'
import useSpecies from '../../hooks/useSpecies'

const CONFIDENCE_OPTIONS = [
  { value: 'certain', label: 'Certain' },
  { value: 'probable', label: 'Probable' },
  { value: 'possible', label: 'Possible' },
  { value: 'unknown', label: 'Unknown' },
]

export default function MetadataSpecies({
  species = '',
  confidence = 'unknown',
  commonName = '',
  referenceUrl = '',
  onChange,
  disabled = false
}) {
  const [inputValue, setInputValue] = useState(species)
  const [urlInputValue, setUrlInputValue] = useState(referenceUrl)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [urlError, setUrlError] = useState('')

  // Sync local state with prop changes (e.g., when sidecar data loads async)
  useEffect(() => {
    setInputValue(species)
  }, [species])

  useEffect(() => {
    setUrlInputValue(referenceUrl)
  }, [referenceUrl])

  const { data: speciesData } = useSpecies({ sort: 'count', order: 'desc', limit: 20 })

  const suggestions = speciesData?.species
    ?.filter(s => s.name.toLowerCase().includes(inputValue.toLowerCase()))
    ?.slice(0, 5) || []

  const handleSpeciesChange = (value) => {
    setInputValue(value)
    onChange('species', value)
  }

  const handleSelectSuggestion = (name) => {
    setInputValue(name)
    onChange('species', name)
    setShowSuggestions(false)
  }

  const validateUrl = (url) => {
    if (!url) {
      setUrlError('')
      return true
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setUrlError('URL must start with http:// or https://')
      return false
    }
    setUrlError('')
    return true
  }

  const handleUrlChange = (value) => {
    setUrlInputValue(value)
    validateUrl(value)
    onChange('referenceUrl', value)
  }

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
          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value)
              setShowSuggestions(true)
            }}
            onBlur={() => {
              setTimeout(() => setShowSuggestions(false), 200)
              handleSpeciesChange(inputValue)
            }}
            onFocus={() => setShowSuggestions(true)}
            placeholder="e.g., Actias luna"
            disabled={disabled}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
          />

          {showSuggestions && suggestions.length > 0 && inputValue && (
            <ul className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-800 dark:border-gray-600 max-h-48 overflow-auto">
              {suggestions.map((s) => (
                <li
                  key={s.name}
                  onClick={() => handleSelectSuggestion(s.name)}
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
          value={commonName}
          onChange={(e) => onChange('commonName', e.target.value)}
          placeholder="e.g., Luna Moth"
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
        />
      </div>

      {/* Confidence Level */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Confidence
        </label>
        <select
          value={confidence}
          onChange={(e) => onChange('confidence', e.target.value)}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
        >
          {CONFIDENCE_OPTIONS.map((opt) => (
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
            value={urlInputValue}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="https://inaturalist.org/..."
            disabled={disabled}
            className={`w-full pl-9 pr-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 ${
              urlError ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            }`}
          />
        </div>
        {urlError && (
          <p className="mt-1 text-xs text-red-500">{urlError}</p>
        )}
      </div>
    </div>
  )
}

MetadataSpecies.propTypes = {
  species: PropTypes.string,
  confidence: PropTypes.oneOf(['certain', 'probable', 'possible', 'unknown']),
  commonName: PropTypes.string,
  referenceUrl: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}
