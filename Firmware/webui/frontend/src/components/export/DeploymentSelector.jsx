import { useMemo } from 'react'
import PropTypes from 'prop-types'
import { PencilIcon } from '@heroicons/react/24/outline'
import useDeployments from '../../hooks/useDeployments'

/**
 * DeploymentSelector Component
 *
 * Dropdown to select or create deployment metadata.
 *
 * @component
 * @example
 * <DeploymentSelector
 *   value="/photos/deployment1"
 *   onChange={(path) => console.log('Selected:', path)}
 *   onCreateNew={() => console.log('Create new')}
 *   onEdit={() => console.log('Edit')}
 * />
 */
export default function DeploymentSelector({
  value,
  onChange,
  onCreateNew,
  onEdit,
  disabled = false
}) {
  const { data, isLoading, error } = useDeployments()

  // Sort deployments alphabetically by name
  const sortedDeployments = useMemo(() => {
    if (!data?.deployments) return []
    return [...data.deployments].sort((a, b) =>
      a.name.localeCompare(b.name)
    )
  }, [data])

  const handleChange = (e) => {
    const selectedValue = e.target.value

    if (selectedValue === '__create_new__') {
      onCreateNew()
      return
    }

    if (selectedValue === '') {
      onChange(null)
      return
    }

    onChange(selectedValue)
  }

  if (isLoading) {
    return (
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Loading deployments...
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-sm text-red-600 dark:text-red-400">
        Failed to load deployments: {error.message}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <label htmlFor="deployment-selector" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Deployment
      </label>

      <div className="flex gap-2">
        <select
          id="deployment-selector"
          value={value || ''}
          onChange={handleChange}
          disabled={disabled}
          aria-label="Select deployment"
          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                   focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   dark:bg-gray-700 dark:text-gray-100
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">Select a deployment...</option>
          <option value="__create_new__">+ Create new deployment...</option>
          {sortedDeployments.map((deployment) => (
            <option key={deployment.directory} value={deployment.directory}>
              {deployment.name}
            </option>
          ))}
        </select>

        {value && (
          <button
            type="button"
            onClick={onEdit}
            disabled={disabled}
            aria-label="Edit deployment"
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                     hover:bg-gray-50 dark:hover:bg-gray-700
                     text-gray-700 dark:text-gray-300
                     disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center gap-1"
          >
            <PencilIcon className="h-4 w-4" />
            <span className="text-sm">Edit</span>
          </button>
        )}
      </div>

      {sortedDeployments.length === 0 && !isLoading && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          No deployments found. Create a new one to get started.
        </p>
      )}
    </div>
  )
}

DeploymentSelector.propTypes = {
  /** Selected deployment directory path */
  value: PropTypes.string,
  /** Change handler - receives deployment directory path or null */
  onChange: PropTypes.func.isRequired,
  /** Create new deployment handler */
  onCreateNew: PropTypes.func.isRequired,
  /** Edit deployment handler */
  onEdit: PropTypes.func.isRequired,
  /** Disabled state */
  disabled: PropTypes.bool
}
