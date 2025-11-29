import PropTypes from 'prop-types'

/**
 * MetadataSkeleton - Loading skeleton for metadata panel
 *
 * Displays an animated placeholder while photo metadata is loading.
 * Shows multiple rows with varying widths to simulate metadata fields.
 *
 * @param {number} rows - Number of skeleton rows to display (default: 6)
 * @param {string} className - Optional additional CSS classes for the container
 */
export default function MetadataSkeleton({ rows = 6, className = '' }) {
  // Generate array of widths for visual variety
  const widths = ['85%', '70%', '90%', '75%', '80%', '65%']

  return (
    <div
      className={`animate-pulse ${className}`}
      role="status"
      aria-label="Loading photo metadata"
    >
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            data-testid="skeleton-row"
            className="bg-gray-200 rounded h-4"
            style={{ width: widths[index % widths.length] }}
          />
        ))}
      </div>
    </div>
  )
}

MetadataSkeleton.propTypes = {
  rows: PropTypes.number,
  className: PropTypes.string,
}
