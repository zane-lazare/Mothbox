import PropTypes from 'prop-types'
import { MOON_PHASES, TRIGGER_FORM_BORDER } from './constants'

/**
 * MoonPhaseTriggerForm Component
 *
 * Form for configuring moon phase triggers with emoji grid.
 *
 * @component
 */
function MoonPhaseTriggerForm({ trigger, onChange, disabled = false, error = null }) {
  const selectedPhases = trigger?.phases || ['full']
  const hasError = error || selectedPhases.length === 0

  /**
   * Handle phase toggle
   */
  const handlePhaseToggle = (phaseValue) => {
    const isSelected = selectedPhases.includes(phaseValue)
    let newPhases

    if (isSelected) {
      // Remove phase (but keep at least one)
      if (selectedPhases.length <= 1) return
      newPhases = selectedPhases.filter(p => p !== phaseValue)
    } else {
      // Add phase
      newPhases = [...selectedPhases, phaseValue]
    }

    onChange({
      ...trigger,
      phases: newPhases,
    })
  }

  return (
    <div className={TRIGGER_FORM_BORDER} data-testid="moon-phase-trigger-form">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-900 dark:text-white">Moon Phase</span>
        <span className="text-xs text-gray-500 dark:text-gray-600">lunar cycle events</span>
      </div>

      <div className="space-y-4">
        {/* Moon Phase Grid */}
        <div
          className={`grid grid-cols-4 gap-2 ${hasError ? 'ring-1 ring-red-500 rounded p-1' : ''}`}
          data-testid="moon-phase-grid"
        >
          {MOON_PHASES.map((phase) => {
            const isSelected = selectedPhases.includes(phase.value)
            const isLastSelected = isSelected && selectedPhases.length === 1
            return (
              <label
                key={phase.value}
                title={isLastSelected ? 'At least one phase required' : undefined}
                className={`
                  flex flex-col items-center p-2 border rounded cursor-pointer
                  ${isSelected
                    ? 'border-gray-700 bg-gray-800'
                    : 'border-gray-800 hover:border-gray-600'
                  }
                  ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                  ${isLastSelected ? 'opacity-60 cursor-not-allowed' : ''}
                `}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handlePhaseToggle(phase.value)}
                  disabled={disabled}
                  className="sr-only"
                  data-testid={`moon-phase-${phase.value}`}
                />
                <span className="text-lg">{phase.emoji}</span>
                <span className={`text-xs mt-1 ${isSelected ? 'text-gray-400' : 'text-gray-500'}`}>
                  {phase.label}
                </span>
              </label>
            )
          })}
        </div>

        {/* Error message */}
        {error && (
          <div className="text-xs text-red-400" data-testid="moon-phase-error">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}

MoonPhaseTriggerForm.propTypes = {
  trigger: PropTypes.shape({
    trigger_type: PropTypes.string,
    phases: PropTypes.arrayOf(PropTypes.string),
  }),
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  error: PropTypes.string,
}

export default MoonPhaseTriggerForm
