/**
 * SchedulerContext - State management for Scheduler UI
 *
 * Related to Issue #221 - Scheduler UI Context Implementation
 *
 * Provides centralized state management for schedules, editing state,
 * preview events, validation, and UI state with localStorage persistence.
 *
 * Error Boundary Integration:
 * This context provides error state (error, errorInfo) for integration with
 * React Error Boundaries. Usage example:
 *
 * @example
 * // In an Error Boundary component
 * class SchedulerErrorBoundary extends React.Component {
 *   componentDidCatch(error, errorInfo) {
 *     // Store error in context for recovery UI
 *     this.props.setError(error, errorInfo)
 *   }
 *
 *   render() {
 *     if (this.props.hasError) {
 *       return <ErrorRecoveryUI onRetry={this.props.clearError} />
 *     }
 *     return this.props.children
 *   }
 * }
 *
 * // Wrap with context consumer
 * function SchedulerErrorBoundaryWrapper({ children }) {
 *   const { errorActions, computed } = useSchedulerContext()
 *   return (
 *     <SchedulerErrorBoundary
 *       setError={errorActions.setError}
 *       clearError={errorActions.clearError}
 *       hasError={computed.hasError}
 *     >
 *       {children}
 *     </SchedulerErrorBoundary>
 *   )
 * }
 */
import React, { createContext, useReducer, useMemo, useCallback, useEffect } from 'react'
import PropTypes from 'prop-types'

const SchedulerContext = createContext(null)

// localStorage keys for persisting UI state
const STORAGE_KEY_DRAWER = 'mothbox-scheduler-drawer-open'
const STORAGE_KEY_SECTIONS = 'mothbox-scheduler-sections'

/**
 * Load a value from localStorage with fallback to default
 * @param {string} key - localStorage key
 * @param {*} defaultValue - Default value if key not found or error occurs
 * @returns {*} Parsed value or defaultValue
 */
function loadFromStorage(key, defaultValue) {
  try {
    const stored = localStorage.getItem(key)
    return stored ? JSON.parse(stored) : defaultValue
  } catch (error) {
    // Log in development for debugging localStorage issues (quota, corruption, etc.)
    if (import.meta.env.DEV) {
      console.warn(`Failed to load ${key} from localStorage:`, error.message)
    }
    return defaultValue
  }
}

/**
 * Save a value to localStorage with error handling
 * @param {string} key - localStorage key
 * @param {*} value - Value to save (will be JSON stringified)
 */
function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    // Log in development for debugging localStorage issues (quota exceeded, private browsing)
    if (import.meta.env.DEV) {
      console.warn(`Failed to save ${key} to localStorage:`, error.message)
    }
    // Gracefully ignore in production - UI will still work, just without persistence
  }
}

// Action types
const ActionTypes = {
  SET_SCHEDULES: 'SET_SCHEDULES',
  SET_ACTIVE_SCHEDULE: 'SET_ACTIVE_SCHEDULE',
  CLEAR_ACTIVE_SCHEDULE: 'CLEAR_ACTIVE_SCHEDULE',
  SET_EDITING_SCHEDULE: 'SET_EDITING_SCHEDULE',
  CLEAR_EDITING_SCHEDULE: 'CLEAR_EDITING_SCHEDULE',
  UPDATE_EDITING_SCHEDULE: 'UPDATE_EDITING_SCHEDULE',
  SET_CREATING: 'SET_CREATING',
  SET_UNSAVED_CHANGES: 'SET_UNSAVED_CHANGES',
  SET_PREVIEW: 'SET_PREVIEW',
  SET_PREVIEW_LOADING: 'SET_PREVIEW_LOADING',
  SET_PREVIEW_ERROR: 'SET_PREVIEW_ERROR',
  CLEAR_PREVIEW: 'CLEAR_PREVIEW',
  SET_CONFLICTS: 'SET_CONFLICTS',
  CLEAR_VALIDATION: 'CLEAR_VALIDATION',
  SET_MOON_PHASES: 'SET_MOON_PHASES',
  SET_VIEW_MODE: 'SET_VIEW_MODE',
  SET_SELECTED_DATE: 'SET_SELECTED_DATE',
  TOGGLE_EXPERT_MODE: 'TOGGLE_EXPERT_MODE',
  TOGGLE_DRAWER: 'TOGGLE_DRAWER',
  TOGGLE_SECTION: 'TOGGLE_SECTION',
  LOAD_STATE: 'LOAD_STATE',
  RESET_STATE: 'RESET_STATE',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
}

