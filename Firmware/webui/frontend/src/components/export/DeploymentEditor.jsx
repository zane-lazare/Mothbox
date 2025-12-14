import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, XMarkIcon } from '@heroicons/react/24/outline'
import CoordinateInput from './CoordinateInput'

/**
 * DeploymentEditor Component
 *
 * Full deployment metadata form with collapsible sections.
 *
 * @component
 * @example
 * <DeploymentEditor
 *   deployment={existingDeployment}
 *   directory="/photos/deployment1"
 *   onSave={(data) => console.log('Save', data)}
 *   onCancel={() => console.log('Cancel')}
 * />
 */
export default function DeploymentEditor({
  deployment,
  directory,
  onSave,
  onCancel,
  isLoading = false,
  error = null
}) {
  // Form state
  const [deploymentName, setDeploymentName] = useState('')
  const [locationName, setLocationName] = useState('')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)
  const [altitude, setAltitude] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [environmental, setEnvironmental] = useState([])
  const [mothboxId, setMothboxId] = useState('')
  const [firmwareVersion, setFirmwareVersion] = useState('')
  const [customFields, setCustomFields] = useState([])

  // Validation errors
  const [errors, setErrors] = useState({})

  // Collapsible section state
  const [sectionsExpanded, setSectionsExpanded] = useState({
    environmental: false,
    metadata: false,
    custom: false
  })

  // Track if form has been modified
  const [hasChanges, setHasChanges] = useState(false)

  // Initialize form with existing deployment data
  useEffect(() => {
    if (deployment) {
      setDeploymentName(deployment.deployment_name || '')
      setLocationName(deployment.location_name || '')
      setLatitude(deployment.latitude ?? null)
      setLongitude(deployment.longitude ?? null)
      setAltitude(deployment.altitude?.toString() || '')
      setStartDate(deployment.start_date || '')
      setEndDate(deployment.end_date || '')

      // Convert environmental object to array
      const envArray = Object.entries(deployment.environmental || {}).map(([key, value]) => ({
        key,
        value
      }))
      setEnvironmental(envArray)

      setMothboxId(deployment.mothbox_id || '')
      setFirmwareVersion(deployment.firmware_version || '')

      // Convert custom object to array
      const customArray = Object.entries(deployment.custom || {}).map(([key, value]) => ({
        key,
        value
      }))
      setCustomFields(customArray)
    }
  }, [deployment])

  // Validate form
  const validate = () => {
    const newErrors = {}

    // Required: deployment_name
    if (!deploymentName.trim()) {
      newErrors.deploymentName = 'Deployment name is required'
    } else if (deploymentName.length > 200) {
      newErrors.deploymentName = 'Deployment name must be 200 characters or less'
    }

    // Optional: location_name max length
    if (locationName.length > 500) {
      newErrors.locationName = 'Location name must be 500 characters or less'
    }

    // Date range validation
    if (startDate && endDate && startDate > endDate) {
      newErrors.dateRange = 'End date must be after start date'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Run validation on field changes
  useEffect(() => {
    validate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deploymentName, locationName, startDate, endDate])

  const handleSave = () => {
    if (!validate()) return

    // Convert arrays back to objects
    const environmentalObj = {}
    environmental.forEach(({ key, value }) => {
      if (key.trim()) {
        environmentalObj[key.trim()] = value
      }
    })

    const customObj = {}
    customFields.forEach(({ key, value }) => {
      if (key.trim()) {
        customObj[key.trim()] = value
      }
    })

    const data = {
      deployment_name: deploymentName.trim(),
      location_name: locationName.trim(),
      latitude,
      longitude,
      altitude: altitude ? parseFloat(altitude) : null,
      start_date: startDate || null,
      end_date: endDate || null,
      environmental: environmentalObj,
      mothbox_id: mothboxId.trim(),
      firmware_version: firmwareVersion.trim(),
      custom: customObj
    }

    onSave(data)
  }

  const handleCancel = () => {
    if (hasChanges) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to cancel?'
      )
      if (!confirmed) return
    }
    onCancel()
  }

  const toggleSection = (section) => {
    setSectionsExpanded({
      ...sectionsExpanded,
      [section]: !sectionsExpanded[section]
    })
  }

  const addEnvironmentalField = () => {
    setEnvironmental([...environmental, { key: '', value: '' }])
    setSectionsExpanded({ ...sectionsExpanded, environmental: true })
  }

  const removeEnvironmentalField = (index) => {
    setEnvironmental(environmental.filter((_, i) => i !== index))
  }

  const updateEnvironmentalField = (index, field, value) => {
    const updated = [...environmental]
    updated[index][field] = value
    setEnvironmental(updated)
  }

  const addCustomField = () => {
    if (customFields.length >= 50) return
    setCustomFields([...customFields, { key: '', value: '' }])
    setSectionsExpanded({ ...sectionsExpanded, custom: true })
  }

  const removeCustomField = (index) => {
    setCustomFields(customFields.filter((_, i) => i !== index))
  }

  const updateCustomField = (index, field, value) => {
    const updated = [...customFields]
    updated[index][field] = value
    setCustomFields(updated)
  }

  const isFormValid = !errors.deploymentName && !errors.locationName && !errors.dateRange && deploymentName.trim()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {deployment ? 'Edit Deployment Metadata' : 'Create Deployment Metadata'}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Directory: {directory}
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Required Fields */}
      <div className="space-y-4">
        <div>
          <label htmlFor="deployment-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Deployment Name <span className="text-red-500">*</span>
          </label>
          <input
            id="deployment-name"
            type="text"
            value={deploymentName}
            onChange={(e) => {
              setDeploymentName(e.target.value)
              setHasChanges(true)
            }}
            disabled={isLoading}
            maxLength={200}
            placeholder="e.g., Oak Ridge Forest Survey 2024"
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       ${errors.deploymentName ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                       disabled:opacity-50 disabled:cursor-not-allowed`}
          />
          {errors.deploymentName && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.deploymentName}</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {deploymentName.length}/200 characters
          </p>
        </div>
      </div>

      {/* Location Section */}
      <div className="space-y-4 border-t pt-4 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Location</h4>

        <div>
          <label htmlFor="location-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Location Name
          </label>
          <input
            id="location-name"
            type="text"
            value={locationName}
            onChange={(e) => setLocationName(e.target.value)}
            disabled={isLoading}
            maxLength={500}
            placeholder="e.g., Oak Ridge, TN, USA"
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       ${errors.locationName ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                       disabled:opacity-50 disabled:cursor-not-allowed`}
          />
          {errors.locationName && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.locationName}</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {locationName.length}/500 characters
          </p>
        </div>

        <CoordinateInput
          latitude={latitude}
          longitude={longitude}
          onChange={({ latitude, longitude }) => {
            setLatitude(latitude)
            setLongitude(longitude)
          }}
          disabled={isLoading}
        />

        <div>
          <label htmlFor="altitude" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Altitude (meters)
          </label>
          <input
            id="altitude"
            type="number"
            step="0.1"
            value={altitude}
            onChange={(e) => setAltitude(e.target.value)}
            disabled={isLoading}
            placeholder="e.g., 350.5"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     dark:bg-gray-700 dark:text-gray-100
                     disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      {/* Date Range Section */}
      <div className="space-y-4 border-t pt-4 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Date Range</h4>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Start Date
            </label>
            <input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <div>
            <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              End Date
            </label>
            <input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        {errors.dateRange && (
          <p className="text-xs text-red-600 dark:text-red-400">{errors.dateRange}</p>
        )}
      </div>

      {/* Environmental Conditions (Collapsible) */}
      <div className="border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={() => toggleSection('environmental')}
          className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600"
        >
          {sectionsExpanded.environmental ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
          Environmental Conditions
          {environmental.length > 0 && (
            <span className="text-xs text-gray-500">({environmental.length})</span>
          )}
        </button>

        {sectionsExpanded.environmental && (
          <div className="mt-4 space-y-3">
            {environmental.map((field, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  value={field.key}
                  onChange={(e) => updateEnvironmentalField(index, 'key', e.target.value)}
                  disabled={isLoading}
                  placeholder="Key (e.g., temperature)"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <input
                  type="text"
                  value={field.value}
                  onChange={(e) => updateEnvironmentalField(index, 'value', e.target.value)}
                  disabled={isLoading}
                  placeholder="Value (e.g., 18-28°C)"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => removeEnvironmentalField(index)}
                  disabled={isLoading}
                  aria-label="Remove"
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            ))}

            <button
              type="button"
              onClick={addEnvironmentalField}
              disabled={isLoading}
              aria-label="Add environmental field"
              className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlusIcon className="h-4 w-4" />
              Add Field
            </button>
          </div>
        )}
      </div>

      {/* Metadata Section (Collapsible) */}
      <div className="border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={() => toggleSection('metadata')}
          className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600"
        >
          {sectionsExpanded.metadata ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
          Metadata
        </button>

        {sectionsExpanded.metadata && (
          <div className="mt-4 space-y-3">
            <div>
              <label htmlFor="mothbox-id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Mothbox ID
              </label>
              <input
                id="mothbox-id"
                type="text"
                value={mothboxId}
                onChange={(e) => setMothboxId(e.target.value)}
                disabled={isLoading}
                placeholder="e.g., mothbox-001"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:bg-gray-700 dark:text-gray-100
                         disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label htmlFor="firmware-version" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Firmware Version
              </label>
              <input
                id="firmware-version"
                type="text"
                value={firmwareVersion}
                onChange={(e) => setFirmwareVersion(e.target.value)}
                disabled={isLoading}
                placeholder="e.g., 5.2.1"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:bg-gray-700 dark:text-gray-100
                         disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        )}
      </div>

      {/* Custom Fields (Collapsible) */}
      <div className="border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={() => toggleSection('custom')}
          className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600"
        >
          {sectionsExpanded.custom ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
          Custom Fields
          {customFields.length > 0 && (
            <span className="text-xs text-gray-500">({customFields.length}/50)</span>
          )}
        </button>

        {sectionsExpanded.custom && (
          <div className="mt-4 space-y-3">
            {customFields.map((field, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  value={field.key}
                  onChange={(e) => updateCustomField(index, 'key', e.target.value)}
                  disabled={isLoading}
                  placeholder="Key"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <input
                  type="text"
                  value={field.value}
                  onChange={(e) => updateCustomField(index, 'value', e.target.value)}
                  disabled={isLoading}
                  placeholder="Value"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => removeCustomField(index)}
                  disabled={isLoading}
                  aria-label="Remove"
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            ))}

            <button
              type="button"
              onClick={addCustomField}
              disabled={isLoading || customFields.length >= 50}
              aria-label="Add custom field"
              className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlusIcon className="h-4 w-4" />
              Add Field {customFields.length >= 50 && '(Max 50)'}
            </button>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={handleCancel}
          disabled={isLoading}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                   hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!isFormValid || isLoading}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                   hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  )
}

DeploymentEditor.propTypes = {
  /** Existing deployment data (null for new deployment) */
  deployment: PropTypes.shape({
    deployment_name: PropTypes.string,
    location_name: PropTypes.string,
    latitude: PropTypes.number,
    longitude: PropTypes.number,
    altitude: PropTypes.number,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    environmental: PropTypes.object,
    mothbox_id: PropTypes.string,
    firmware_version: PropTypes.string,
    custom: PropTypes.object
  }),
  /** Directory path for deployment */
  directory: PropTypes.string.isRequired,
  /** Save handler - receives deployment data object */
  onSave: PropTypes.func.isRequired,
  /** Cancel handler */
  onCancel: PropTypes.func.isRequired,
  /** Loading state */
  isLoading: PropTypes.bool,
  /** Error message */
  error: PropTypes.string
}
