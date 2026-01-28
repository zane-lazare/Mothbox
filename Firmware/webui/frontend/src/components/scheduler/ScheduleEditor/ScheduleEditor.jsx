import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';
import RoutineList from './RoutineList';
import PreviewSection from './PreviewSection';
import { SCHEDULE_LIMITS } from './constants';
import { RoutinePropType } from './propTypes';
import { generateUUID } from '../../../utils/uuid';

/** Delay before focusing name input to allow drawer animation to start */
const FOCUS_DELAY_MS = 100;

/**
 * Known error codes and their user-friendly messages
 */
const KNOWN_ERROR_CODES = {
  NETWORK_ERROR: 'Unable to save. Please check your connection.',
  VALIDATION_ERROR: 'Please fix the errors above.',
  SERVER_ERROR: 'Server error. Please try again later.',
};

/**
 * Sanitize error messages for safe display
 * - Maps known error codes to user-friendly messages
 * - Strips HTML tags as defense-in-depth
 * - Truncates long messages to 200 characters
 *
 * Note: React automatically escapes text content when rendering,
 * but we strip HTML tags as additional defense-in-depth.
 *
 * @param {Error} error - The error object
 * @returns {string} Sanitized error message
 */
const sanitizeErrorMessage = (error) => {
  // Check for known error codes first
  if (error?.code && KNOWN_ERROR_CODES[error.code]) {
    return KNOWN_ERROR_CODES[error.code];
  }

  // Get message or use fallback
  let message = String(error?.message || 'Failed to save schedule');

  // Strip HTML tags as defense-in-depth using iterative approach
  // to handle incomplete/malformed tags like "<script" without closing ">"
  let previousLength;
  do {
    previousLength = message.length;
    // Remove complete tags and incomplete opening tags
    message = message.replace(/<[^>]*>?/g, '');
  } while (message.length < previousLength);

  // Truncate to 200 characters
  return message.length > 200 ? message.slice(0, 200) + '...' : message;
};

/**
 * ScheduleEditor Component
 *
 * A drawer/panel component for creating and editing schedules.
 * Combines trigger configuration, event pattern selection, date range,
 * and preview sections into a unified editing experience.
 *
 * @component
 * @example
 * <ScheduleEditor
 *   isOpen={true}
 *   onSave={(schedule) => console.log('Save:', schedule)}
 *   onCancel={() => console.log('Cancel')}
 * />
 */
