import { forwardRef } from 'react'

export interface RadioOption {
  value: string
  label: string
  description?: string
  disabled?: boolean
}

export interface FormRadioGroupProps {
  label?: string
  options: RadioOption[]
  value?: string
  onChange?: (value: string) => void
  error?: string
  helperText?: string
  required?: boolean
  name: string
  disabled?: boolean
}

/**
 * FormRadioGroup - Reusable radio button group component
 *
 * @example
 * <FormRadioGroup
 *   label="Focus Mode"
 *   name="focusMode"
 *   options={[
 *     { value: 'auto', label: 'Auto-Calibrate', description: 'Automatic focus adjustment' },
 *     { value: 'manual', label: 'Manual', description: 'Set focus position manually' },
 *     { value: 'af_single', label: 'AF Single', description: 'Single autofocus' },
 *   ]}
 *   value={selectedMode}
 *   onChange={setSelectedMode}
 * />
 */
export const FormRadioGroup = forwardRef<HTMLDivElement, FormRadioGroupProps>(
  ({ label, options, value, onChange, error, helperText, required, name, disabled, ...props }, ref) => {
    const groupId = `radio-group-${Math.random().toString(36).substr(2, 9)}`

    return (
      <div ref={ref} {...props}>
        {label && (
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}

        <div
          role="radiogroup"
          aria-labelledby={label ? `${groupId}-label` : undefined}
          aria-describedby={error ? `${groupId}-error` : helperText ? `${groupId}-helper` : undefined}
          className="space-y-3"
        >
          {options.map((option) => {
            const radioId = `${groupId}-${option.value}`
            const isDisabled = disabled || option.disabled

            return (
              <div key={option.value} className="flex items-start">
                <div className="flex items-center h-5">
                  <input
                    type="radio"
                    id={radioId}
                    name={name}
                    value={option.value}
                    checked={value === option.value}
                    onChange={() => onChange?.(option.value)}
                    disabled={isDisabled}
                    className={`w-4 h-4 text-blue-600 border-gray-300 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:border-gray-600 dark:bg-gray-800 ${
                      error ? 'border-red-500' : ''
                    }`}
                    aria-invalid={error ? 'true' : 'false'}
                  />
                </div>

                <div className="ml-3">
                  <label
                    htmlFor={radioId}
                    className={`text-sm font-medium ${
                      isDisabled
                        ? 'text-gray-400 cursor-not-allowed'
                        : 'text-gray-700 dark:text-gray-300 cursor-pointer'
                    }`}
                  >
                    {option.label}
                  </label>

                  {option.description && (
                    <p className={`text-sm ${isDisabled ? 'text-gray-400' : 'text-gray-500 dark:text-gray-400'}`}>
                      {option.description}
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {error && (
          <p id={`${groupId}-error`} className="mt-2 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}

        {!error && helperText && (
          <p id={`${groupId}-helper`} className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

FormRadioGroup.displayName = 'FormRadioGroup'

export default FormRadioGroup
