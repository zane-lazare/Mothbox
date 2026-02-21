import React from 'react'

export interface FormNumberInputProps {
  name: string
  label?: string
  error?: { message?: string }
  helperText?: string
  min?: number
  max?: number
  step?: number
  value?: number | string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  disabled?: boolean
  className?: string
}

export function FormNumberInput({
  name,
  label,
  error,
  helperText,
  min,
  max,
  step,
  value,
  onChange,
  disabled,
  className,
}: FormNumberInputProps) {
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
      <input
        type="number"
        id={name}
        value={value}
        onChange={onChange}
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        aria-invalid={!!error}
        aria-describedby={describedBy}
        className={
          className ??
          `w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            error ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
          } disabled:bg-gray-100 disabled:cursor-not-allowed dark:bg-gray-800 dark:text-gray-200`
        }
      />
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
