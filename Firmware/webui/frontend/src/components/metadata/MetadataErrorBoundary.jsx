import { Component } from 'react'
import PropTypes from 'prop-types'

/**
 * MetadataErrorBoundary - Error boundary for metadata panel
 *
 * Catches JavaScript errors anywhere in the metadata component tree and
 * displays a fallback UI instead of crashing the entire application.
 *
 * Features:
 * - Graceful degradation when a tab component crashes
 * - User-friendly error message
 * - Retry button to attempt recovery
 * - Logs errors to console for debugging
 *
 * @example
 * <MetadataErrorBoundary>
 *   <MetadataPanel photoPath="/path/to/photo.jpg" />
 * </MetadataErrorBoundary>
 */
class MetadataErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // Log error details to console for debugging
    console.error('MetadataPanel error:', error, errorInfo)
  }

  handleReset = () => {
    // Reset error state to try rendering again
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 text-center bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div className="mb-4">
            <svg
              className="w-12 h-12 mx-auto text-red-600 dark:text-red-400"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>
          <p className="text-red-600 dark:text-red-400 font-semibold mb-2">
            Something went wrong
          </p>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
            Unable to display metadata. This may be due to corrupted data or an unexpected error.
          </p>
          <button
            onClick={this.handleReset}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

MetadataErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
}

export default MetadataErrorBoundary
