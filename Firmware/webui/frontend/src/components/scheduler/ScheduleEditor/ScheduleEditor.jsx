import { useState, useEffect, useRef, useCallback, useMemo, useLayoutEffect } from 'react';
import PropTypes from 'prop-types';
import { PencilIcon, TrashIcon, DocumentDuplicateIcon } from '@heroicons/react/24/outline';
import RoutineList from './RoutineList';
import ConflictPanel from './ConflictPanel';
import ActivationPanel from './ActivationPanel';
import CronLimitWarning from '../CronLimitWarning';
import ConfirmDialog from '../../common/ConfirmDialog';
import { SCHEDULE_LIMITS } from './constants';
import { RoutinePropType } from './propTypes';
import { generateUUID } from '../../../utils/uuid';
import { useSchedule } from '../../../hooks/useSchedules';
import { useValidateDraft } from '../../../hooks/useValidateDraft';

/** Delay before focusing name input to allow drawer animation to start */
const FOCUS_DELAY_MS = 100;

/**
 * Known error codes and their user-friendly messages.
 * These codes are returned by the backend in the 'code' field of error responses.
 * Issue #385 review: Standardize error codes between backend and frontend.
 */
const KNOWN_ERROR_CODES = {
  NETWORK_ERROR: 'Unable to save. Please check your connection.',
  VALIDATION_ERROR: 'Please fix the errors above.',
  NOT_FOUND: 'Schedule not found. It may have been deleted.',
  CONFLICT_ERROR: 'Schedule has conflicts that must be resolved.',
  ACTIVATION_ERROR: 'Failed to activate schedule.',
  SERVER_ERROR: 'Server error. Please try again later.',
};

/**
 * Sanitize error messages for safe display
 * - Maps known error codes to user-friendly messages
 * - Checks both error.code and error.response.data.code (API responses)
 * - Strips HTML tags as defense-in-depth
 * - Truncates long messages to 200 characters
 *
 * Note: React automatically escapes text content when rendering,
 * but we strip HTML tags as additional defense-in-depth.
 *
 * Issue #385 review: Standardize error codes between backend and frontend.
 *
 * @param {Error} error - The error object
 * @returns {string} Sanitized error message
 */
