import PropTypes from 'prop-types';
import { useEffect, useRef } from 'react';
import { XMarkIcon, ClockIcon } from '@heroicons/react/24/outline';
import MoonPhaseIcon from './MoonPhaseIcon';
import { formatTime, getPatternColor } from './calendarUtils';

/**
 * Get Tailwind color classes for action type badges
 * @param {string} type - Action type (gpio, camera, gps_sync, service)
 * @returns {string} Tailwind classes for badge styling
 */
function getActionTypeColor(type) {
  const colors = {
    gpio: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    camera: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    gps_sync: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    service: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  };
  return colors[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
}

/**
 * Modal dialog showing detailed information about a schedule execution
 *
 * Displays:
 * - Pattern name with color indicator
 * - Start/end times
 * - Trigger information
 * - Moon phase (if available)
 * - List of scheduled actions with timing
 *
 * @component
 * @example
 * <ExecutionDetailModal
 *   isOpen={showModal}
 *   onClose={() => setShowModal(false)}
 *   execution={{
 *     pattern_id: "pattern-1",
 *     pattern_name: "Night Photography",
 *     start_time: "2025-01-15T20:00:00",
 *     end_time: "2025-01-15T22:00:00",
 *     trigger_info: "Triggered by sunset",
 *     actions: [
 *       { time: "2025-01-15T20:00:00", action_name: "Turn on lights", action_type: "gpio", offset_minutes: 0 },
 *       { time: "2025-01-15T20:15:00", action_name: "Take photo", action_type: "camera", offset_minutes: 15 }
 *     ]
 *   }}
 *   moonPhase={{ phase_name: "Full Moon", illumination: 1.0 }}
 * />
 */
function ExecutionDetailModal({ isOpen, onClose, execution, moonPhase }) {
  const modalRef = useRef(null);

  // Handle ESC key and focus trap for accessibility (WCAG 2.1)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      // Focus trap: keep focus within modal
      if (e.key !== 'Tab' || !modalRef.current) return;

      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    // Focus first element on open
    const focusableElements = modalRef.current?.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements?.[0]) {
      focusableElements[0].focus();
    }

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !execution) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        className="max-w-lg w-full mx-4 bg-white dark:bg-gray-800 rounded-lg shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${getPatternColor(execution.pattern_id)}`}
              aria-hidden="true"
            />
            <h2
              id="modal-title"
              className="text-lg font-semibold text-gray-900 dark:text-white"
            >
              {execution.pattern_name}
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4">
          {/* Time info */}
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <ClockIcon className="h-5 w-5" />
            <span>
              {formatTime(execution.start_time)} - {formatTime(execution.end_time)}
            </span>
          </div>

          {/* Trigger info */}
          {execution.trigger_info && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {execution.trigger_info}
            </p>
          )}

          {/* Moon phase */}
          {moonPhase && (
            <div className="flex items-center gap-2">
              <MoonPhaseIcon phase={moonPhase} size="md" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {moonPhase.phase_name}
              </span>
            </div>
          )}

          {/* Actions list */}
          {execution.actions && execution.actions.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2 text-gray-900 dark:text-white">
                Actions
              </h3>
              <ul className="space-y-2">
                {execution.actions.map((action, idx) => (
                  <li
                    key={idx}
                    className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
                  >
                    <span className="text-gray-500 dark:text-gray-400 font-mono">
                      +{action.offset_minutes}m
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${getActionTypeColor(action.action_type)}`}
                    >
                      {action.action_type}
                    </span>
                    <span>{action.action_name}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

ExecutionDetailModal.propTypes = {
  /** Whether the modal is open */
  isOpen: PropTypes.bool.isRequired,
  /** Callback to close the modal */
  onClose: PropTypes.func.isRequired,
  /** Execution details to display */
  execution: PropTypes.shape({
    /** Unique pattern identifier */
    pattern_id: PropTypes.string.isRequired,
    /** Human-readable pattern name */
    pattern_name: PropTypes.string.isRequired,
    /** ISO datetime string for execution start */
    start_time: PropTypes.string.isRequired,
    /** ISO datetime string for execution end */
    end_time: PropTypes.string.isRequired,
    /** Optional description of what triggered this execution */
    trigger_info: PropTypes.string,
    /** List of actions in this execution */
    actions: PropTypes.arrayOf(
      PropTypes.shape({
        /** ISO datetime string for action execution */
        time: PropTypes.string.isRequired,
        /** Human-readable action name */
        action_name: PropTypes.string.isRequired,
        /** Action type (gpio, camera, gps_sync, service) */
        action_type: PropTypes.string.isRequired,
        /** Minutes offset from execution start */
        offset_minutes: PropTypes.number.isRequired,
        /** Optional action description */
        description: PropTypes.string,
      })
    ),
  }),
  /** Moon phase data for the execution date */
  moonPhase: PropTypes.shape({
    /** Phase name (New Moon, Full Moon, etc.) */
    phase_name: PropTypes.string.isRequired,
    /** Illumination percentage (0-1) */
    illumination: PropTypes.number,
  }),
};

export default ExecutionDetailModal;
