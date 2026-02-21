/**
 * Type declarations for TagChip.jsx
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with TagChip.jsx.
 */

import { ComponentType } from 'react'

interface TagChipProps {
  tag: string
  count?: number
  selected?: boolean
  removable?: boolean
  onClick?: () => void
  onRemove?: () => void
  size?: 'sm' | 'md'
  className?: string
}

declare const TagChip: ComponentType<TagChipProps>
export default TagChip
