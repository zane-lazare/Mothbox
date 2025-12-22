import { memo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { BoltIcon, ClockIcon } from '@heroicons/react/24/outline';
import TagChip from '../../gallery/TagChip';

/**
 * PatternCard Component
 *
 * Displays a pattern card in the pattern library with name, description,
 * action count, duration, tags, and a "Use Pattern" button.
 *
 * @component
 * @example
 * <PatternCard
 *   pattern={pattern}
 *   onClick={(pattern) => console.log('View details:', pattern)}
 *   onSelect={(pattern) => console.log('Use pattern:', pattern)}
 *   isSelected={false}
 * />
 */
function PatternCard({ pattern, onClick, onSelect, isSelected = false }) {
  const handleCardClick = useCallback(() => {
    if (onClick) {
      onClick(pattern);
    }
  }, [onClick, pattern]);

  const handleCardKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleCardClick();
      }
    },
    [handleCardClick]
  );

  const handleSelectClick = useCallback(
    (e) => {
      e.stopPropagation();
      if (onSelect) {
        onSelect(pattern);
      }
    },
    [onSelect, pattern]
  );

  const getCategoryBadgeClasses = () => {
    const baseClasses = 'px-2 py-1 text-xs font-medium rounded-full';
    if (pattern.category === 'built-in') {
      return `${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`;
    }
    return `${baseClasses} bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200`;
  };

  return (
    <article
      role="article"
      tabIndex={0}
      className={`
        bg-white dark:bg-gray-800
        border dark:border-gray-700
        rounded-lg
        shadow-md
        hover:shadow-lg
        transition-shadow
        cursor-pointer
        p-4
        flex flex-col
        gap-3
        ${isSelected ? 'ring-2 ring-blue-500' : ''}
      `}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      aria-label={`Pattern: ${pattern.name}`}
    >
      {/* Header: Name and Category Badge */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex-1">
          {pattern.name}
        </h3>
        <span className={getCategoryBadgeClasses()}>{pattern.category}</span>
      </div>

      {/* Description */}
      {pattern.description && (
        <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
          {pattern.description}
        </p>
      )}

      {/* Metadata Row: Action Count and Duration */}
      <div className="flex items-center gap-4 text-sm text-gray-700 dark:text-gray-300">
        <div className="flex items-center gap-1">
          <BoltIcon className="h-4 w-4" />
          <span>{pattern.actions.length} actions</span>
        </div>
        <div className="flex items-center gap-1">
          <ClockIcon className="h-4 w-4" />
          <span>{pattern.duration_minutes} min</span>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 min-h-[24px]">
        {pattern.tags && pattern.tags.length > 0 && pattern.tags.map((tag) => (
          <TagChip key={tag} tag={tag} size="sm" />
        ))}
      </div>

      {/* Action Button */}
      <button
        type="button"
        className="
          mt-2
          w-full
          px-4
          py-2
          bg-blue-600
          hover:bg-blue-700
          dark:bg-blue-500
          dark:hover:bg-blue-600
          text-white
          font-medium
          rounded-md
          transition-colors
          focus:outline-none
          focus:ring-2
          focus:ring-blue-500
          focus:ring-offset-2
          dark:focus:ring-offset-gray-800
        "
        onClick={handleSelectClick}
        aria-label="Use Pattern"
      >
        Use Pattern
      </button>
    </article>
  );
}

PatternCard.propTypes = {
  /** Pattern object with id, name, description, actions, category, tags, and duration */
  pattern: PropTypes.shape({
    pattern_id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    actions: PropTypes.arrayOf(
      PropTypes.shape({
        action_type: PropTypes.string.isRequired,
        action_name: PropTypes.string.isRequired,
        offset_minutes: PropTypes.number.isRequired,
      })
    ).isRequired,
    category: PropTypes.oneOf(['built-in', 'user']).isRequired,
    tags: PropTypes.arrayOf(PropTypes.string),
    duration_minutes: PropTypes.number.isRequired,
  }).isRequired,
  /** Called when card is clicked (to view details) */
  onClick: PropTypes.func.isRequired,
  /** Called when "Use Pattern" button is clicked */
  onSelect: PropTypes.func.isRequired,
  /** Shows selection ring when true */
  isSelected: PropTypes.bool,
};

export default memo(PatternCard);
