import React, { createContext, useReducer, useMemo, useCallback, ReactNode } from 'react'

export const MAX_SELECTION = 500

// Action types
const ActionTypes = {
  TOGGLE_SELECT_MODE: 'TOGGLE_SELECT_MODE',
  SELECT_PHOTO: 'SELECT_PHOTO',
  DESELECT_PHOTO: 'DESELECT_PHOTO',
  TOGGLE_PHOTO: 'TOGGLE_PHOTO',
  SELECT_RANGE: 'SELECT_RANGE',
  SELECT_ALL: 'SELECT_ALL',
  DESELECT_ALL: 'DESELECT_ALL',
} as const

type SelectionAction =
  | { type: 'TOGGLE_SELECT_MODE' }
  | { type: 'SELECT_PHOTO'; payload: { path: string } }
  | { type: 'DESELECT_PHOTO'; payload: { path: string } }
  | { type: 'TOGGLE_PHOTO'; payload: { path: string; index: number } }
  | { type: 'SELECT_RANGE'; payload: { toIndex: number; photos: string[] } }
  | { type: 'SELECT_ALL'; payload: { photos: string[] } }
  | { type: 'DESELECT_ALL' }

interface State {
  isSelectMode: boolean
  selectedPhotos: Set<string>
  lastClickedIndex: number
}

// Initial state
const initialState: State = {
  isSelectMode: false,
  selectedPhotos: new Set(),
  lastClickedIndex: -1,
}

// Reducer
function selectionReducer(state: State, action: SelectionAction): State {
  switch (action.type) {
    case ActionTypes.TOGGLE_SELECT_MODE: {
      const newSelectMode = !state.isSelectMode
      return {
        ...state,
        isSelectMode: newSelectMode,
        // Clear selection when exiting select mode
        selectedPhotos: newSelectMode ? state.selectedPhotos : new Set(),
        lastClickedIndex: newSelectMode ? state.lastClickedIndex : -1,
      }
    }

    case ActionTypes.SELECT_PHOTO: {
      const { path } = action.payload

      // Don't add if already at max
      if (state.selectedPhotos.size >= MAX_SELECTION && !state.selectedPhotos.has(path)) {
        return state
      }

      const newSet = new Set(state.selectedPhotos)
      newSet.add(path)
      return {
        ...state,
        selectedPhotos: newSet,
      }
    }

    case ActionTypes.DESELECT_PHOTO: {
      const { path } = action.payload
      const newSet = new Set(state.selectedPhotos)
      newSet.delete(path)
      return {
        ...state,
        selectedPhotos: newSet,
      }
    }

    case ActionTypes.TOGGLE_PHOTO: {
      const { path, index } = action.payload
      const newSet = new Set(state.selectedPhotos)

      if (newSet.has(path)) {
        newSet.delete(path)
      } else {
        // Don't add if already at max
        if (newSet.size >= MAX_SELECTION) {
          return {
            ...state,
            lastClickedIndex: index,
          }
        }
        newSet.add(path)
      }

      return {
        ...state,
        selectedPhotos: newSet,
        lastClickedIndex: index,
      }
    }

    case ActionTypes.SELECT_RANGE: {
      const { toIndex, photos } = action.payload

      if (!photos || !Array.isArray(photos)) {
        return state
      }

      const { lastClickedIndex } = state
      const newSet = new Set(state.selectedPhotos)

      // If no previous click, just select the target photo
      if (lastClickedIndex === -1) {
        if (newSet.size < MAX_SELECTION && photos[toIndex]) {
          newSet.add(photos[toIndex])
        }
        return {
          ...state,
          selectedPhotos: newSet,
        }
      }

      // Select range between lastClickedIndex and toIndex
      const startIndex = Math.min(lastClickedIndex, toIndex)
      const endIndex = Math.max(lastClickedIndex, toIndex)

      for (let i = startIndex; i <= endIndex; i++) {
        if (newSet.size >= MAX_SELECTION) {
          break
        }
        if (photos[i]) {
          newSet.add(photos[i])
        }
      }

      return {
        ...state,
        selectedPhotos: newSet,
        lastClickedIndex: toIndex,
      }
    }

    case ActionTypes.SELECT_ALL: {
      const { photos } = action.payload

      if (!photos || !Array.isArray(photos)) {
        return state
      }

      const newSet = new Set<string>()
      for (let i = 0; i < photos.length && newSet.size < MAX_SELECTION; i++) {
        newSet.add(photos[i])
      }

      return {
        ...state,
        selectedPhotos: newSet,
      }
    }

    case ActionTypes.DESELECT_ALL: {
      return {
        ...state,
        selectedPhotos: new Set(),
        lastClickedIndex: -1,
      }
    }

    default:
      return state
  }
}

