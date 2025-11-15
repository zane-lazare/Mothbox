import PropTypes from 'prop-types'
import CopyButton from './CopyButton'

/**
 * MetadataField - Display a single metadata field with label and value
 *
 * A simple component for displaying key-value pairs in the photo metadata panel.
 * Supports copying values to clipboard and displays "N/A" for missing data.
 *
 * @param {string} label - The field label (e.g., "Camera Model")
 * @param {any} value - The field value (will display "N/A" if null/undefined/empty string)
 * @param {boolean} copyable - If true, shows a copy button next to the value
 * @param {string} className - Optional additional CSS classes for the container
 */
export default function MetadataField({ label, value, copyable = false, className = '' }) {
  // Check if value is "empty" (null, undefined, or empty string)
  // Note: 0 and false are valid values and should not be treated as empty
  const isEmpty = value === null || value === undefined || value === ''
  const displayValue = isEmpty ? 'N/A' : String(value)
  const shouldShowCopyButton = copyable && !isEmpty

  return (
    <div className={`flex items-start justify-between py-2 ${className}`}>
      <div className="flex-1">
        <div className="text-sm font-medium text-gray-600">{label}</div>
        <div className="mt-1 text-sm text-gray-900 break-words">{displayValue}</div>
      </div>
      {shouldShowCopyButton && (
        <div className="ml-2 flex-shrink-0">
          <CopyButton text={displayValue} />
        </div>
      )}
    </div>
  )
}

MetadataField.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.any,
  copyable: PropTypes.bool,
  className: PropTypes.string,
}
