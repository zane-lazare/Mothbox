import PropTypes from 'prop-types'

/**
 * ExpertModeToggle Component (Issue #233)
 *
 * A toggle button for switching between Visual and Expert modes in the scheduler.
 * Styled as a two-option radio button group.
 *
 * @component
 * @example
 * <ExpertModeToggle
 *   mode="visual"
 *   onChange={(newMode) => console.log(newMode)}
 * />
 */
const ExpertModeToggle = ({ mode = 'visual', onChange }) => {
  const modes = [
    { value: 'visual', label: 'Visual' },
    { value: 'expert', label: 'Expert' },
  ]

  return (
    <div className="inline-flex rounded-md shadow-sm" role="group" aria-label="Mode selector">
      {modes.map((modeOption, index) => {
        const isSelected = mode === modeOption.value
        const isFirst = index === 0
        const isLast = index === modes.length - 1

        return (
          <button
            key={modeOption.value}
            type="button"
            onClick={() => onChange(modeOption.value)}
            className={`
              px-4 py-2 text-sm font-medium
              focus:z-10 focus:ring-2 focus:ring-blue-500 focus:outline-none
              transition-colors duration-150
              ${
                isFirst
                  ? 'rounded-l-md'
                  : isLast
                    ? 'rounded-r-md'
                    : ''
              }
              ${
                isSelected
                  ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                  : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600'
              }
              ${!isFirst && !isSelected ? '-ml-px' : ''}
            `}
            aria-pressed={isSelected}
            aria-label={`Switch to ${modeOption.label} mode`}
          >
            {modeOption.label}
          </button>
        )
      })}
    </div>
  )
}

ExpertModeToggle.propTypes = {
  /** Current mode: 'visual' or 'expert' */
  mode: PropTypes.oneOf(['visual', 'expert']),
  /** Callback when mode changes */
  onChange: PropTypes.func.isRequired,
}

export default ExpertModeToggle