const ScheduleEditor = ({
  isOpen,
  schedule = null,
  onSave,
  onCancel,
}) => {
  // Refs
  const nameInputRef = useRef(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [routines, setRoutines] = useState([]);
  const [useSecondsTiming, setUseSecondsTiming] = useState(false);
  const [isAddingRoutine, setIsAddingRoutine] = useState(false);

  // UI state
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  // Determine if editing existing schedule (memoized to prevent recalculation on every render)
  const isEditMode = useMemo(() => Boolean(schedule?.schedule_id), [schedule?.schedule_id]);

  /**
   * Initialize form from schedule prop
   */
  useEffect(() => {
    if (schedule) {
      setName(schedule.name || '');
      setDescription(schedule.description || '');
      setRoutines(schedule.routines || []);
      setUseSecondsTiming(schedule.use_seconds_timing || false);
      setIsAddingRoutine(false);
    } else {
      // Reset to defaults for new schedule
      setName('');
      setDescription('');
      setRoutines([]);
      setUseSecondsTiming(false);
      setIsAddingRoutine(false);
    }
    setErrors({});
  }, [schedule]);

  /**
   * Focus name input when drawer opens
   */
  useEffect(() => {
    if (isOpen && nameInputRef.current) {
      const timer = setTimeout(() => nameInputRef.current?.focus(), FOCUS_DELAY_MS);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  /**
   * Handle Escape key to close
   */
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  /**
   * Body scroll lock effect.
   *
   * ASSUMPTION: Only one drawer/modal is open at a time in this application.
   * If multiple concurrent drawers are needed, consider using a library like
   * body-scroll-lock for proper reference counting.
   */
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  /**
   * Focus trap implementation for WCAG 2.1.2 compliance.
   *
   * This implementation queries focusable elements on each Tab keypress.
   * If drawer content becomes highly dynamic (conditional fields based on
   * server responses), consider migrating to focus-trap-react for robustness.
   *
   * Current implementation handles static drawer content correctly.
   */
  useEffect(() => {
    if (!isOpen) return;

    const drawer = document.querySelector('[data-testid="schedule-editor-drawer"]');
    if (!drawer) return;

    const getFocusableElements = () => {
      return drawer.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
    };

    const handleKeyDown = (e) => {
      if (e.key !== 'Tab') return;

      const focusableElements = getFocusableElements();
      if (focusableElements.length === 0) return;

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

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  /**
   * Handle backdrop click
   */
  const handleBackdropClick = useCallback(
    (e) => {
      if (e.target === e.currentTarget) {
        onCancel();
      }
    },
    [onCancel]
  );

  /**
   * Validate form
   */
  const validate = useCallback(() => {
    const newErrors = {};

    if (!name.trim()) {
      newErrors.name = 'Schedule name is required';
    } else if (name.length > SCHEDULE_LIMITS.NAME_MAX_LENGTH) {
      newErrors.name = `Name must be ${SCHEDULE_LIMITS.NAME_MAX_LENGTH} characters or less`;
    }

    if (routines.length === 0) {
      newErrors.routines = 'At least one routine is required';
    } else if (routines.some(r => !r.trigger || !r.actions || r.actions.length === 0)) {
      newErrors.routines = 'All routines must have a trigger and at least one action';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [name, routines]);

  /**
   * Handle save
   */
  const handleSave = useCallback(async () => {
    if (!validate()) {
      return;
    }

    setIsSaving(true);

    try {
      const scheduleData = {
        schedule_id: schedule?.schedule_id || generateUUID(),
        name: name.trim(),
        description: description.trim(),
        routines,
        use_seconds_timing: useSecondsTiming,
      };

      await onSave(scheduleData);
    } catch (error) {
      setErrors({ save: sanitizeErrorMessage(error) });
    } finally {
      setIsSaving(false);
    }
  }, [
    validate,
    schedule?.schedule_id,
    name,
    description,
    routines,
    useSecondsTiming,
    onSave,
  ]);

  /**
   * Handle name change
   */
  const handleNameChange = (e) => {
    setName(e.target.value);
    if (errors.name) {
      setErrors((prev) => ({ ...prev, name: undefined }));
    }
  };

  /**
   * Handle description change
   */
  const handleDescriptionChange = (e) => {
    setDescription(e.target.value);
  };

  /**
   * Handle routine update
   */
  const handleRoutineUpdate = useCallback((updatedRoutine) => {
    setRoutines((prev) =>
      prev.map((r) =>
        r.routine_id === updatedRoutine.routine_id ? updatedRoutine : r
      )
    );
    if (errors.routines) {
      setErrors((prev) => ({ ...prev, routines: undefined }));
    }
  }, [errors.routines]);

  /**
   * Handle routine delete
   */
  const handleRoutineDelete = useCallback((routineId) => {
    setRoutines((prev) => prev.filter((r) => r.routine_id !== routineId));
  }, []);

  /**
   * Handle routine add
   */
  const handleRoutineAdd = useCallback((routine) => {
    setRoutines((prev) => [...prev, routine]);
    if (errors.routines) {
      setErrors((prev) => ({ ...prev, routines: undefined }));
    }
  }, [errors.routines]);

  /**
   * Start adding a new routine
   */
  const handleStartAddRoutine = useCallback(() => {
    setIsAddingRoutine(true);
  }, []);

  /**
   * Cancel adding a new routine
   */
  const handleCancelAddRoutine = useCallback(() => {
    setIsAddingRoutine(false);
  }, []);

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="drawer-backdrop"
        className="fixed inset-0 bg-black/50 z-40"
        onClick={handleBackdropClick}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        data-testid="schedule-editor-drawer"
        role="dialog"
        aria-label="Schedule Editor"
        aria-modal="true"
        className="fixed inset-y-0 right-0 w-full max-w-2xl bg-white dark:bg-gray-900
                   shadow-xl z-50 flex flex-col
                   transform transition-transform duration-300 ease-in-out"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {isEditMode ? 'Edit Schedule' : 'Create Schedule'}
          </h2>
          <button
            type="button"
            onClick={onCancel}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200
                       rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8">
          {/* Name and Description */}
          <div className="space-y-4">
            <div>
              <label
                htmlFor="schedule-name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Schedule Name *
              </label>
              <input
                ref={nameInputRef}
                id="schedule-name"
                type="text"
                value={name}
                onChange={handleNameChange}
                maxLength={SCHEDULE_LIMITS.NAME_MAX_LENGTH}
                disabled={isSaving}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="Enter schedule name"
                aria-label="Schedule name"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="schedule-description"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Description
              </label>
              <textarea
                id="schedule-description"
                value={description}
                onChange={handleDescriptionChange}
                maxLength={SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH}
                rows={3}
                disabled={isSaving}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600
                           bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y
                           disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="Optional description"
                aria-label="Description"
              />
            </div>

            {/* Advanced timing options */}
            <div className="pt-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useSecondsTiming}
                  onChange={(e) => setUseSecondsTiming(e.target.checked)}
                  disabled={isSaving}
                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600
                             text-blue-600 focus:ring-blue-500 focus:ring-2
                             disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Enable seconds-level timing
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {useSecondsTiming
                      ? 'You can set exact seconds for each action'
                      : 'Actions at the same minute are auto-staggered by 5 seconds based on list order'}
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Routines Section */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
              Routines *
            </h3>
            <RoutineList
              routines={routines}
              onRoutineUpdate={handleRoutineUpdate}
              onRoutineDelete={handleRoutineDelete}
              onRoutineAdd={handleRoutineAdd}
              isAddingRoutine={isAddingRoutine}
              onStartAddRoutine={handleStartAddRoutine}
              onCancelAddRoutine={handleCancelAddRoutine}
              disabled={isSaving}
              useSecondsTiming={useSecondsTiming}
            />
            {errors.routines && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.routines}</p>
            )}
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Preview */}
          <PreviewSection
            routines={routines}
          />

          {/* Save Error */}
          {errors.save && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <p className="text-sm text-red-600 dark:text-red-400">{errors.save}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSaving}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-300 rounded-md
                       hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </>
  );
};

ScheduleEditor.propTypes = {
  /** Whether the editor drawer is open */
  isOpen: PropTypes.bool.isRequired,
  /** Schedule to edit (null for new). Contains routines with per-routine triggers. */
  schedule: PropTypes.shape({
    schedule_id: PropTypes.string,
    name: PropTypes.string,
    description: PropTypes.string,
    routines: PropTypes.arrayOf(RoutinePropType),
    use_seconds_timing: PropTypes.bool,
  }),
  /** Callback when schedule is saved. Receives complete schedule object. */
  onSave: PropTypes.func.isRequired,
  /** Callback when editor is cancelled/closed */
  onCancel: PropTypes.func.isRequired,
};

export default ScheduleEditor;
