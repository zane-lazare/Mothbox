import { render, act } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import React from 'react'
import { SelectionProvider, MAX_SELECTION } from '../SelectionContext'
import useSelection from '../../hooks/useSelection'

// Test component to access context
function TestConsumer({ onContextReady }) {
  const ctx = useSelection()
  React.useEffect(() => {
    onContextReady(ctx)
  }, [ctx, onContextReady])
  return null
}

// Helper to render with provider
function renderWithProvider(ui) {
  return render(<SelectionProvider>{ui}</SelectionProvider>)
}

describe('SelectionContext', () => {
  let ctx

  beforeEach(() => {
    ctx = null
  })

  const setupContext = () => {
    return new Promise((resolve) => {
      renderWithProvider(<TestConsumer onContextReady={(c) => { ctx = c; resolve() }} />)
    })
  }

  describe('Initial State', () => {
    it('should have isSelectMode false initially', async () => {
      await setupContext()
      expect(ctx.isSelectMode).toBe(false)
    })

    it('should have empty selectedPhotos Set', async () => {
      await setupContext()
      expect(ctx.selectedPhotos).toBeInstanceOf(Set)
      expect(ctx.selectedPhotos.size).toBe(0)
    })

    it('should have selectedCount of 0', async () => {
      await setupContext()
      expect(ctx.selectedCount).toBe(0)
    })

    it('should have lastClickedIndex of -1', async () => {
      await setupContext()
      expect(ctx.lastClickedIndex).toBe(-1)
    })

    it('should have empty selectedArray', async () => {
      await setupContext()
      expect(ctx.selectedArray).toEqual([])
    })
  })

  describe('toggleSelectMode', () => {
    it('should toggle isSelectMode from false to true', async () => {
      await setupContext()
      expect(ctx.isSelectMode).toBe(false)

      act(() => {
        ctx.toggleSelectMode()
      })

      expect(ctx.isSelectMode).toBe(true)
    })

    it('should toggle isSelectMode from true to false', async () => {
      await setupContext()

      act(() => {
        ctx.toggleSelectMode()
      })
      expect(ctx.isSelectMode).toBe(true)

      act(() => {
        ctx.toggleSelectMode()
      })
      expect(ctx.isSelectMode).toBe(false)
    })

    it('should clear selection when exiting select mode', async () => {
      await setupContext()

      // Enter select mode and select some photos
      act(() => {
        ctx.toggleSelectMode()
        ctx.selectPhoto('photo1.jpg')
        ctx.selectPhoto('photo2.jpg')
      })
      expect(ctx.selectedCount).toBe(2)

      // Exit select mode
      act(() => {
        ctx.toggleSelectMode()
      })

      expect(ctx.selectedCount).toBe(0)
      expect(ctx.lastClickedIndex).toBe(-1)
    })
  })

  describe('selectPhoto', () => {
    it('should add photo to selection', async () => {
      await setupContext()

      act(() => {
        ctx.selectPhoto('photo1.jpg')
      })

      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(true)
      expect(ctx.selectedCount).toBe(1)
    })

    it('should not add duplicate photos', async () => {
      await setupContext()

      act(() => {
        ctx.selectPhoto('photo1.jpg')
        ctx.selectPhoto('photo1.jpg')
      })

      expect(ctx.selectedCount).toBe(1)
    })

    it('should respect MAX_SELECTION limit (500)', async () => {
      await setupContext()

      act(() => {
        // Try to add 501 photos
        for (let i = 0; i < MAX_SELECTION + 1; i++) {
          ctx.selectPhoto(`photo${i}.jpg`)
        }
      })

      expect(ctx.selectedCount).toBe(MAX_SELECTION)
    })

    it('should not add photo if at MAX_SELECTION limit', async () => {
      await setupContext()

      act(() => {
        // Add MAX_SELECTION photos
        for (let i = 0; i < MAX_SELECTION; i++) {
          ctx.selectPhoto(`photo${i}.jpg`)
        }
      })

      const beforeCount = ctx.selectedCount

      act(() => {
        ctx.selectPhoto('newphoto.jpg')
      })

      expect(ctx.selectedCount).toBe(beforeCount)
      expect(ctx.selectedPhotos.has('newphoto.jpg')).toBe(false)
    })
  })

  describe('deselectPhoto', () => {
    it('should remove photo from selection', async () => {
      await setupContext()

      act(() => {
        ctx.selectPhoto('photo1.jpg')
      })
      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(true)

      act(() => {
        ctx.deselectPhoto('photo1.jpg')
      })

      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(false)
      expect(ctx.selectedCount).toBe(0)
    })

    it('should handle deselecting non-selected photo gracefully', async () => {
      await setupContext()

      act(() => {
        ctx.deselectPhoto('nonexistent.jpg')
      })

      expect(ctx.selectedCount).toBe(0)
    })
  })

  describe('togglePhoto', () => {
    it('should add photo if not selected', async () => {
      await setupContext()

      act(() => {
        ctx.togglePhoto('photo1.jpg', 5)
      })

      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(true)
      expect(ctx.lastClickedIndex).toBe(5)
    })

    it('should remove photo if already selected', async () => {
      await setupContext()

      act(() => {
        ctx.selectPhoto('photo1.jpg')
      })
      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(true)

      act(() => {
        ctx.togglePhoto('photo1.jpg', 5)
      })

      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(false)
      expect(ctx.lastClickedIndex).toBe(5)
    })

    it('should update lastClickedIndex', async () => {
      await setupContext()

      act(() => {
        ctx.togglePhoto('photo1.jpg', 10)
      })
      expect(ctx.lastClickedIndex).toBe(10)

      act(() => {
        ctx.togglePhoto('photo2.jpg', 20)
      })
      expect(ctx.lastClickedIndex).toBe(20)
    })
  })

  describe('selectRange', () => {
    const photos = ['photo0.jpg', 'photo1.jpg', 'photo2.jpg', 'photo3.jpg', 'photo4.jpg']

    it('should select all photos between lastClickedIndex and new index', async () => {
      await setupContext()

      act(() => {
        ctx.togglePhoto('photo1.jpg', 1) // Set lastClickedIndex to 1
        ctx.selectRange(3, photos)
      })

      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(true)
      expect(ctx.selectedPhotos.has('photo2.jpg')).toBe(true)
      expect(ctx.selectedPhotos.has('photo3.jpg')).toBe(true)
      expect(ctx.selectedCount).toBe(3)
    })

    it('should handle reverse selection (clicking earlier photo)', async () => {
      await setupContext()

      act(() => {
        ctx.togglePhoto('photo3.jpg', 3) // Set lastClickedIndex to 3
        ctx.selectRange(1, photos)
      })

      expect(ctx.selectedPhotos.has('photo1.jpg')).toBe(true)
      expect(ctx.selectedPhotos.has('photo2.jpg')).toBe(true)
      expect(ctx.selectedPhotos.has('photo3.jpg')).toBe(true)
      expect(ctx.selectedCount).toBe(3)
    })

    it('should respect MAX_SELECTION limit', async () => {
      await setupContext()

      // Create a large photos array
      const largePhotos = []
      for (let i = 0; i < MAX_SELECTION + 100; i++) {
        largePhotos.push(`photo${i}.jpg`)
      }

      act(() => {
        ctx.togglePhoto('photo0.jpg', 0)
        ctx.selectRange(MAX_SELECTION + 50, largePhotos)
      })

      expect(ctx.selectedCount).toBe(MAX_SELECTION)
    })

    it('should require photos array parameter', async () => {
      await setupContext()

      act(() => {
        ctx.togglePhoto('photo1.jpg', 1)
        ctx.selectRange(3) // No photos array
      })

      // Should not crash, just not select anything beyond what's already selected
      expect(ctx.selectedCount).toBe(1)
    })

    it('should handle when lastClickedIndex is -1', async () => {
      await setupContext()

      act(() => {
        ctx.selectRange(2, photos)
      })

      // Should only select the target photo
      expect(ctx.selectedPhotos.has('photo2.jpg')).toBe(true)
      expect(ctx.selectedCount).toBe(1)
    })
  })

  describe('selectAll', () => {
    it('should select all provided photos', async () => {
      await setupContext()

      const photos = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']

      act(() => {
        ctx.selectAll(photos)
      })

      expect(ctx.selectedCount).toBe(3)
      photos.forEach(photo => {
        expect(ctx.selectedPhotos.has(photo)).toBe(true)
      })
    })

    it('should cap at MAX_SELECTION (500)', async () => {
      await setupContext()

      // Create array with more than MAX_SELECTION photos
      const photos = []
      for (let i = 0; i < MAX_SELECTION + 100; i++) {
        photos.push(`photo${i}.jpg`)
      }

      act(() => {
        ctx.selectAll(photos)
      })

      expect(ctx.selectedCount).toBe(MAX_SELECTION)
    })

    it('should handle empty array', async () => {
      await setupContext()

      act(() => {
        ctx.selectAll([])
      })

      expect(ctx.selectedCount).toBe(0)
    })
  })

  describe('deselectAll', () => {
    it('should clear all selected photos', async () => {
      await setupContext()

      act(() => {
        ctx.selectPhoto('photo1.jpg')
        ctx.selectPhoto('photo2.jpg')
        ctx.selectPhoto('photo3.jpg')
      })
      expect(ctx.selectedCount).toBe(3)

      act(() => {
        ctx.deselectAll()
      })

      expect(ctx.selectedCount).toBe(0)
      expect(ctx.selectedPhotos.size).toBe(0)
    })

    it('should reset lastClickedIndex to -1', async () => {
      await setupContext()

      act(() => {
        ctx.togglePhoto('photo1.jpg', 5)
      })
      expect(ctx.lastClickedIndex).toBe(5)

      act(() => {
        ctx.deselectAll()
      })

      expect(ctx.lastClickedIndex).toBe(-1)
    })
  })

  describe('isSelected', () => {
    it('should return true for selected photos', async () => {
      await setupContext()

      act(() => {
        ctx.selectPhoto('photo1.jpg')
      })

      expect(ctx.isSelected('photo1.jpg')).toBe(true)
    })

    it('should return false for non-selected photos', async () => {
      await setupContext()

      expect(ctx.isSelected('nonexistent.jpg')).toBe(false)
    })
  })

  describe('selectedArray', () => {
    it('should return array of selected photo paths', async () => {
      await setupContext()

      const photos = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']

      act(() => {
        photos.forEach(photo => ctx.selectPhoto(photo))
      })

      const selectedArray = ctx.selectedArray
      expect(Array.isArray(selectedArray)).toBe(true)
      expect(selectedArray.length).toBe(3)
      photos.forEach(photo => {
        expect(selectedArray).toContain(photo)
      })
    })
  })

  describe('useSelection hook error handling', () => {
    it('should throw error when used outside SelectionProvider', () => {
      // Suppress console.error for this test
      const consoleError = console.error
      console.error = () => {}

      expect(() => {
        render(<TestConsumer onContextReady={() => {}} />)
      }).toThrow('useSelection must be used within SelectionProvider')

      console.error = consoleError
    })
  })

  describe('MAX_SELECTION constant', () => {
    it('should export MAX_SELECTION constant', () => {
      expect(MAX_SELECTION).toBe(500)
    })
  })
})
