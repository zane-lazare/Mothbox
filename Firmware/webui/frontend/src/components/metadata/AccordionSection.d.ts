/**
 * Type declarations for AccordionSection.jsx
 *
 * Provides TypeScript types during the gradual migration.
 */
import { ReactNode } from 'react'

interface AccordionSectionProps {
  title: string
  icon?: ReactNode
  defaultExpanded?: boolean
  children: ReactNode
  className?: string
}

declare function AccordionSection(props: AccordionSectionProps): JSX.Element
export default AccordionSection
