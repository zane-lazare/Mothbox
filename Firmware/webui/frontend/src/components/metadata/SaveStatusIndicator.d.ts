/**
 * Type declarations for SaveStatusIndicator.jsx
 *
 * Provides TypeScript types during the gradual migration.
 */

interface SaveStatusIndicatorProps {
  status: 'idle' | 'saving' | 'saved' | 'error'
  onRetry?: () => void
  errorMessage?: string
}

declare function SaveStatusIndicator(props: SaveStatusIndicatorProps): JSX.Element | null
export default SaveStatusIndicator
