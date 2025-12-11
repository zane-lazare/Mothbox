import React, { createContext, useReducer, useMemo, useCallback } from 'react'
import PropTypes from 'prop-types'
import { countActiveFilters } from '../utils/filterQueryBuilder'

const FilterContext = createContext(null)

// Action types
const ActionTypes = {
  SET_DATE_RANGE: 'SET_DATE_RANGE',
  SET_TAGS: 'SET_TAGS',
  SET_SPECIES: 'SET_SPECIES',
  SET_FILE_TYPES: 'SET_FILE_TYPES',
  SET_CAMERA_SETTINGS: 'SET_CAMERA_SETTINGS',
  SET_NOTES: 'SET_NOTES',
  SET_CUSTOM_FIELD: 'SET_CUSTOM_FIELD',
  CLEAR_FILTER: 'CLEAR_FILTER',
  CLEAR_ALL_FILTERS: 'CLEAR_ALL_FILTERS',
  TOGGLE_DRAWER: 'TOGGLE_DRAWER',
  TOGGLE_SECTION: 'TOGGLE_SECTION',
  LOAD_STATE: 'LOAD_STATE',
}

// Initial state
const initialState = {
  // Date Range Filter
  dateRange: {
    preset: null, // 'today' | '7days' | '30days' | '90days' | 'thisMonth' | 'lastMonth' | 'thisYear' | 'custom' | null
    startDate: null, // ISO date string (YYYY-MM-DD)
    endDate: null,   // ISO date string (YYYY-MM-DD)
  },

  // Tag Filter
  tags: {
    selected: [],     // Array of tag strings
    matchMode: 'any', // 'any' | 'all'
  },

  // Species Filter
  species: {
    selected: [],           // Array of species strings
    includeUnidentified: false,
  },

  // File Type Filter
  fileTypes: {
    selected: [], // ['jpg', 'png', 'raw', 'video']
  },

  // Camera Settings Filter (EXIF)
  cameraSettings: {
    iso: { min: null, max: null },
    aperture: { min: null, max: null },
    shutterSpeed: { min: null, max: null },
  },

  // Notes Filter
  notes: {
    hasNotes: null, // true | false | null (any)
    keywords: '',
  },

  // Custom Fields Filter
  customFields: {}, // Dynamic: { fieldName: value }

  // UI State
  isDrawerOpen: true,
  expandedSections: ['dateRange'], // Which accordion sections are open
}

// Helper function to reset a specific filter to initial state
function getInitialFilterState(filterType) {
  switch (filterType) {
    case 'dateRange':
      return initialState.dateRange
    case 'tags':
      return initialState.tags
    case 'species':
      return initialState.species
    case 'fileTypes':
      return initialState.fileTypes
    case 'cameraSettings':
      return initialState.cameraSettings
    case 'notes':
      return initialState.notes
    case 'customFields':
      return initialState.customFields
    default:
      return null
  }
}

// Reducer
function filterReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_DATE_RANGE: {
      const { preset, startDate, endDate } = action.payload
      return {
        ...state,
        dateRange: {
          preset: preset !== undefined ? preset : state.dateRange.preset,
          startDate: startDate !== undefined ? startDate : state.dateRange.startDate,
          endDate: endDate !== undefined ? endDate : state.dateRange.endDate,
        },
      }
    }

    case ActionTypes.SET_TAGS: {
      const { selected, matchMode } = action.payload
      return {
        ...state,
        tags: {
          selected: selected !== undefined ? selected : state.tags.selected,
          matchMode: matchMode !== undefined ? matchMode : state.tags.matchMode,
        },
      }
    }

    case ActionTypes.SET_SPECIES: {
      const { selected, includeUnidentified } = action.payload
      return {
        ...state,
        species: {
          selected: selected !== undefined ? selected : state.species.selected,
          includeUnidentified: includeUnidentified !== undefined ? includeUnidentified : state.species.includeUnidentified,
        },
      }
    }

    case ActionTypes.SET_FILE_TYPES: {
      const { selected } = action.payload
      return {
        ...state,
        fileTypes: {
          selected: selected !== undefined ? selected : state.fileTypes.selected,
        },
      }
    }

    case ActionTypes.SET_CAMERA_SETTINGS: {
      const { settings } = action.payload
      return {
        ...state,
        cameraSettings: {
          ...state.cameraSettings,
          ...settings, // Partial update
        },
      }
    }

    case ActionTypes.SET_NOTES: {
      const { hasNotes, keywords } = action.payload
      return {
        ...state,
        notes: {
          hasNotes: hasNotes !== undefined ? hasNotes : state.notes.hasNotes,
          keywords: keywords !== undefined ? keywords : state.notes.keywords,
        },
      }
    }

    case ActionTypes.SET_CUSTOM_FIELD: {
      const { fieldName, value } = action.payload
      return {
        ...state,
        customFields: {
          ...state.customFields,
          [fieldName]: value,
        },
      }
    }

    case ActionTypes.CLEAR_FILTER: {
      const { filterType } = action.payload
      const resetValue = getInitialFilterState(filterType)

      if (resetValue === null) {
        return state
      }

      return {
        ...state,
        [filterType]: resetValue,
      }
    }

    case ActionTypes.CLEAR_ALL_FILTERS: {
      return {
        ...state,
        dateRange: initialState.dateRange,
        tags: initialState.tags,
        species: initialState.species,
        fileTypes: initialState.fileTypes,
        cameraSettings: initialState.cameraSettings,
        notes: initialState.notes,
        customFields: initialState.customFields,
      }
    }

    case ActionTypes.TOGGLE_DRAWER: {
      return {
        ...state,
        isDrawerOpen: !state.isDrawerOpen,
      }
    }

    case ActionTypes.TOGGLE_SECTION: {
      const { sectionId } = action.payload
      const isExpanded = state.expandedSections.includes(sectionId)

      return {
        ...state,
        expandedSections: isExpanded
          ? state.expandedSections.filter(id => id !== sectionId)
          : [...state.expandedSections, sectionId],
      }
    }

    case ActionTypes.LOAD_STATE: {
      const { newState } = action.payload
      return {
        ...state,
        ...newState,
      }
    }

    default:
      return state
  }
}