// Allowlist for schedule fields (sanitization for UPDATE_EDITING_SCHEDULE)
const SCHEDULE_FIELDS = [
  'id', 'name', 'description', 'events', 'enabled', 'category',
  'triggers', 'created_at', 'modified_at', 'version'
]

// Allowlist for loadable state keys (LOAD_STATE protection)
// Excludes: error, errorInfo (protected from external overwrite)
const LOADABLE_STATE_KEYS = [
  'schedules', 'activeSchedule', 'editingSchedule', 'isCreating',
  'hasUnsavedChanges', 'previewEvents', 'previewLoading', 'previewError',
  'conflicts', 'moonPhases', 'viewMode', 'selectedDate', 'isExpertMode',
  'isDrawerOpen', 'expandedSections'
]

// Initial state
const initialState = {
  // Data state
  schedules: [],
  activeSchedule: null,

  // Edit state
  editingSchedule: null,
  isCreating: false,
  hasUnsavedChanges: false,

  // Preview state
  previewEvents: [],
  previewLoading: false,
  previewError: null,

  // Validation state
  conflicts: [],

  // Moon phase data
  moonPhases: {},

  // UI state
  viewMode: 'list',
  selectedDate: null,
  isExpertMode: false,

  // UI persistence (localStorage)
  isDrawerOpen: loadFromStorage(STORAGE_KEY_DRAWER, true),
  expandedSections: loadFromStorage(STORAGE_KEY_SECTIONS, ['triggers']),

  // Error state for error boundary integration
  error: null,
  errorInfo: null,
}

/**
 * Reducer for scheduler state management
 *
 * VALIDATION STRATEGY:
 * All reducer actions validate their payloads before applying state changes.
 * Invalid payloads result in the current state being returned unchanged (no-op).
 *
 * - Array fields (schedules, events, conflicts): Check `!value || !Array.isArray(value)`
 *   Catches null, undefined, and non-array values in a single condition.
 *
 * - Object fields (updates, newState): Check `!value || typeof value !== 'object' || Array.isArray(value)`
 *   Ensures value is a plain object (not null, undefined, or array).
 *
 * - Primitive fields (strings, booleans): No validation needed; React prop-types
 *   handle type checking at the component level.
 *
 * - Sanitized fields (editingSchedule updates, loadState): Use allowlist filtering
 *   (SCHEDULE_FIELDS, LOADABLE_STATE_KEYS) to prevent prototype pollution.
 *
 * @param {Object} state - Current reducer state
 * @param {Object} action - Action with type and payload
 * @returns {Object} Updated state or current state if validation fails
 */
function schedulerReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_SCHEDULES: {
      const { schedules } = action.payload
      // Validate schedules is an array
      if (!schedules || !Array.isArray(schedules)) {
        return state
      }
      return {
        ...state,
        schedules,
      }
    }

    case ActionTypes.SET_ACTIVE_SCHEDULE: {
      const { schedule } = action.payload
      return {
        ...state,
        activeSchedule: schedule,
      }
    }

    case ActionTypes.CLEAR_ACTIVE_SCHEDULE: {
      return {
        ...state,
        activeSchedule: null,
      }
    }

    case ActionTypes.SET_EDITING_SCHEDULE: {
      const { schedule } = action.payload
      return {
        ...state,
        editingSchedule: schedule,
      }
    }

    case ActionTypes.CLEAR_EDITING_SCHEDULE: {
      return {
        ...state,
        editingSchedule: null,
      }
    }

    /**
     * UPDATE_EDITING_SCHEDULE - Partially update the schedule being edited
     *
     * Security: Only allows updates to fields in SCHEDULE_FIELDS allowlist
     * (defined at line 117) to prevent prototype pollution attacks via
     * malicious keys like __proto__ or constructor.
     *
     * Behavior:
     * - No-op if updates is not a plain object (null, undefined, array rejected)
     * - No-op if editingSchedule is null (nothing to update)
     * - Filters updates to only SCHEDULE_FIELDS keys
     * - No-op if no valid fields remain after filtering
     *
     * @param {Object} action.payload.updates - Partial schedule fields to merge
     */
    case ActionTypes.UPDATE_EDITING_SCHEDULE: {
      const { updates } = action.payload
      // Validate updates is an object and editingSchedule exists
      if (!updates || typeof updates !== 'object' || Array.isArray(updates)) {
        return state
      }
      if (!state.editingSchedule) {
        return state
      }
      // Sanitize updates to only allowed schedule fields
      const sanitizedUpdates = Object.fromEntries(
        Object.entries(updates).filter(([key]) => SCHEDULE_FIELDS.includes(key))
      )
      // If no valid fields remain, don't update state
      if (Object.keys(sanitizedUpdates).length === 0) {
        return state
      }
      return {
        ...state,
        editingSchedule: {
          ...state.editingSchedule,
          ...sanitizedUpdates,
        },
      }
    }

    case ActionTypes.SET_CREATING: {
      const { isCreating } = action.payload
      return {
        ...state,
        isCreating,
      }
    }

    case ActionTypes.SET_UNSAVED_CHANGES: {
      const { hasChanges } = action.payload
      return {
        ...state,
        hasUnsavedChanges: hasChanges,
      }
    }

    case ActionTypes.SET_PREVIEW: {
      const { events } = action.payload
      // Validate events is an array
      if (!events || !Array.isArray(events)) {
        return state
      }
      return {
        ...state,
        previewEvents: events,
      }
    }

    case ActionTypes.SET_PREVIEW_LOADING: {
      const { loading } = action.payload
      return {
        ...state,
        previewLoading: loading,
      }
    }

    case ActionTypes.SET_PREVIEW_ERROR: {
      const { error } = action.payload
      return {
        ...state,
        previewError: error,
      }
    }

    case ActionTypes.CLEAR_PREVIEW: {
      return {
        ...state,
        previewEvents: [],
        previewError: null,
      }
    }

    case ActionTypes.SET_CONFLICTS: {
      const { conflicts } = action.payload
      // Validate conflicts is an array
      if (!conflicts || !Array.isArray(conflicts)) {
        return state
      }
      return {
        ...state,
        conflicts,
      }
    }

    case ActionTypes.CLEAR_VALIDATION: {
      return {
        ...state,
        conflicts: [],
      }
    }

    case ActionTypes.SET_MOON_PHASES: {
      const { phases } = action.payload
      return {
        ...state,
        moonPhases: phases,
      }
    }

    case ActionTypes.SET_VIEW_MODE: {
      const { mode } = action.payload
      return {
        ...state,
        viewMode: mode,
      }
    }

    case ActionTypes.SET_SELECTED_DATE: {
      const { date } = action.payload
      return {
        ...state,
        selectedDate: date,
      }
    }

    case ActionTypes.TOGGLE_EXPERT_MODE: {
      return {
        ...state,
        isExpertMode: !state.isExpertMode,
      }
    }

    case ActionTypes.TOGGLE_DRAWER: {
      return {
        ...state,
        isDrawerOpen: !state.isDrawerOpen,
      }
    }

    case ActionTypes.TOGGLE_SECTION: {
      const { section } = action.payload
      const isExpanded = state.expandedSections.includes(section)

      return {
        ...state,
        expandedSections: isExpanded
          ? state.expandedSections.filter(id => id !== section)
          : [...state.expandedSections, section],
      }
    }

    case ActionTypes.LOAD_STATE: {
      const { newState } = action.payload
      // Validate newState is an object
      if (!newState || typeof newState !== 'object' || Array.isArray(newState)) {
        return state
      }
      // Sanitize to only allowed state keys (protects error, errorInfo)
      const sanitizedState = Object.fromEntries(
        Object.entries(newState).filter(([key]) => LOADABLE_STATE_KEYS.includes(key))
      )
      // If no valid keys remain, don't update state
      if (Object.keys(sanitizedState).length === 0) {
        return state
      }
      return {
        ...state,
        ...sanitizedState,
      }
    }

    case ActionTypes.RESET_STATE: {
      return {
        ...initialState,
        // Override UI persistence to reset to defaults, not localStorage values
        isDrawerOpen: true,
        expandedSections: ['triggers'],
      }
    }

    case ActionTypes.SET_ERROR: {
      const { error, errorInfo } = action.payload
      return { ...state, error, errorInfo }
    }

    case ActionTypes.CLEAR_ERROR: {
      return { ...state, error: null, errorInfo: null }
    }

    default:
      return state
  }
}

