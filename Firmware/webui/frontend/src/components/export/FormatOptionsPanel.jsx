import PropTypes from 'prop-types'
import { GPS_PRECISION_OPTIONS, getGpsPrecision } from '../../utils/gpsPrecision'

function FormatOptionsPanel({ format, options = {}, onChange, disabled = false }) {
  const handleOptionChange = (key, value) => {
    onChange({ ...options, [key]: value })
  }

  // Don't render anything if no format selected
  if (!format) {
    return null
  }

  // Get current GPS precision value (from options or global setting)
  const currentPrecision = options.gps_precision ?? getGpsPrecision()

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Format Options
      </h3>

      {/* GPS Precision - Common to all formats (Issue #288) */}
      <div className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        <label
          htmlFor="gps-precision"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
        >
          GPS Precision
        </label>
        <select
          id="gps-precision"
          value={currentPrecision}
          onChange={(e) => handleOptionChange('gps_precision', parseInt(e.target.value, 10))}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                    bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                    disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {GPS_PRECISION_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
          Reduce precision for privacy when sharing location data
        </p>
      </div>

      {/* Darwin Core Options */}
      {format === 'darwin_core' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.validate || false}
              onChange={(e) => handleOptionChange('validate', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Validate output against Darwin Core schema
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Ensure exported data conforms to Darwin Core standards
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.include_warnings || false}
              onChange={(e) => handleOptionChange('include_warnings', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include validation warnings
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add warnings as comments in the CSV file
              </p>
            </div>
          </label>
        </div>
      )}

      {/* iNaturalist Options */}
      {format === 'inaturalist' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.include_xmp_sidecars !== false} // Default true
              onChange={(e) => handleOptionChange('include_xmp_sidecars', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include XMP sidecar files
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Generate .xmp files alongside photos with embedded metadata
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.include_manifest !== false} // Default true
              onChange={(e) => handleOptionChange('include_manifest', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include manifest.json
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add manifest file with export metadata and file list
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.include_csv_summary || false}
              onChange={(e) => handleOptionChange('include_csv_summary', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include CSV summary
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add a summary CSV file with photo metadata
              </p>
            </div>
          </label>
        </div>
      )}

      {/* JSON Options */}
      {format === 'json' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.pretty_print !== false} // Default true
              onChange={(e) => handleOptionChange('pretty_print', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Pretty print JSON
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Format JSON with indentation for readability
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.include_raw_exif || false}
              onChange={(e) => handleOptionChange('include_raw_exif', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include raw EXIF data
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add complete EXIF data from photo files
              </p>
            </div>
          </label>
        </div>
      )}

      {/* CSV Options */}
      {format === 'csv' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={options.include_bom !== false} // Default true
              onChange={(e) => handleOptionChange('include_bom', e.target.checked)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include UTF-8 BOM
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add byte order mark for Excel compatibility
              </p>
            </div>
          </label>

          <div>
            <label
              htmlFor="csv-delimiter"
              className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
            >
              Delimiter
            </label>
            <select
              id="csv-delimiter"
              value={options.delimiter || ','}
              onChange={(e) => handleOptionChange('delimiter', e.target.value)}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                        disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value=",">Comma (,)</option>
              <option value={'\t'}>Tab</option>
              <option value=";">Semicolon (;)</option>
            </select>
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
              Choose delimiter for CSV columns
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

FormatOptionsPanel.propTypes = {
  format: PropTypes.string,
  options: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}

export default FormatOptionsPanel