interface SelectionContextValue {
  isSelectMode: boolean
  selectedPhotos: Set<string>
  lastClickedIndex: number
  selectedCount: number
  selectedArray: string[]
  toggleSelectMode: () => void
  selectPhoto: (path: string) => void
  deselectPhoto: (path: string) => void
  togglePhoto: (path: string, index: number) => void
  selectRange: (toIndex: number, photos: string[]) => void
  selectAll: (photos: string[]) => void
  deselectAll: () => void
  isSelected: (path: string) => boolean
}

interface SelectionProviderProps {
  children: ReactNode
}

const SelectionContext = createContext<SelectionContextValue | undefined>(undefined)

export function SelectionProvider({ children }: SelectionProviderProps) {
  const [state, dispatch] = useReducer(selectionReducer, initialState)

  // Actions
  const toggleSelectMode = useCallback(() => {
    dispatch({ type: ActionTypes.TOGGLE_SELECT_MODE })
  }, [])

  const selectPhoto = useCallback((path: string) => {
    dispatch({ type: ActionTypes.SELECT_PHOTO, payload: { path } })
  }, [])

  const deselectPhoto = useCallback((path: string) => {
    dispatch({ type: ActionTypes.DESELECT_PHOTO, payload: { path } })
  }, [])

  const togglePhoto = useCallback((path: string, index: number) => {
    dispatch({ type: ActionTypes.TOGGLE_PHOTO, payload: { path, index } })
  }, [])

  const selectRange = useCallback((toIndex: number, photos: string[]) => {
    dispatch({ type: ActionTypes.SELECT_RANGE, payload: { toIndex, photos } })
  }, [])

  const selectAll = useCallback((photos: string[]) => {
    dispatch({ type: ActionTypes.SELECT_ALL, payload: { photos } })
  }, [])

  const deselectAll = useCallback(() => {
    dispatch({ type: ActionTypes.DESELECT_ALL })
  }, [])

  const isSelected = useCallback((path: string): boolean => {
    return state.selectedPhotos.has(path)
  }, [state.selectedPhotos])

  // Computed values
  const selectedCount = state.selectedPhotos.size
  const selectedArray = useMemo(() => Array.from(state.selectedPhotos), [state.selectedPhotos])

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo<SelectionContextValue>(
    () => ({
      isSelectMode: state.isSelectMode,
      selectedPhotos: state.selectedPhotos,
      lastClickedIndex: state.lastClickedIndex,
      selectedCount,
      selectedArray,
      toggleSelectMode,
      selectPhoto,
      deselectPhoto,
      togglePhoto,
      selectRange,
      selectAll,
      deselectAll,
      isSelected,
    }),
    [
      state.isSelectMode,
      state.selectedPhotos,
      state.lastClickedIndex,
      selectedCount,
      selectedArray,
      toggleSelectMode,
      selectPhoto,
      deselectPhoto,
      togglePhoto,
      selectRange,
      selectAll,
      deselectAll,
      isSelected,
    ]
  )

  return (
    <SelectionContext.Provider value={contextValue}>
      {children}
    </SelectionContext.Provider>
  )
}

export function useSelectionContext(): SelectionContextValue {
  const context = React.useContext(SelectionContext)

  if (!context) {
    throw new Error('useSelectionContext must be used within SelectionProvider')
  }

  return context
}

export default SelectionContext
