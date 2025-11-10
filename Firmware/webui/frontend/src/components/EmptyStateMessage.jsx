import MothIcon from './MothIcon'

/**
 * EmptyStateMessage Component
 *
 * Displays context-aware empty state messages with moth icon branding.
 * Used in Gallery when no photos are available.
 *
 * @param {Object} props - Component props
 * @param {string} [props.variant='first-time'] - Empty state variant: 'first-time' | 'filtered' | 'error'
 * @param {Function} [props.onCtaClick] - Optional callback when CTA button is clicked
 * @param {string} [props.className=''] - Optional CSS classes for styling
 */
export default function EmptyStateMessage({
  variant = 'first-time',
  onCtaClick,
  className = '',
}) {
  // Define messages and CTAs for each variant
  const variants = {
    'first-time': {
      title: 'No photos yet',
      message: "Let's capture your first insect!",
      ctaText: 'Capture First Photo',
      iconSize: 120,
      iconOpacity: 'opacity-60',
    },
    filtered: {
      title: 'No matches found',
      message: 'Try adjusting your filters',
      ctaText: null, // No CTA for filtered state
      iconSize: 100,
      iconOpacity: 'opacity-40',
    },
    error: {
      title: 'Unable to load photos',
      message: 'There was an error loading the gallery',
      ctaText: 'Retry',
      iconSize: 100,
      iconOpacity: 'opacity-50',
    },
  }

  const config = variants[variant] || variants['first-time']

  return (
    <div
      role="status"
      className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}
    >
      {/* Moth Icon */}
      <div className="mb-6">
        <MothIcon size={config.iconSize} className={config.iconOpacity} />
      </div>

      {/* Title */}
      <h2 className="text-xl font-semibold text-gray-800 mb-2">{config.title}</h2>

      {/* Message */}
      <p className="text-gray-600 mb-6 max-w-md">{config.message}</p>

      {/* CTA Button (if provided) */}
      {config.ctaText && onCtaClick && (
        <button
          onClick={onCtaClick}
          className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label={config.ctaText}
        >
          {config.ctaText}
        </button>
      )}
    </div>
  )
}
