import { forwardRef } from 'react'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  footer?: React.ReactNode
  children: React.ReactNode
}

/**
 * Card - Card container component with optional header and footer
 *
 * @example
 * <Card title="Settings">
 *   <p>Card content goes here</p>
 * </Card>
 *
 * @example
 * <Card
 *   title="User Profile"
 *   footer={<Button>Save Changes</Button>}
 * >
 *   <FormTextInput label="Name" />
 * </Card>
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ title, footer, children, className = '', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden ${className}`}
        {...props}
      >
        {/* Header */}
        {title && (
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {title}
            </h3>
          </div>
        )}

        {/* Body */}
        <div className="px-6 py-4">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            {footer}
          </div>
        )}
      </div>
    )
  }
)

Card.displayName = 'Card'
