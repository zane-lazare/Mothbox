import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { validateCoordinate, formatCoordinateDisplay } from '../../utils/gpsCoordinates'

/**
 * CoordinateInput Component
 *
 * GPS coordinate input with validation and optional DMS format display.
 *
 * @component
 * @example
 * <CoordinateInput
 *   latitude={37.7749}
 *   longitude={-122.4194}
 *   onChange={({ latitude, longitude }) => console.log(latitude, longitude)}
 * />
 */
export default function CoordinateInput({
  latitude,
  longitude,
  onChange,
  error = null,
  disabled = false
}) {
  const [latValue, setLatValue] = useState(latitude ?? '')
  const [lonValue, setLonValue] = useState(longitude ?? '')
  const [latError, setLatError] = useState(null)
  const [lonError, setLonError] = useState(null)
  const [showDMS, setShowDMS] = useState(false)

  // Sync with external values
  useEffect(() => {
    setLatValue(latitude ?? '')
  }, [latitude])

  useEffect(() => {
    setLonValue(longitude ?? '')
  }, [longitude])

  const handleLatitudeChange = (e) => {
    const value = e.target.value
    setLatValue(value)

    // Empty value is valid (optional field)
    if (value === '' || value === null) {
      setLatError(null)
      onChange({ latitude: null, longitude })
      return
    }

    const numValue = parseFloat(value)

    // Validate
    if (isNaN(numValue)) {
      setLatError('Latitude must be a number')
      return
    }

    const validation = validateCoordinate(numValue, 'latitude')
    if (!validation.isValid) {
      setLatError(validation.error)
      return
    }

    setLatError(null)
    onChange({ latitude: numValue, longitude })
  }

  const handleLongitudeChange = (e) => {
    const value = e.target.value
    setLonValue(value)

    // Empty value is valid (optional field)
    if (value === '' || value === null) {
      setLonError(null)
      onChange({ latitude, longitude: null })
      return
    }

    const numValue = parseFloat(value)

    // Validate
    if (isNaN(numValue)) {
      setLonError('Longitude must be a number')
      return
    }

    const validation = validateCoordinate(numValue, 'longitude')
    if (!validation.isValid) {
      setLonError(validation.error)
      return
    }

    setLonError(null)
    onChange({ latitude, longitude: numValue })
  }

  const toggleFormat = () => {
    setShowDMS(!showDMS)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          GPS Coordinates
        </label>
        {(latitude !== null && longitude !== null) && (
          <button
            type="button"
            onClick={toggleFormat}
            aria-label="Toggle format"
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            disabled={disabled}
          >
            {showDMS ? 'Show Decimal' : 'Show DMS'}
          </button>
        )}
      </div>

      {/* Decimal inputs */}
      {!showDMS && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="latitude" className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Latitude
            </label>
            <input
              id="latitude"
              type="number"
              step="0.000001"
              min="-90"
              max="90"
              value={latValue}
              onChange={handleLatitudeChange}
              disabled={disabled}
              placeholder="e.g., 37.7749"
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:bg-gray-700 dark:text-gray-100
                         ${latError ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                         disabled:opacity-50 disabled:cursor-not-allowed`}
              aria-describedby={latError ? 'lat-error' : undefined}
            />
            {latError && (
              <p id="lat-error" className="text-xs text-red-600 dark:text-red-400 mt-1">
                {latError}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="longitude" className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Longitude
            </label>
            <input
              id="longitude"
              type="number"
              step="0.000001"
              min="-180"
              max="180"
              value={lonValue}
              onChange={handleLongitudeChange}
              disabled={disabled}
              placeholder="e.g., -122.4194"
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:bg-gray-700 dark:text-gray-100
                         ${lonError ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                         disabled:opacity-50 disabled:cursor-not-allowed`}
              aria-describedby={lonError ? 'lon-error' : undefined}
            />
            {lonError && (
              <p id="lon-error" className="text-xs text-red-600 dark:text-red-400 mt-1">
                {lonError}
              </p>
            )}
          </div>
        </div>
      )}

      {/* DMS display */}
      {showDMS && latitude !== null && longitude !== null && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Latitude (DMS)
            </label>
            <div className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                          bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
              {formatCoordinateDisplay(latitude, true, 'dms')}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
              Longitude (DMS)
            </label>
            <div className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                          bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
              {formatCoordinateDisplay(longitude, false, 'dms')}
            </div>
          </div>
        </div>
      )}

      {/* External error message */}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      <p className="text-xs text-gray-500 dark:text-gray-400">
        Latitude: -90 to 90, Longitude: -180 to 180
      </p>
    </div>
  )
}

CoordinateInput.propTypes = {
  /** Latitude in decimal degrees (-90 to 90) */
  latitude: PropTypes.number,
  /** Longitude in decimal degrees (-180 to 180) */
  longitude: PropTypes.number,
  /** Change handler - receives { latitude, longitude } */
  onChange: PropTypes.func.isRequired,
  /** External error message */
  error: PropTypes.string,
  /** Disabled state */
  disabled: PropTypes.bool
}
