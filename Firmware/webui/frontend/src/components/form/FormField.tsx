import React from 'react'

export interface FormFieldProps {
  name: string
  label?: string
  error?: { message?: string }
  helperText?: string
  children: React.ReactElement<
    React.InputHTMLAttributes<HTMLElement> & {
      'aria-invalid'?: boolean
      'aria-describedby'?: string
    }
  >
}

export function FormField({ name, label, error, helperText, children }: FormFieldProps) {
  const describedBy = error
    ? `${name}-error`
    : helperText
      ? `${name}-help`
      : undefined

  return (
    <div>
      {label && (
        <label
          htmlFor={name}
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          {label}
        </label>
      )}
      {/* ref is NOT forwarded — callers must spread field.ref on the input */}
      {React.cloneElement(children, {
        id: name,
        'aria-invalid': !!error,
        'aria-describedby': describedBy,
      })}
      {error?.message && (
        <p
          id={`${name}-error`}
          role="alert"
          className="mt-1 text-sm text-red-600 dark:text-red-400"
        >
          {error.message}
        </p>
      )}
      {!error && helperText && (
        <p
          id={`${name}-help`}
          className="mt-1 text-xs text-gray-500 dark:text-gray-400"
        >
          {helperText}
        </p>
      )}
    </div>
  )
}