export function FilterProvider({ children }) {
  const [state, dispatch] = useReducer(filterReducer, initialState)

  // Actions
  const setDateRange = useCallback((preset, startDate, endDate) => {
    dispatch({
      type: ActionTypes.SET_DATE_RANGE,
      payload: { preset, startDate, endDate },
    })
  }, [])

  const setTags = useCallback((selected, matchMode) => {
    dispatch({
      type: ActionTypes.SET_TAGS,
      payload: { selected, matchMode },
    })
  }, [])

  const setSpecies = useCallback((selected, includeUnidentified) => {
    dispatch({
      type: ActionTypes.SET_SPECIES,
      payload: { selected, includeUnidentified },
    })
  }, [])

  const setFileTypes = useCallback((selected) => {
    dispatch({
      type: ActionTypes.SET_FILE_TYPES,
      payload: { selected },
    })
  }, [])

  const setCameraSettings = useCallback((settings) => {
    dispatch({
      type: ActionTypes.SET_CAMERA_SETTINGS,
      payload: { settings },
    })
  }, [])

  const setNotes = useCallback((hasNotes, keywords) => {
    dispatch({
      type: ActionTypes.SET_NOTES,
      payload: { hasNotes, keywords },
    })
  }, [])

  const setCustomField = useCallback((fieldName, value) => {
    dispatch({
      type: ActionTypes.SET_CUSTOM_FIELD,
      payload: { fieldName, value },
    })
  }, [])

  const clearFilter = useCallback((filterType) => {
    dispatch({
      type: ActionTypes.CLEAR_FILTER,
      payload: { filterType },
    })
  }, [])

  const clearAllFilters = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_ALL_FILTERS })
  }, [])

  const toggleDrawer = useCallback(() => {
    dispatch({ type: ActionTypes.TOGGLE_DRAWER })
  }, [])

  const toggleSection = useCallback((sectionId) => {
    dispatch({
      type: ActionTypes.TOGGLE_SECTION,
      payload: { sectionId },
    })
  }, [])

  const loadState = useCallback((newState) => {
    dispatch({
      type: ActionTypes.LOAD_STATE,
      payload: { newState },
    })
  }, [])

  // Computed values - count active filters (uses shared utility to avoid duplication)
  const activeFilterCount = useMemo(
    () => countActiveFilters(state),
    [state.dateRange, state.tags, state.species, state.fileTypes, state.cameraSettings, state.notes, state.customFields]
  )

  // Helper to check if any filters are active
  const hasActiveFilters = activeFilterCount > 0

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(
    () => ({
      // State
      isDrawerOpen: state.isDrawerOpen,
      expandedSections: state.expandedSections,
      dateRange: state.dateRange,
      tags: state.tags,
      species: state.species,
      fileTypes: state.fileTypes,
      cameraSettings: state.cameraSettings,
      notes: state.notes,
      customFields: state.customFields,
      // Computed
      activeFilterCount,
      hasActiveFilters,
      // Actions
      setDateRange,
      setTags,
      setSpecies,
      setFileTypes,
      setCameraSettings,
      setNotes,
      setCustomField,
      clearFilter,
      clearAllFilters,
      toggleDrawer,
      toggleSection,
      loadState,
    }),
    [
      state.isDrawerOpen,
      state.expandedSections,
      state.dateRange,
      state.tags,
      state.species,
      state.fileTypes,
      state.cameraSettings,
      state.notes,
      state.customFields,
      activeFilterCount,
      hasActiveFilters,
      setDateRange,
      setTags,
      setSpecies,
      setFileTypes,
      setCameraSettings,
      setNotes,
      setCustomField,
      clearFilter,
      clearAllFilters,
      toggleDrawer,
      toggleSection,
      loadState,
    ]
  )

  return (
    <FilterContext.Provider value={contextValue}>
      {children}
    </FilterContext.Provider>
  )
}

FilterProvider.propTypes = {
  children: PropTypes.node.isRequired,
}

export function useFilterContext() {
  const context = React.useContext(FilterContext)

  if (!context) {
    throw new Error('useFilterContext must be used within a FilterProvider')
  }

  return context
}

export default FilterContext
