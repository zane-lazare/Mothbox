import { forwardRef } from 'react'

export interface FormCheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  helperText?: string
  error?: string
}

/**
 * FormCheckbox - Reusable checkbox component with label and helper text
 *
 * @example
 * <FormCheckbox
 *   label="Enable GPS tagging"
 *   helperText="Automatically tag photos with GPS coordinates"
 *   checked={values.gpsEnabled}
 *   onChange={handleChange}
 * />
 */
export const FormCheckbox = forwardRef<HTMLInputElement, FormCheckboxProps>(
  ({ label, helperText, error, className = '', id, ...props }, ref) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`

    return (
      <div className="flex items-start">
        <div className="flex items-center h-5">
          <input
            ref={ref}
            type="checkbox"
            id={checkboxId}
            className={`w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:border-gray-600 dark:bg-gray-800 ${
              error ? 'border-red-500' : ''
            } ${className}`}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? `${checkboxId}-error` : helperText ? `${checkboxId}-helper` : undefined}
            {...props}
          />
        </div>

        {(label || helperText || error) && (
          <div className="ml-3">
            {label && (
              <label
                htmlFor={checkboxId}
                className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer"
              >
                {label}
              </label>
            )}

            {helperText && !error && (
              <p id={`${checkboxId}-helper`} className="text-xs text-gray-500 dark:text-gray-400">
                {helperText}
              </p>
            )}

            {error && (
              <p id={`${checkboxId}-error`} className="text-xs text-red-600 dark:text-red-400">
                {error}
              </p>
            )}
          </div>
        )}
      </div>
    )
  }
)

FormCheckbox.displayName = 'FormCheckbox'

export default FormCheckbox
