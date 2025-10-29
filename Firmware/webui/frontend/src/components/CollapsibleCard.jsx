// Collapsible Card Component
// Shared component for collapsible sections in Settings and related pages

import PropTypes from 'prop-types'

export default function CollapsibleCard({ id, title, isCollapsed, onToggle, children, className = "settings-card" }) {
  return (
    <div className={className}>
      <div
        className="flex justify-between items-center cursor-pointer select-none"
        onClick={() => onToggle(id)}
      >
        <h4 className="settings-card-title mb-0">{title}</h4>
        <span className="text-gray-500 text-sm">
          {isCollapsed ? '▶' : '▼'}
        </span>
      </div>
      {!isCollapsed && <div className="mt-2">{children}</div>}
    </div>
  )
}

CollapsibleCard.propTypes = {
  id: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  isCollapsed: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
  className: PropTypes.string
}
