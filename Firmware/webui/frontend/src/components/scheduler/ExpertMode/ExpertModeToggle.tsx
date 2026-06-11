/**
 * ExpertModeToggle Component (Issue #233)
 *
 * A toggle button for switching between Visual and Expert modes in the scheduler.
 * Styled as a two-option radio button group.
 *
 * @example
 * <ExpertModeToggle
 *   mode="visual"
 *   onChange={(newMode) => console.log(newMode)}
 * />
 */

type ModeValue = 'visual' | 'expert'

interface ModeOption {
  value: ModeValue
  label: string
}

interface ExpertModeToggleProps {
  mode?: ModeValue
  onChange: (mode: ModeValue) => void
}

const ExpertModeToggle = ({ mode = 'visual', onChange }: ExpertModeToggleProps) => {
  const modes: ModeOption[] = [
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

export default ExpertModeToggle