export function SchedulerProvider({ children }) {
  const [state, dispatch] = useReducer(schedulerReducer, initialState)

  // Persist UI state to localStorage with debounce to avoid excessive writes
  // Batches both drawer and sections writes into a single effect
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      saveToStorage(STORAGE_KEY_DRAWER, state.isDrawerOpen)
      saveToStorage(STORAGE_KEY_SECTIONS, state.expandedSections)
    }, 100) // 100ms debounce

    return () => {
      clearTimeout(timeoutId)
      // Save immediately on unmount to prevent data loss if component
      // unmounts before the debounce timeout completes
      saveToStorage(STORAGE_KEY_DRAWER, state.isDrawerOpen)
      saveToStorage(STORAGE_KEY_SECTIONS, state.expandedSections)
    }
  }, [state.isDrawerOpen, state.expandedSections])

  // Actions
  const setSchedules = useCallback((schedules) => {
    dispatch({
      type: ActionTypes.SET_SCHEDULES,
      payload: { schedules },
    })
  }, [])

  const setActiveSchedule = useCallback((schedule) => {
    dispatch({
      type: ActionTypes.SET_ACTIVE_SCHEDULE,
      payload: { schedule },
    })
  }, [])

  const clearActiveSchedule = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_ACTIVE_SCHEDULE })
  }, [])

  const setEditingSchedule = useCallback((schedule) => {
    dispatch({
      type: ActionTypes.SET_EDITING_SCHEDULE,
      payload: { schedule },
    })
  }, [])

  const clearEditingSchedule = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_EDITING_SCHEDULE })
  }, [])

  const updateEditingSchedule = useCallback((updates) => {
    dispatch({
      type: ActionTypes.UPDATE_EDITING_SCHEDULE,
      payload: { updates },
    })
  }, [])

  const setCreating = useCallback((isCreating) => {
    dispatch({
      type: ActionTypes.SET_CREATING,
      payload: { isCreating },
    })
  }, [])

  const setUnsavedChanges = useCallback((hasChanges) => {
    dispatch({
      type: ActionTypes.SET_UNSAVED_CHANGES,
      payload: { hasChanges },
    })
  }, [])

  const setPreview = useCallback((events) => {
    dispatch({
      type: ActionTypes.SET_PREVIEW,
      payload: { events },
    })
  }, [])

  const setPreviewLoading = useCallback((loading) => {
    dispatch({
      type: ActionTypes.SET_PREVIEW_LOADING,
      payload: { loading },
    })
  }, [])

  const setPreviewError = useCallback((error) => {
    dispatch({
      type: ActionTypes.SET_PREVIEW_ERROR,
      payload: { error },
    })
  }, [])

  const clearPreview = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_PREVIEW })
  }, [])

  const setConflicts = useCallback((conflicts) => {
    dispatch({
      type: ActionTypes.SET_CONFLICTS,
      payload: { conflicts },
    })
  }, [])

  const clearValidation = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_VALIDATION })
  }, [])

  const setMoonPhases = useCallback((phases) => {
    dispatch({
      type: ActionTypes.SET_MOON_PHASES,
      payload: { phases },
    })
  }, [])

  const setViewMode = useCallback((mode) => {
    dispatch({
      type: ActionTypes.SET_VIEW_MODE,
      payload: { mode },
    })
  }, [])

  const setSelectedDate = useCallback((date) => {
    dispatch({
      type: ActionTypes.SET_SELECTED_DATE,
      payload: { date },
    })
  }, [])

  const toggleExpertMode = useCallback(() => {
    dispatch({ type: ActionTypes.TOGGLE_EXPERT_MODE })
  }, [])

  const toggleDrawer = useCallback(() => {
    dispatch({ type: ActionTypes.TOGGLE_DRAWER })
  }, [])

  const toggleSection = useCallback((section) => {
    dispatch({
      type: ActionTypes.TOGGLE_SECTION,
      payload: { section },
    })
  }, [])

  const loadState = useCallback((newState) => {
    dispatch({
      type: ActionTypes.LOAD_STATE,
      payload: { newState },
    })
  }, [])

  const resetState = useCallback(() => {
    dispatch({ type: ActionTypes.RESET_STATE })
  }, [])

  const setError = useCallback((error, errorInfo = null) => {
    dispatch({
      type: ActionTypes.SET_ERROR,
      payload: { error, errorInfo },
    })
  }, [])

  const clearError = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_ERROR })
  }, [])

  // Computed values
  const hasSchedules = useMemo(
    () => state.schedules.length > 0,
    [state.schedules]
  )

  const isEditing = useMemo(
    () => state.editingSchedule !== null,
    [state.editingSchedule]
  )

  const hasConflicts = useMemo(
    () => state.conflicts.length > 0,
    [state.conflicts]
  )

  const hasError = useMemo(
    () => state.error !== null,
    [state.error]
  )

  // Memoize context value to prevent unnecessary re-renders
  // Grouped structure reduces dependency array from 40+ items to 5
  const contextValue = useMemo(
    () => ({
      // ─── STATE ───────────────────────────────────────────────────────────
      // Core state grouped by domain for organized access
      state: {
        schedules: state.schedules,
        activeSchedule: state.activeSchedule,
        editingSchedule: state.editingSchedule,
        isCreating: state.isCreating,
        hasUnsavedChanges: state.hasUnsavedChanges,
        error: state.error,
        errorInfo: state.errorInfo,
      },
      preview: {
        events: state.previewEvents,
        loading: state.previewLoading,
        error: state.previewError,
      },
      validation: {
        conflicts: state.conflicts,
      },
      ui: {
        viewMode: state.viewMode,
        selectedDate: state.selectedDate,
        isExpertMode: state.isExpertMode,
        isDrawerOpen: state.isDrawerOpen,
        expandedSections: state.expandedSections,
        moonPhases: state.moonPhases,
      },

      // ─── COMPUTED ────────────────────────────────────────────────────────
      // Derived boolean values for conditional rendering
      computed: {
        hasSchedules,
        isEditing,
        hasConflicts,
        hasError,
      },

      // ─── ACTIONS ─────────────────────────────────────────────────────────
      // Grouped action dispatchers (all stable via useCallback)
      scheduleActions: {
        setSchedules,
        setActiveSchedule,
        clearActiveSchedule,
      },
      editActions: {
        setEditingSchedule,
        clearEditingSchedule,
        updateEditingSchedule,
        setCreating,
        setUnsavedChanges,
      },
      previewActions: {
        setPreview,
        setPreviewLoading,
        setPreviewError,
        clearPreview,
        setMoonPhases,
      },
      validationActions: {
        setConflicts,
        clearValidation,
      },
      uiActions: {
        setViewMode,
        setSelectedDate,
        toggleExpertMode,
        toggleDrawer,
        toggleSection,
      },
      errorActions: {
        setError,
        clearError,
      },
      stateActions: {
        loadState,
        resetState,
      },
    }),
    // ═══════════════════════════════════════════════════════════════════════════
    // DEPENDENCY ARRAY - STABILITY GUARANTEE
    // ═══════════════════════════════════════════════════════════════════════════
    //
    // INCLUDED (trigger re-renders when changed):
    // - state: Full reducer state object, changes on any dispatch
    // - hasSchedules, isEditing, hasConflicts, hasError: Computed boolean values
    //
    // INTENTIONALLY OMITTED (stable references - never change identity):
    // - All 20+ action functions (setSchedules, setActiveSchedule, toggleDrawer, etc.)
    //   These are created with useCallback([]) making them referentially stable.
    //
    // WHY THIS IS CORRECT:
    // 1. Actions wrapped in useCallback([]) never change identity across renders
    // 2. Adding them would create a 40+ item dependency array with no behavior change
    // 3. Would trigger false positive warnings in React DevTools profiler
    //
    // MAINTAINER NOTE:
    // If you add new actions, ensure they are wrapped in useCallback with an empty
    // dependency array to preserve this optimization. Otherwise, context consumers
    // will re-render unnecessarily on every provider render.
    // ═══════════════════════════════════════════════════════════════════════════
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state, hasSchedules, isEditing, hasConflicts, hasError]
  )

  return (
    <SchedulerContext.Provider value={contextValue}>
      {children}
    </SchedulerContext.Provider>
  )
}

