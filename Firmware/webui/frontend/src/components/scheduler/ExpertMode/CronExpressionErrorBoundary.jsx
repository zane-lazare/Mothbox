import React from 'react'
import PropTypes from 'prop-types'

/**
 * Error Boundary for CronExpressionInput component (Issue #233)
 *
 * Provides graceful degradation if the cron expression editor encounters
 * an unexpected error, such as validation API failures or rendering issues.
 *
 * @component
 * @example
 * <CronExpressionErrorBoundary>
 *   <CronExpressionInput value={value} onChange={onChange} />
 * </CronExpressionErrorBoundary>
 */
class CronExpressionErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('CronExpressionInput error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <p className="text-sm text-red-600 dark:text-red-400 mb-2">
            Unable to load cron expression editor
          </p>
          {import.meta.env.DEV && this.state.error && (
            <p className="text-xs text-red-500 dark:text-red-500 font-mono mb-2">
              {this.state.error.message}
            </p>
          )}
          <button
            type="button"
            onClick={this.handleRetry}
            className="text-xs px-3 py-1 bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

CronExpressionErrorBoundary.propTypes = {
  /** Child components to wrap */
  children: PropTypes.node.isRequired,
}

export default CronExpressionErrorBoundary
