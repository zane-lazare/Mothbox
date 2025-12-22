import { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  XMarkIcon,
  ClockIcon,
  BoltIcon,
  CameraIcon,
  MapPinIcon,
  CogIcon,
} from '@heroicons/react/24/outline';
import TagChip from '@/components/gallery/TagChip';

const actionTypeIcons = {
  gpio: BoltIcon,
  camera: CameraIcon,
  gps_sync: MapPinIcon,
  service: CogIcon,
};

const actionTypeLabels = {
  gpio: 'GPIO',
  camera: 'Camera',
  gps_sync: 'GPS Sync',
  service: 'Service',
};

function PatternDetailsDrawer({ pattern, isOpen, onClose, onSelect }) {
  const dialogRef = useRef(null);

  // Focus first button when drawer opens (accessibility)
  useEffect(() => {
    if (isOpen && dialogRef.current) {
      const firstButton = dialogRef.current.querySelector('button');
      firstButton?.focus();
    }
  }, [isOpen]);

  // Handle escape key and body scroll lock
  // Note: This hook must be called before any early returns to satisfy Rules of Hooks
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  // Don't render if closed or no pattern
  if (!isOpen || !pattern) {
    return null;
  }

  // Sort actions by offset_minutes
  const sortedActions = [...(pattern.actions || [])].sort(
    (a, b) => a.offset_minutes - b.offset_minutes
  );

  const headerId = 'pattern-details-header';

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-labelledby={headerId}
        className="fixed inset-y-0 right-0 flex max-w-full"
      >
        <div className="w-screen max-w-md max-md:max-w-full">
          <div className="flex h-full flex-col overflow-y-auto bg-white shadow-xl dark:bg-gray-800">
            {/* Header */}
            <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2
                    id={headerId}
                    className="text-2xl font-semibold text-gray-900 dark:text-white"
                  >
                    {pattern.name}
                  </h2>
                  <div className="mt-2">
                    <span
                      className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                        pattern.category === 'built-in'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                      }`}
                    >
                      {pattern.category}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="ml-4 rounded-md text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  aria-label="Close drawer"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
              {/* Description */}
              {pattern.description && (
                <div className="mb-6">
                  <h3 className="mb-2 text-sm font-medium text-gray-900 dark:text-white">
                    Description
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    {pattern.description}
                  </p>
                </div>
              )}

              {/* Metadata */}
              <div className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
                <div className="space-y-2 text-sm">
                  <div className="flex items-center text-gray-700 dark:text-gray-300">
                    <ClockIcon className="mr-2 h-5 w-5" />
                    <span className="font-medium">Duration:</span>
                    <span className="ml-2">{pattern.duration_minutes} min</span>
                  </div>
                  <div className="flex items-center text-gray-700 dark:text-gray-300">
                    <BoltIcon className="mr-2 h-5 w-5" />
                    <span className="font-medium">Actions:</span>
                    <span className="ml-2">{pattern.actions?.length || 0} actions</span>
                  </div>
                  {pattern.source_schedule && (
                    <div className="flex items-center text-gray-700 dark:text-gray-300">
                      <span className="font-medium">Source:</span>
                      <span className="ml-2 font-mono text-xs">
                        {pattern.source_schedule}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Tags */}
              {pattern.tags && pattern.tags.length > 0 && (
                <div className="mb-6">
                  <h3 className="mb-2 text-sm font-medium text-gray-900 dark:text-white">
                    Tags
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {pattern.tags.map((tag) => (
                      <TagChip key={tag} tag={tag} />
                    ))}
                  </div>
                </div>
              )}

              {/* Actions Timeline */}
              <div className="mb-6">
                <h3 className="mb-4 text-sm font-medium text-gray-900 dark:text-white">
                  Actions Timeline
                </h3>

                {sortedActions.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No actions defined
                  </p>
                ) : (
                  <div className="space-y-4">
                    {sortedActions.map((action, index) => {
                      const Icon = actionTypeIcons[action.action_type] || CogIcon;
                      const isLast = index === sortedActions.length - 1;

                      return (
                        <div key={`${action.action_name}-${action.offset_minutes}-${index}`} className="relative">
                          <div className="flex items-start">
                            {/* Timeline dot and line */}
                            <div className="relative mr-4 flex flex-col items-center">
                              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                                <Icon className="h-4 w-4 text-blue-600 dark:text-blue-300" />
                              </div>
                              {!isLast && (
                                <div className="absolute top-8 h-full w-0.5 bg-gray-300 dark:bg-gray-600" />
                              )}
                            </div>

                            {/* Action content */}
                            <div className="flex-1 pb-8">
                              <div className="flex items-baseline">
                                <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
                                  +{action.offset_minutes} min
                                </span>
                                <span className="mx-2 text-gray-400">·</span>
                                <span className="font-mono text-sm text-gray-700 dark:text-gray-300">
                                  {action.action_name}
                                </span>
                              </div>
                              <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                {actionTypeLabels[action.action_type] || action.action_type}
                                {action.description && (
                                  <>
                                    {' - '}
                                    {action.description}
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 px-6 py-4 dark:border-gray-700">
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => onSelect(pattern)}
                  className="flex-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-500 dark:hover:bg-blue-600"
                >
                  Use This Pattern
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

PatternDetailsDrawer.propTypes = {
  pattern: PropTypes.shape({
    pattern_id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    actions: PropTypes.arrayOf(
      PropTypes.shape({
        action_type: PropTypes.oneOf(['gpio', 'camera', 'gps_sync', 'service']).isRequired,
        action_name: PropTypes.string.isRequired,
        offset_minutes: PropTypes.number.isRequired,
        description: PropTypes.string,
      })
    ),
    category: PropTypes.oneOf(['built-in', 'user']).isRequired,
    tags: PropTypes.arrayOf(PropTypes.string),
    duration_minutes: PropTypes.number.isRequired,
    source_schedule: PropTypes.string,
  }),
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};

export default PatternDetailsDrawer;