SchedulerProvider.propTypes = {
  children: PropTypes.node.isRequired,
}

export function useSchedulerContext() {
  const context = React.useContext(SchedulerContext)

  if (!context) {
    throw new Error('useSchedulerContext must be used within a SchedulerProvider')
  }

  return context
}

/**
 * Error Boundary for Scheduler - Catches errors in child components
 *
 * IMPORTANT: This boundary is intentionally exported separately from SchedulerProvider
 * to give consumers flexibility in error handling. You MUST wrap your component tree
 * with this boundary to catch React errors.
 *
 * @example Basic usage - wrap the Scheduler page
 * ```jsx
 * <SchedulerErrorBoundary fallback={<ErrorUI />}>
 *   <SchedulerProvider>
 *     <SchedulerPage />
 *   </SchedulerProvider>
 * </SchedulerErrorBoundary>
 * ```
 *
 * @example With context integration for error recovery
 * ```jsx
 * function SchedulerWithErrorHandling() {
 *   const { errorActions, computed } = useSchedulerContext()
 *   return (
 *     <SchedulerErrorBoundary
 *       onError={errorActions.setError}
 *       fallback={
 *         <ErrorRecoveryUI
 *           onRetry={errorActions.clearError}
 *           hasError={computed.hasError}
 *         />
 *       }
 *     >
 *       <SchedulerPage />
 *     </SchedulerErrorBoundary>
 *   )
 * }
 * ```
 *
 * @param {React.ReactNode} children - Child components to wrap
 * @param {React.ReactNode} [fallback] - UI to show when error occurs
 * @param {Function} [onError] - Callback when error caught (error, errorInfo) => void
 */
export class SchedulerErrorBoundary extends React.Component {
  static defaultProps = {
    fallback: null,
    onError: null,
  }

  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    // Context integration happens via onError callback
    this.props.onError?.(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <div>Something went wrong in the Scheduler</div>
    }
    return this.props.children
  }
}

SchedulerErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  fallback: PropTypes.node,
  onError: PropTypes.func,
}

export default SchedulerContext
