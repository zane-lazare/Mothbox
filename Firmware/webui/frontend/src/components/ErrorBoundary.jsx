import React from 'react'

/**
 * Error Boundary component for catching and handling React errors.
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of crashing.
 *
 * @component
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components to wrap
 * @param {Function} props.fallback - Optional custom fallback function (error, onClose, onRetry) => ReactNode
 * @param {string} props.errorTitle - Optional title for default fallback UI
 * @param {string} props.errorMessage - Optional message for default fallback UI
 * @param {Function} props.onReset - Callback when user clicks reset/try again
 * @param {Function} props.onRetry - Optional retry callback passed to custom fallback
 *
 * @example
 * // Basic usage with default fallback
 * <ErrorBoundary onReset={() => window.location.reload()}>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * @example
 * // Custom fallback component
 * <ErrorBoundary
 *   fallback={({ error, onClose, onRetry }) => (
 *     <LightboxErrorFallback error={error} onClose={onClose} onRetry={onRetry} />
 *   )}
 *   onReset={handleClose}
 *   onRetry={handleRetry}
 * >
 *   <PhotoLightbox {...props} />
 * </ErrorBoundary>
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback component if provided
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          onClose: () => {
            this.setState({ hasError: false, error: null })
            if (this.props.onReset) {
              this.props.onReset()
            }
          },
          onRetry: this.props.onRetry,
        })
      }

      // Default fallback UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full">
              <span className="text-2xl">⚠️</span>
            </div>
            <h2 className="mt-4 text-center text-2xl font-bold text-gray-900">
              {this.props.errorTitle || 'Something went wrong'}
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              {this.props.errorMessage || this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => {
                if (this.props.onReset) {
                  this.setState({ hasError: false, error: null })
                  this.props.onReset()
                } else {
                  window.location.reload()
                }
              }}
              className="mt-6 w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              {this.props.onReset ? 'Try Again' : 'Reload Page'}
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
