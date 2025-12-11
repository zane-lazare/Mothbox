import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useFilterPresets } from '../useFilterPresets'

// Mock localStorage
const localStorageMock = (() => {
  let store = {}

  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString()
    }),
    removeItem: vi.fn((key) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

describe('useFilterPresets', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should return empty presets array on first load', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(result.current.presets).toEqual([])
      expect(result.current.isLoading).toBe(false)
    })

    it('should provide all required functions', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(typeof result.current.savePreset).toBe('function')
      expect(typeof result.current.loadPreset).toBe('function')
      expect(typeof result.current.deletePreset).toBe('function')
      expect(typeof result.current.renamePreset).toBe('function')
    })

    it('should start with isLoading true then set to false', () => {
      const { result } = renderHook(() => useFilterPresets())

      // After initial render, isLoading should be false
      expect(result.current.isLoading).toBe(false)
    })

    it('should load existing presets from localStorage', () => {
      const existingPresets = [
        {
          id: 'preset_1',
          name: 'Test Preset',
          filters: { tags: ['moth'] },
          createdAt: '2024-01-01T00:00:00.000Z',
        },
      ]

      localStorageMock.getItem.mockReturnValueOnce(
        JSON.stringify(existingPresets)
      )

      const { result } = renderHook(() => useFilterPresets())

      expect(result.current.presets).toEqual(existingPresets)
      expect(localStorageMock.getItem).toHaveBeenCalledWith(
        'mothbox-filter-presets'
      )
    })
  })

  describe('Save Preset', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })
    it('should save a new preset', () => {
      const { result } = renderHook(() => useFilterPresets())

      const filterState = {
        tags: { selected: ['moth'], matchMode: 'any' },
        dateRange: { preset: 'today' },
      }

      let saveResult
      act(() => {
        saveResult = result.current.savePreset('My Filter', filterState)
      })

      expect(result.current.presets).toHaveLength(1)
      expect(saveResult.preset).toBeDefined()
      expect(saveResult.preset.name).toBe('My Filter')
      expect(saveResult.preset.filters).toEqual(filterState)
      expect(saveResult.preset.id).toBeDefined()
      expect(saveResult.preset.createdAt).toBeDefined()
    })

    it('should generate unique preset ID', () => {
      const { result } = renderHook(() => useFilterPresets())

      let result1, result2
      act(() => {
        result1 = result.current.savePreset('Preset 1', { tags: ['moth'] })
        result2 = result.current.savePreset('Preset 2', { tags: ['butterfly'] })
      })

      expect(result1.preset.id).not.toBe(result2.preset.id)
    })

    it('should save preset to localStorage', () => {
      const { result } = renderHook(() => useFilterPresets())

      const filterState = { tags: ['moth'] }

      act(() => {
        result.current.savePreset('Test', filterState)
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'mothbox-filter-presets',
        expect.any(String)
      )

      const savedData = JSON.parse(localStorageMock.setItem.mock.calls[0][1])
      expect(savedData).toHaveLength(1)
      expect(savedData[0].name).toBe('Test')
    })

    it('should throw error if name is empty', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.savePreset('', { tags: ['moth'] })
        })
      }).toThrow('Preset name is required')
    })

    it('should throw error if name is not a string', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.savePreset(null, { tags: ['moth'] })
        })
      }).toThrow('Preset name is required')
    })

    it('should throw error if filter state is missing', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.savePreset('Test', null)
        })
      }).toThrow('Filter state is required')
    })

    it('should throw error if filter state is not an object', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.savePreset('Test', 'not an object')
        })
      }).toThrow('Filter state is required')
    })

    it('should sort presets by creation date (newest first)', () => {
      const { result } = renderHook(() => useFilterPresets())

      act(() => {
        result.current.savePreset('First', { tags: ['a'] })
      })

      // Wait a bit to ensure different timestamp
      act(() => {
        vi.advanceTimersByTime(10)
      })

      act(() => {
        result.current.savePreset('Second', { tags: ['b'] })
      })

      expect(result.current.presets[0].name).toBe('Second')
      expect(result.current.presets[1].name).toBe('First')
    })
  })

  describe('Duplicate Name Handling', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('should append number for duplicate names', () => {
      const { result } = renderHook(() => useFilterPresets())

      act(() => {
        result.current.savePreset('My Filter', { tags: ['a'] })
      })

      act(() => {
        vi.advanceTimersByTime(10)
      })

      act(() => {
        result.current.savePreset('My Filter', { tags: ['b'] })
      })

      expect(result.current.presets).toHaveLength(2)
      expect(result.current.presets[0].name).toBe('My Filter (2)')
      expect(result.current.presets[1].name).toBe('My Filter')
    })

    it('should handle multiple duplicates with incrementing numbers', () => {
      const { result } = renderHook(() => useFilterPresets())

      act(() => {
        result.current.savePreset('Test', { tags: ['a'] })
      })
      act(() => {
        vi.advanceTimersByTime(10)
      })
      act(() => {
        result.current.savePreset('Test', { tags: ['b'] })
      })
      act(() => {
        vi.advanceTimersByTime(10)
      })
      act(() => {
        result.current.savePreset('Test', { tags: ['c'] })
      })

      expect(result.current.presets).toHaveLength(3)
      const names = result.current.presets.map((p) => p.name).sort()
      expect(names).toEqual(['Test', 'Test (2)', 'Test (3)'])
    })

    it('should be case-insensitive when checking duplicates', () => {
      const { result } = renderHook(() => useFilterPresets())

      act(() => {
        result.current.savePreset('My Filter', { tags: ['a'] })
      })
      act(() => {
        vi.advanceTimersByTime(10)
      })
      act(() => {
        result.current.savePreset('my filter', { tags: ['b'] })
      })
      act(() => {
        vi.advanceTimersByTime(10)
      })
      act(() => {
        result.current.savePreset('MY FILTER', { tags: ['c'] })
      })

      expect(result.current.presets).toHaveLength(3)
      expect(result.current.presets[0].name).toBe('MY FILTER (3)')
      expect(result.current.presets[1].name).toBe('my filter (2)')
      expect(result.current.presets[2].name).toBe('My Filter')
    })

    it('should trim whitespace when checking duplicates', () => {
      const { result } = renderHook(() => useFilterPresets())

      act(() => {
        result.current.savePreset('Test', { tags: ['a'] })
      })
      act(() => {
        vi.advanceTimersByTime(10)
      })
      act(() => {
        result.current.savePreset('  Test  ', { tags: ['b'] })
      })

      expect(result.current.presets).toHaveLength(2)
      expect(result.current.presets[0].name).toBe('Test (2)')
    })
  })

  describe('Max Presets Limit', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })
    it('should enforce maximum of 20 presets', () => {
      const { result } = renderHook(() => useFilterPresets())

      // Create 25 presets
      for (let i = 1; i <= 25; i++) {
        act(() => {
          result.current.savePreset(`Preset ${i}`, { tags: [`tag${i}`] })
        })
        act(() => {
          vi.advanceTimersByTime(1) // Ensure unique timestamps
        })
      }

      expect(result.current.presets).toHaveLength(20)
    })

    it('should remove oldest presets when limit exceeded', () => {
      const { result } = renderHook(() => useFilterPresets())

      // Create 21 presets
      for (let i = 1; i <= 21; i++) {
        act(() => {
          result.current.savePreset(`Preset ${i}`, { tags: [`tag${i}`] })
        })
        act(() => {
          vi.advanceTimersByTime(1)
        })
      }

      // Should have newest 20 presets
      expect(result.current.presets).toHaveLength(20)
      expect(result.current.presets[0].name).toBe('Preset 21') // Newest
      expect(result.current.presets[19].name).toBe('Preset 2') // Oldest kept
    })
  })

  describe('Load Preset', () => {
    it('should load preset by ID', () => {
      const { result } = renderHook(() => useFilterPresets())

      const filterState = {
        tags: { selected: ['moth'] },
        dateRange: { preset: 'today' },
      }

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', filterState)
        presetId = saved.preset.id
      })

      const loaded = result.current.loadPreset(presetId)

      expect(loaded).toEqual(filterState)
    })

    it('should return null for non-existent preset ID', () => {
      const { result } = renderHook(() => useFilterPresets())

      const loaded = result.current.loadPreset('nonexistent_id')

      expect(loaded).toBeNull()
    })

    it('should throw error if preset ID is not provided', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        result.current.loadPreset(null)
      }).toThrow('Preset ID is required')
    })

    it('should throw error if preset ID is not a string', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        result.current.loadPreset(123)
      }).toThrow('Preset ID is required')
    })
  })

  describe('Delete Preset', () => {
    it('should delete preset by ID', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      expect(result.current.presets).toHaveLength(1)

      act(() => {
        result.current.deletePreset(presetId)
      })

      expect(result.current.presets).toHaveLength(0)
    })

    it('should update localStorage after deletion', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      vi.clearAllMocks()

      act(() => {
        result.current.deletePreset(presetId)
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'mothbox-filter-presets',
        '[]'
      )
    })

    it('should handle deleting non-existent preset gracefully', () => {
      const { result } = renderHook(() => useFilterPresets())

      act(() => {
        result.current.savePreset('Test', { tags: ['moth'] })
      })

      expect(result.current.presets).toHaveLength(1)

      act(() => {
        result.current.deletePreset('nonexistent_id')
      })

      // Should not throw, original preset still exists
      expect(result.current.presets).toHaveLength(1)
    })

    it('should throw error if preset ID is not provided', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.deletePreset(null)
        })
      }).toThrow('Preset ID is required')
    })
  })

  describe('Rename Preset', () => {
    it('should rename preset by ID', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Old Name', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      act(() => {
        result.current.renamePreset(presetId, 'New Name')
      })

      expect(result.current.presets[0].name).toBe('New Name')
    })

    it('should update localStorage after rename', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Old Name', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      vi.clearAllMocks()

      act(() => {
        result.current.renamePreset(presetId, 'New Name')
      })

      expect(localStorageMock.setItem).toHaveBeenCalled()
      const savedData = JSON.parse(localStorageMock.setItem.mock.calls[0][1])
      expect(savedData[0].name).toBe('New Name')
    })

    it('should throw error if preset ID not found', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.renamePreset('nonexistent_id', 'New Name')
        })
      }).toThrow('Preset not found')
    })

    it('should throw error if preset ID is not provided', () => {
      const { result } = renderHook(() => useFilterPresets())

      expect(() => {
        act(() => {
          result.current.renamePreset(null, 'New Name')
        })
      }).toThrow('Preset ID is required')
    })

    it('should throw error if new name is empty', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      expect(() => {
        act(() => {
          result.current.renamePreset(presetId, '')
        })
      }).toThrow('New preset name is required')
    })

    it('should handle renaming to duplicate name by appending number', () => {
      vi.useFakeTimers()

      const { result } = renderHook(() => useFilterPresets())
      let preset2Id

      act(() => {
        result.current.savePreset('Preset 1', { tags: ['a'] })
      })

      act(() => {
        vi.advanceTimersByTime(10)
      })

      act(() => {
        const p2 = result.current.savePreset('Preset 2', { tags: ['b'] })
        preset2Id = p2.preset.id
      })

      act(() => {
        result.current.renamePreset(preset2Id, 'Preset 1')
      })

      expect(result.current.presets[0].name).toBe('Preset 1 (2)')

      vi.useRealTimers()
    })

    it('should allow renaming to same name (no change)', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      vi.clearAllMocks()

      act(() => {
        result.current.renamePreset(presetId, 'Test')
      })

      // Should not update storage since no change
      expect(localStorageMock.setItem).not.toHaveBeenCalled()
    })

    it('should trim whitespace from new name', () => {
      const { result } = renderHook(() => useFilterPresets())

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      act(() => {
        result.current.renamePreset(presetId, '  New Name  ')
      })

      expect(result.current.presets[0].name).toBe('New Name')
    })
  })

  describe('LocalStorage Persistence', () => {
    it('should persist presets across hook instances', () => {
      const { result: result1 } = renderHook(() => useFilterPresets())

      act(() => {
        result1.current.savePreset('Test', { tags: ['moth'] })
      })

      // Create new hook instance
      const { result: result2 } = renderHook(() => useFilterPresets())

      expect(result2.current.presets).toHaveLength(1)
      expect(result2.current.presets[0].name).toBe('Test')
    })

    it('should handle corrupted localStorage data gracefully', () => {
      localStorageMock.getItem.mockReturnValueOnce('invalid json {')

      const { result } = renderHook(() => useFilterPresets())

      // Should fall back to empty array
      expect(result.current.presets).toEqual([])
    })

    it('should filter out invalid preset objects from storage', () => {
      const invalidData = [
        { id: 'valid', name: 'Valid', filters: {}, createdAt: '2024-01-01' },
        { id: 'invalid1' }, // Missing required fields
        { name: 'invalid2', filters: {} }, // Missing id and createdAt
        null, // Null entry
        'string', // Invalid type
      ]

      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(invalidData))

      const { result } = renderHook(() => useFilterPresets())

      expect(result.current.presets).toHaveLength(1)
      expect(result.current.presets[0].id).toBe('valid')
    })

    it('should handle non-array data in localStorage', () => {
      localStorageMock.getItem.mockReturnValueOnce(
        JSON.stringify({ not: 'an array' })
      )

      const { result } = renderHook(() => useFilterPresets())

      expect(result.current.presets).toEqual([])
    })
  })

  describe('Error Handling', () => {
    it('should return error status when localStorage setItem fails', () => {
      const { result } = renderHook(() => useFilterPresets())

      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {})

      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Storage quota exceeded')
      })

      let saveResult
      act(() => {
        saveResult = result.current.savePreset('Test', { tags: ['moth'] })
      })

      expect(saveResult.success).toBe(false)
      expect(saveResult.error).toBe('Failed to save preset')
      expect(saveResult.preset).toBeDefined()
      expect(consoleErrorSpy).toHaveBeenCalled()

      consoleErrorSpy.mockRestore()
    })

    it('should return quota-specific error message for QuotaExceededError', () => {
      const { result } = renderHook(() => useFilterPresets())

      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {})

      const quotaError = new Error('Storage quota exceeded')
      quotaError.name = 'QuotaExceededError'

      localStorageMock.setItem.mockImplementationOnce(() => {
        throw quotaError
      })

      let saveResult
      act(() => {
        saveResult = result.current.savePreset('Test', { tags: ['moth'] })
      })

      expect(saveResult.success).toBe(false)
      expect(saveResult.error).toContain('quota')
      expect(saveResult.preset).toBeDefined()

      consoleErrorSpy.mockRestore()
    })

    it('should return success status on successful save', () => {
      const { result } = renderHook(() => useFilterPresets())

      let saveResult
      act(() => {
        saveResult = result.current.savePreset('Test', { tags: ['moth'] })
      })

      expect(saveResult.success).toBe(true)
      expect(saveResult.error).toBeUndefined()
      expect(saveResult.preset).toBeDefined()
      expect(saveResult.preset.name).toBe('Test')
    })

    it('should return error status from deletePreset on storage failure', () => {
      const { result } = renderHook(() => useFilterPresets())

      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {})

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Storage error')
      })

      let deleteResult
      act(() => {
        deleteResult = result.current.deletePreset(presetId)
      })

      expect(deleteResult.success).toBe(false)
      expect(deleteResult.error).toBe('Failed to save preset')

      consoleErrorSpy.mockRestore()
    })

    it('should return error status from renamePreset on storage failure', () => {
      const { result } = renderHook(() => useFilterPresets())

      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {})

      let presetId
      act(() => {
        const saved = result.current.savePreset('Test', { tags: ['moth'] })
        presetId = saved.preset.id
      })

      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Storage error')
      })

      let renameResult
      act(() => {
        renameResult = result.current.renamePreset(presetId, 'New Name')
      })

      expect(renameResult.success).toBe(false)
      expect(renameResult.error).toBe('Failed to save preset')

      consoleErrorSpy.mockRestore()
    })

    it('should handle localStorage getItem errors gracefully', () => {
      const consoleWarnSpy = vi
        .spyOn(console, 'warn')
        .mockImplementation(() => {})

      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Storage access denied')
      })

      const { result } = renderHook(() => useFilterPresets())

      expect(result.current.presets).toEqual([])
      expect(consoleWarnSpy).toHaveBeenCalled()

      consoleWarnSpy.mockRestore()
    })
  })
})
