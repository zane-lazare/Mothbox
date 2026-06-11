// Collapsible Card Component
// Shared component for collapsible sections in Settings and related pages

import React from 'react'

export interface CollapsibleCardProps {
  id: string
  title: string
  isCollapsed: boolean
  onToggle: (id: string) => void
  children: React.ReactNode
  className?: string
}

export default function CollapsibleCard({
  id,
  title,
  isCollapsed,
  onToggle,
  children,
  className = "settings-card"
}: CollapsibleCardProps) {
  return (
    <div className={className}>
      <button
        className="w-full flex justify-between items-center cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded px-2 py-1 -mx-2 -my-1"
        onClick={() => onToggle(id)}
        aria-expanded={!isCollapsed}
        aria-controls={`collapsible-content-${id}`}
        type="button"
      >
        <h4 className="settings-card-title mb-0">{title}</h4>
        <span className="text-gray-500 text-sm" aria-hidden="true">
          {isCollapsed ? '▶' : '▼'}
        </span>
      </button>
      {!isCollapsed && (
        <div id={`collapsible-content-${id}`} className="mt-2">
          {children}
        </div>
      )}
    </div>
  )
}