const sanitizeErrorMessage = (error) => {
  // Check for known error codes from API response first (axios pattern)
  const apiCode = error?.response?.data?.code;
  if (apiCode && KNOWN_ERROR_CODES[apiCode]) {
    return KNOWN_ERROR_CODES[apiCode];
  }

  // Check for known error codes on the error object itself
  if (error?.code && KNOWN_ERROR_CODES[error.code]) {
    return KNOWN_ERROR_CODES[error.code];
  }

  // Get message from API response or error object, with fallback
  let message = String(
    error?.response?.data?.error || error?.message || 'Failed to save schedule'
  );

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
 * A drawer/panel component for viewing, creating, and editing schedules.
 * Opens in read-only view mode by default for existing schedules.
 * Combines trigger configuration, event pattern selection, date range,
 * and preview sections into a unified editing experience.
 *
 * @component
 * @example
 * <ScheduleEditor
 *   isOpen={true}
 *   onSave={(schedule) => console.log('Save:', schedule)}
 *   onCancel={() => console.log('Cancel')}
 *   onDelete={(scheduleId) => console.log('Delete:', scheduleId)}
 * />
 */
const ScheduleEditor = ({
  isOpen,
  schedule = null,
  onSave,
  onCancel,
  onDelete,
  onClone,
  isDeleting = false,
  isCloning = false,
}) => {
  // Refs
  const nameInputRef = useRef(null);
  // Track requested schedule ID to prevent race conditions (Issue #385)
  const requestedScheduleRef = useRef(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [routines, setRoutines] = useState([]);
  const [useSecondsTiming, setUseSecondsTiming] = useState(false);
  const [isAddingRoutine, setIsAddingRoutine] = useState(false);

  // UI state
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [isViewMode, setIsViewMode] = useState(true);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Determine if editing existing schedule (memoized to prevent recalculation on every render)
  const isEditMode = useMemo(() => Boolean(schedule?.schedule_id), [schedule?.schedule_id]);

  // Fetch full schedule data when editing (list endpoint only returns summaries without routines)
  const { data: fullSchedule, isLoading: isLoadingSchedule } = useSchedule(
    isOpen && isEditMode ? schedule?.schedule_id : null
  );

  // Track unsaved changes by comparing current form state to loaded data
  const hasUnsavedChanges = useMemo(() => {
    if (!isEditMode || !fullSchedule) return true; // New schedule always has "unsaved" state
    if (name !== (fullSchedule.name || '')) return true;
    if (description !== (fullSchedule.description || '')) return true;
    // Compare routine count as a simple heuristic (deep comparison is expensive)
    if (routines.length !== (fullSchedule.routines || []).length) return true;
    return false;
  }, [isEditMode, fullSchedule, name, description, routines.length]);

  // Draft validation for conflict detection
  const {
    validateDraft,
    conflictReport,
    isValidating,
    isError: isValidationError,
    error: validationError,
    reset: resetValidation,
  } = useValidateDraft();

  /**
   * Reset form when schedule changes (before new data loads)
   * This prevents showing stale data from the previous schedule
   */
  useEffect(() => {
    if (isOpen && isEditMode) {
      // Clear form while loading new schedule data
      setName('');
      setDescription('');
      setRoutines([]);
      setIsAddingRoutine(false);
      setErrors({});
      setIsViewMode(true); // Existing schedules open in view mode
      setShowDeleteConfirm(false);
      resetValidation();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- Only reset on schedule_id change, not drawer open/close
  }, [schedule?.schedule_id]);

  /**
   * Set view mode based on whether editing existing or creating new
   * - Existing schedules: Open in view mode (read-only)
   * - New schedules: Open directly in edit mode
   */
  useEffect(() => {
    if (isOpen) {
      setIsViewMode(isEditMode); // View mode for existing, edit mode for new
    }
  }, [isOpen, isEditMode]);

  /**
   * Track requested schedule ID to detect stale responses (Issue #385)
   * This ref is updated synchronously when schedule changes, allowing
   * the form initialization effect to ignore stale fetch responses.
   */
  useLayoutEffect(() => {
    requestedScheduleRef.current = isEditMode ? schedule?.schedule_id : null;
  }, [isEditMode, schedule?.schedule_id]);

  /**
   * Initialize form from schedule data
   * In edit mode, use fullSchedule (fetched from API with complete data including routines)
   * In create mode, reset to defaults
   */
  useEffect(() => {
    // Ignore stale responses from previous schedule fetches (Issue #385)
    if (isEditMode && fullSchedule?.schedule_id !== requestedScheduleRef.current) {
      return;
    }

    if (isEditMode && fullSchedule && fullSchedule.schedule_id === schedule?.schedule_id) {
      // Only populate when fetched data matches the requested schedule
      setName(fullSchedule.name || '');
      setDescription(fullSchedule.description || '');
      setRoutines(fullSchedule.routines || []);
      setIsAddingRoutine(false);
      setErrors({});
      resetValidation();
    } else if (!isEditMode && isOpen) {
      // Reset to defaults for new schedule
      setName('');
      setDescription('');
      setRoutines([]);
      setUseSecondsTiming(false);
      setIsAddingRoutine(false);
      setErrors({});
      resetValidation();
    }
  }, [isEditMode, fullSchedule, isOpen, schedule?.schedule_id, resetValidation]);

  /**
   * Validate routines for conflicts when they change
   * The hook handles debouncing (400ms) to avoid excessive API calls
   */
  useEffect(() => {
    if (isOpen && routines.length > 0) {
      validateDraft(routines);
    }
  }, [isOpen, routines, validateDraft]);

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

  /**
   * Handle switching to edit mode
   */
  const handleEnterEditMode = useCallback(() => {
    setIsViewMode(false);
  }, []);

  /**
   * Handle cancel in edit mode
   * - For existing schedules: Return to view mode and reset form to original data
   * - For new schedules: Close the editor
   */
  const handleCancelEdit = useCallback(() => {
    if (isEditMode && fullSchedule) {
      // Return to view mode and reset form to original values
      setName(fullSchedule.name || '');
      setDescription(fullSchedule.description || '');
      setRoutines(fullSchedule.routines || []);
      setErrors({});
      setIsViewMode(true);
    } else {
      // New schedule: just close
      onCancel();
    }
  }, [isEditMode, fullSchedule, onCancel]);

  /**
   * Handle delete button click - show confirmation dialog
   */
  const handleDeleteClick = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleDeleteConfirm = useCallback(() => {
    if (onDelete && schedule?.schedule_id) {
      onDelete(schedule.schedule_id);
    }
    setShowDeleteConfirm(false);
  }, [onDelete, schedule?.schedule_id]);

  /**
   * Handle delete cancel
   */
  const handleDeleteCancel = useCallback(() => {
    setShowDeleteConfirm(false);
  }, []);

  /**
   * Handle clone button click (non-destructive, no confirmation needed)
   */
  const handleCloneClick = useCallback(() => {
    if (onClone && schedule?.schedule_id) {
      onClone(schedule.schedule_id);
    }
  }, [onClone, schedule?.schedule_id]);

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
        className="fixed inset-y-0 right-0 w-full max-w-4xl bg-white dark:bg-gray-900
                   shadow-xl z-50 flex flex-col
                   transform transition-transform duration-300 ease-in-out"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {isEditMode
              ? (isViewMode ? 'View Schedule' : 'Edit Schedule')
              : 'Create Schedule'}
          </h2>
          <div className="flex items-center gap-2">
            {/* Edit button - only shown in view mode for existing schedules */}
            {isEditMode && isViewMode && !isLoadingSchedule && (
              <button
                type="button"
                onClick={handleEnterEditMode}
                className="inline-flex items-center gap-1.5 px-3 py-1.5
                           text-sm font-medium rounded-md
                           text-gray-700 bg-white border border-gray-300
                           hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                           dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600"
              >
                <PencilIcon className="h-4 w-4" aria-hidden="true" />
                Edit
              </button>
            )}
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
        </div>

        {/* Two-column content area */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left Column: Form */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8">
            {/* Loading state when fetching full schedule data */}
            {isEditMode && isLoadingSchedule ? (
              <div className="flex items-center justify-center h-48">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Loading schedule...</p>
                </div>
              </div>
            ) : (
            <>
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
                  disabled={isSaving || isViewMode}
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
                  disabled={isSaving || isViewMode}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600
                             bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                             focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y
                             disabled:opacity-50 disabled:cursor-not-allowed"
                  placeholder="Optional description"
                  aria-label="Description"
                />
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
                disabled={isSaving || isViewMode}
              />
              {errors.routines && (
                <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.routines}</p>
              )}
            </div>

            {/* Save Error */}
            {errors.save && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">{errors.save}</p>
              </div>
            )}
            </>
            )}
          </div>

          {/* Right Column: Activation & Conflict Panel */}
          <div className="w-80 border-l border-gray-200 dark:border-gray-700 overflow-y-auto
                          bg-gray-50 dark:bg-gray-800/50 px-4 py-6 flex-shrink-0 space-y-6">
            {/* Activation Panel (only for existing schedules) */}
            {isEditMode && !isLoadingSchedule && fullSchedule?.schedule_id && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
                  Activation
                </h3>
                <ActivationPanel
                  scheduleId={fullSchedule.schedule_id}
                  routineCount={routines.length}
                  hasUnsavedChanges={hasUnsavedChanges}
                />
              </div>
            )}

            {/* Conflict Detection */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
                Conflict Detection
              </h3>
              <ConflictPanel
                conflictReport={conflictReport}
                isValidating={isValidating}
                isError={isValidationError}
                error={validationError}
              />
            </div>

            {/* Cron entry limit warning (Issue #385) */}
            {conflictReport?.estimated_entries && (
              <CronLimitWarning estimatedEntries={conflictReport.estimated_entries} />
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          {/* Left side - Clone and Delete buttons (only for existing schedules) */}
          <div className="flex items-center gap-2">
            {isEditMode && isViewMode && onClone && (
              <button
                type="button"
                onClick={handleCloneClick}
                disabled={isCloning || isLoadingSchedule}
                className="inline-flex items-center gap-1.5 px-4 py-2
                           text-gray-700 bg-white border border-gray-300 rounded-md
                           hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                           dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <DocumentDuplicateIcon className="h-4 w-4" aria-hidden="true" />
                {isCloning ? 'Cloning...' : 'Clone'}
              </button>
            )}
            {isEditMode && onDelete && (
              <button
                type="button"
                onClick={handleDeleteClick}
                disabled={isSaving || isDeleting || isLoadingSchedule}
                className="inline-flex items-center gap-1.5 px-4 py-2
                           text-red-700 bg-white border border-red-300 rounded-md
                           hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500
                           dark:bg-gray-700 dark:text-red-400 dark:border-red-900 dark:hover:bg-red-900/20
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <TrashIcon className="h-4 w-4" aria-hidden="true" />
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            )}
          </div>

          {/* Right side - Close/Cancel/Save buttons */}
          <div className="flex items-center gap-3">
            {isViewMode ? (
              /* View mode: just a Close button */
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600
                           text-gray-700 dark:text-gray-300 rounded-md
                           hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            ) : (
              /* Edit mode: Cancel and Save buttons */
              <>
                <button
                  type="button"
                  onClick={handleCancelEdit}
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
                  disabled={isSaving || (isEditMode && isLoadingSchedule)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md
                             hover:bg-blue-700 transition-colors
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          isOpen={showDeleteConfirm}
          title="Delete Schedule"
          message={`Are you sure you want to delete "${schedule?.name || 'this schedule'}"? This action cannot be undone.`}
          onConfirm={handleDeleteConfirm}
          onClose={handleDeleteCancel}
        />
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
  /** Callback when schedule is deleted. Receives schedule_id. */
  onDelete: PropTypes.func,
  /** Callback when schedule is cloned. Receives schedule_id. */
  onClone: PropTypes.func,
  /** Loading state for deletion */
  isDeleting: PropTypes.bool,
  /** Loading state for cloning */
  isCloning: PropTypes.bool,
};

export default ScheduleEditor;
