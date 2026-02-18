import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import React from 'react'
import useSelection from '../useSelection'
import { SelectionProvider } from '../../contexts/SelectionContext'

const wrapper = ({ children }) => (
  <SelectionProvider>{children}</SelectionProvider>
)

describe('useSelection', () => {
  it('throws when used outside SelectionProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useSelection())).toThrow(
      'useSelection must be used within SelectionProvider'
    )
    spy.mockRestore()
  })

  it('returns context value when inside SelectionProvider', () => {
    const { result } = renderHook(() => useSelection(), { wrapper })
    expect(result.current).toBeDefined()
    expect(result.current.isSelectMode).toBe(false)
    expect(result.current.selectedCount).toBe(0)
    expect(typeof result.current.toggleSelectMode).toBe('function')
    expect(typeof result.current.selectPhoto).toBe('function')
    expect(typeof result.current.deselectPhoto).toBe('function')
    expect(typeof result.current.isSelected).toBe('function')
  })

  it('provides all expected context properties', () => {
    const { result } = renderHook(() => useSelection(), { wrapper })
    const expectedKeys = [
      'isSelectMode', 'selectedPhotos', 'lastClickedIndex',
      'selectedCount', 'selectedArray',
      'toggleSelectMode', 'selectPhoto', 'deselectPhoto',
      'togglePhoto', 'selectRange', 'selectAll', 'deselectAll', 'isSelected',
    ]
    expectedKeys.forEach(key => {
      expect(result.current).toHaveProperty(key)
    })
  })
})
