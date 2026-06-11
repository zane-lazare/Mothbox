import { useState, type ReactNode } from 'react'
import { ChevronDownIcon } from '@heroicons/react/24/outline'

interface AccordionSectionProps {
  title: string
  icon?: ReactNode
  defaultExpanded?: boolean
  children?: ReactNode
  className?: string
}

export default function AccordionSection({
  title,
  icon,
  defaultExpanded = true,
  children,
  className = ''
}: AccordionSectionProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded)
  const contentId = `accordion-content-${title.toLowerCase().replace(/\s+/g, '-')}`

  const handleToggle = () => setIsExpanded(!isExpanded)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault()
      handleToggle()
    }
  }

  return (
    <div className={`border-b border-gray-200 dark:border-gray-700 ${className}`}>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        className="flex items-center justify-between w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <div className="flex items-center gap-2">
          {icon && <span className="w-5 h-5 text-gray-500">{icon}</span>}
          <span className="font-medium text-gray-900 dark:text-gray-100">{title}</span>
        </div>
        <ChevronDownIcon
          className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
        />
      </div>
      {/* Using grid-template-rows for smoother animation than max-height */}
      <div
        id={contentId}
        className={`grid transition-[grid-template-rows,opacity] duration-200 ${isExpanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}
      >
        <div className="overflow-hidden">
          <div className="p-3 pt-0">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
