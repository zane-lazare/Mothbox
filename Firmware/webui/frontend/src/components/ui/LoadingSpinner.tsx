import React from 'react'

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  variant?: 'primary' | 'secondary' | 'light' | 'dark'
  text?: string
  className?: string
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-3',
  lg: 'w-12 h-12 border-4',
  xl: 'w-16 h-16 border-4',
}

const variantClasses = {
  primary: 'border-blue-500 border-t-transparent dark:border-blue-400',
  secondary: 'border-gray-500 border-t-transparent dark:border-gray-400',
  light: 'border-white border-t-transparent',
  dark: 'border-gray-900 border-t-transparent dark:border-gray-100',
}

/**
 * LoadingSpinner - Animated loading spinner component
 *
 * @example
 * <LoadingSpinner size="lg" text="Loading photos..." />
 *
 * @example
 * // Light spinner for dark backgrounds
 * <LoadingSpinner variant="light" />
 */
export function LoadingSpinner({
  size = 'md',
  variant = 'primary',
  text,
  className = '',
}: LoadingSpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <div
        className={`
          ${sizeClasses[size]}
          ${variantClasses[variant]}
          rounded-full
          animate-spin
        `}
        role="status"
        aria-label={text || 'Loading'}
      >
        <span className="sr-only">{text || 'Loading...'}</span>
      </div>
      {text && (
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {text}
        </p>
      )}
    </div>
  )
}
