import { useMemo } from 'react'

interface FieldDefinition {
  name: string
  label: string
  description: string
}

type ExportFormat = 'json' | 'csv' | 'darwin_core' | 'inaturalist'

/**
 * Field definitions grouped by category
 * Each field has: name, label, description (for tooltip)
 */
const FIELD_CATEGORIES: Record<string, FieldDefinition[]> = {
  'File Info': [
    { name: 'filename', label: 'Filename', description: 'Photo file name' },
    { name: 'filepath', label: 'File Path', description: 'Full path to photo file' },
    { name: 'file_size', label: 'File Size', description: 'Size of the file in bytes' },
    { name: 'file_type', label: 'File Type', description: 'File MIME type' },
    { name: 'date_taken', label: 'Date Taken', description: 'Date and time photo was captured' },
    { name: 'modified_at', label: 'Modified At', description: 'Last modification timestamp' }
  ],
  'Location': [
    { name: 'latitude', label: 'Latitude', description: 'GPS latitude coordinate' },
    { name: 'longitude', label: 'Longitude', description: 'GPS longitude coordinate' },
    { name: 'altitude', label: 'Altitude', description: 'GPS altitude in meters' },
    { name: 'gps_accuracy', label: 'GPS Accuracy', description: 'GPS horizontal dilution of precision (HDOP)' },
    { name: 'location_name', label: 'Location Name', description: 'Human-readable location name' }
  ],
  'Species': [
    { name: 'species', label: 'Species', description: 'Scientific species name' },
    { name: 'common_name', label: 'Common Name', description: 'Common species name' },
    { name: 'certainty', label: 'Certainty', description: 'Species identification certainty' },
    { name: 'identified_by', label: 'Identified By', description: 'Person who identified the species' },
    { name: 'identified_at', label: 'Identified At', description: 'When species was identified' }
  ],
  'Deployment': [
    { name: 'deployment_name', label: 'Deployment Name', description: 'Name of deployment/survey' },
    { name: 'deployment_id', label: 'Deployment ID', description: 'Unique deployment identifier' },
    { name: 'mothbox_id', label: 'Mothbox ID', description: 'Mothbox device identifier' },
    { name: 'firmware_version', label: 'Firmware Version', description: 'Mothbox firmware version' }
  ],
  'Tags & Notes': [
    { name: 'tags', label: 'Tags', description: 'User-defined tags' },
    { name: 'notes', label: 'Notes', description: 'User notes and annotations' }
  ],
  'EXIF': [
    { name: 'camera_make', label: 'Camera Make', description: 'Camera manufacturer' },
    { name: 'camera_model', label: 'Camera Model', description: 'Camera model' },
    { name: 'exposure_time', label: 'Exposure Time', description: 'Shutter speed' },
    { name: 'f_number', label: 'F-Number', description: 'Aperture f-stop' },
    { name: 'iso', label: 'ISO', description: 'ISO sensitivity' },
    { name: 'focal_length', label: 'Focal Length', description: 'Lens focal length' }
  ]
}

export interface FieldSelectorProps {
  format: ExportFormat
  selectedFields: Record<string, string[]>
  onChange: (format: ExportFormat, fields: string[]) => void
  disabled?: boolean
}

/**
 * FieldSelector Component
 *
 * Provides field selection UI with per-format state management.
 * Each export format maintains its own set of selected fields.
 *
 * @component
 * @example
 * <FieldSelector
 *   format="json"
 *   selectedFields={{ json: ['filename', 'tags'], darwin_core: ['species'] }}
 *   onChange={(format, fields) => setSelectedFields({ ...selectedFields, [format]: fields })}
 *   disabled={false}
 * />
 */
export default function FieldSelector({
  format,
  selectedFields,
  onChange,
  disabled = false
}: FieldSelectorProps) {
  // Get selected fields for current format
  const currentSelected = selectedFields[format] || []

  // Calculate total available fields
  const allFields = useMemo(() => {
    return Object.values(FIELD_CATEGORIES).flat().map(f => f.name)
  }, [])

  // Handle field toggle
  const handleFieldToggle = (fieldName: string) => {
    if (disabled) return

    const newSelected = currentSelected.includes(fieldName)
      ? currentSelected.filter(f => f !== fieldName)
      : [...currentSelected, fieldName]

    onChange(format, newSelected)
  }

  // Handle select all fields
  const handleSelectAll = () => {
    if (disabled) return
    onChange(format, [...allFields])
  }

  // Handle deselect all fields
  const handleDeselectAll = () => {
    if (disabled) return
    onChange(format, [])
  }

  // Handle category select all
  const handleCategorySelectAll = (categoryFields: FieldDefinition[]) => {
    if (disabled) return

    const categoryFieldNames = categoryFields.map(f => f.name)
    const newSelected = [...new Set([...currentSelected, ...categoryFieldNames])]
    onChange(format, newSelected)
  }

  // Handle category deselect all
  const handleCategoryDeselectAll = (categoryFields: FieldDefinition[]) => {
    if (disabled) return

    const categoryFieldNames = categoryFields.map(f => f.name)
    const newSelected = currentSelected.filter(f => !categoryFieldNames.includes(f))
    onChange(format, newSelected)
  }

  return (
    <div className="space-y-4">
      {/* Header with global controls */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-gray-700">
        <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {currentSelected.length} of {allFields.length} fields selected
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSelectAll}
            disabled={disabled}
            className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 dark:text-blue-400
                     dark:hover:bg-blue-900/20 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={handleDeselectAll}
            disabled={disabled}
            className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-50 dark:text-gray-400
                     dark:hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Deselect All
          </button>
        </div>
      </div>

      {/* Field categories */}
      <div className="space-y-4">
        {Object.entries(FIELD_CATEGORIES).map(([category, fields]) => (
          <div key={category} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            {/* Category header */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900 dark:text-gray-100">{category}</h3>
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid="category-select-all"
                  onClick={() => handleCategorySelectAll(fields)}
                  disabled={disabled}
                  className="text-xs text-blue-600 hover:underline dark:text-blue-400
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Select All
                </button>
                <span className="text-gray-400 dark:text-gray-600">|</span>
                <button
                  type="button"
                  data-testid="category-deselect-all"
                  onClick={() => handleCategoryDeselectAll(fields)}
                  disabled={disabled}
                  className="text-xs text-gray-600 hover:underline dark:text-gray-400
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Deselect All
                </button>
              </div>
            </div>

            {/* Field checkboxes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {fields.map(field => (
                <label
                  key={field.name}
                  title={field.description}
                  className={`flex items-center gap-2 p-2 rounded cursor-pointer
                           ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                >
                  <input
                    type="checkbox"
                    checked={currentSelected.includes(field.name)}
                    onChange={() => handleFieldToggle(field.name)}
                    disabled={disabled}
                    aria-label={field.label}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500
                             dark:border-gray-600 dark:bg-gray-700"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {field.label}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
