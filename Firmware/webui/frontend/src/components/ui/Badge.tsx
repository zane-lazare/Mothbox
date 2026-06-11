import { forwardRef } from 'react'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md' | 'lg'
  onClose?: () => void
  children: React.ReactNode
}

/**
 * Badge - Badge/tag component with variants and optional close button
 *
 * @example
 * <Badge variant="success">Active</Badge>
 *
 * @example
 * <Badge variant="warning" size="sm" onClose={() => removeTag()}>
 *   Tag Name
 * </Badge>
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = 'default', size = 'md', onClose, children, className = '', ...props }, ref) => {
    const baseStyles = 'inline-flex items-center font-medium rounded-full transition-colors'

    const variantStyles = {
      default: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
      success: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      danger: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
    }

    const sizeStyles = {
      sm: 'px-2 py-0.5 text-xs gap-1',
      md: 'px-2.5 py-1 text-sm gap-1.5',
      lg: 'px-3 py-1.5 text-base gap-2'
    }

    return (
      <span
        ref={ref}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {children}
        {onClose && (
          <button
            onClick={onClose}
            className="ml-1 -mr-1 hover:bg-black/10 dark:hover:bg-white/10 rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-current"
            aria-label="Remove badge"
            type="button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-3 w-3"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        )}
      </span>
    )
  }
)

Badge.displayName = 'Badge'
