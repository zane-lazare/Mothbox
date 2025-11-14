import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import useImagePreload from '../useImagePreload'

describe('useImagePreload', () => {
  let mockPhotos

  beforeEach(() => {
    // Mock photos array
    mockPhotos = [
      { path: 'photo1.jpg', url: '/api/gallery/photo/photo1.jpg' },
      { path: 'photo2.jpg', url: '/api/gallery/photo/photo2.jpg' },
      { path: 'photo3.jpg', url: '/api/gallery/photo/photo3.jpg' },
      { path: 'photo4.jpg', url: '/api/gallery/photo/photo4.jpg' },
      { path: 'photo5.jpg', url: '/api/gallery/photo/photo5.jpg' },
    ]

    // Mock Image constructor
    globalThis.Image = class {
      constructor() {
        this._src = ''
        this._onload = null
        this._onerror = null
      }

      get src() {
        return this._src
      }

      set src(value) {
        this._src = value
        // Simulate immediate load
        setTimeout(() => {
          if (this._onload) {
            this._onload()
          }
        }, 10)
      }

      set onload(value) {
        this._onload = value
      }

      set onerror(value) {
        this._onerror = value
      }
    }
  })

  it('returns loading state initially', () => {
    const { result } = renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[0],
        photos: mockPhotos,
        currentIndex: 0,
      })
    )

    expect(result.current.isLoading).toBe(true)
  })

  it('loads current image first', async () => {
    const { result } = renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[2],
        photos: mockPhotos,
        currentIndex: 2,
      })
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.currentImage).toBe('/api/gallery/photo/photo3.jpg')
  })

  it('preloads next image in background', async () => {
    const imageSources = []

    // Override Image to capture all created images
    globalThis.Image = class {
      constructor() {
        this._src = ''
      }

      get src() {
        return this._src
      }

      set src(value) {
        this._src = value
        imageSources.push(value)
        // Simulate immediate load
        setTimeout(() => {
          if (this._onload) {
            this._onload()
          }
        }, 10)
      }

      set onload(value) {
        this._onload = value
      }

      set onerror(value) {
        this._onerror = value
      }
    }

    renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[2],
        photos: mockPhotos,
        currentIndex: 2,
      })
    )

    await waitFor(() => {
      expect(imageSources.length).toBeGreaterThanOrEqual(2)
    })

    // Should preload current and next
    expect(imageSources).toContain('/api/gallery/photo/photo3.jpg') // current
    expect(imageSources).toContain('/api/gallery/photo/photo4.jpg') // next
  })

  it('preloads previous image in background', async () => {
    const imageSources = []

    // Override Image to capture all created images
    globalThis.Image = class {
      constructor() {
        this._src = ''
      }

      get src() {
        return this._src
      }

      set src(value) {
        this._src = value
        imageSources.push(value)
        setTimeout(() => {
          if (this._onload) {
            this._onload()
          }
        }, 10)
      }

      set onload(value) {
        this._onload = value
      }

      set onerror(value) {
        this._onerror = value
      }
    }

    renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[2],
        photos: mockPhotos,
        currentIndex: 2,
      })
    )

    await waitFor(() => {
      expect(imageSources.length).toBe(3)
    })

    // Should preload previous, current, and next
    expect(imageSources).toContain('/api/gallery/photo/photo2.jpg') // previous
    expect(imageSources).toContain('/api/gallery/photo/photo3.jpg') // current
    expect(imageSources).toContain('/api/gallery/photo/photo4.jpg') // next
  })

  it('updates when currentIndex changes', async () => {
    const { result, rerender } = renderHook(
      ({ currentIndex }) =>
        useImagePreload({
          currentPhoto: mockPhotos[currentIndex],
          photos: mockPhotos,
          currentIndex,
        }),
      { initialProps: { currentIndex: 0 } }
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.currentImage).toBe('/api/gallery/photo/photo1.jpg')

    // Change to next photo
    rerender({ currentIndex: 1 })

    await waitFor(() => {
      expect(result.current.currentImage).toBe('/api/gallery/photo/photo2.jpg')
    })
  })

  it('handles first photo (no previous)', async () => {
    const imageSources = []

    globalThis.Image = class {
      constructor() {
        this._src = ''
      }

      get src() {
        return this._src
      }

      set src(value) {
        this._src = value
        imageSources.push(value)
        setTimeout(() => {
          if (this._onload) {
            this._onload()
          }
        }, 10)
      }

      set onload(value) {
        this._onload = value
      }

      set onerror(value) {
        this._onerror = value
      }
    }

    renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[0],
        photos: mockPhotos,
        currentIndex: 0,
      })
    )

    await waitFor(() => {
      expect(imageSources.length).toBe(2)
    })

    // Should only preload current and next (no previous)
    expect(imageSources).toContain('/api/gallery/photo/photo1.jpg') // current
    expect(imageSources).toContain('/api/gallery/photo/photo2.jpg') // next
    expect(imageSources).not.toContain('/api/gallery/photo/photo0.jpg') // no previous
  })

  it('handles last photo (no next)', async () => {
    const imageSources = []

    globalThis.Image = class {
      constructor() {
        this._src = ''
      }

      get src() {
        return this._src
      }

      set src(value) {
        this._src = value
        imageSources.push(value)
        setTimeout(() => {
          if (this._onload) {
            this._onload()
          }
        }, 10)
      }

      set onload(value) {
        this._onload = value
      }

      set onerror(value) {
        this._onerror = value
      }
    }

    renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[4],
        photos: mockPhotos,
        currentIndex: 4,
      })
    )

    await waitFor(() => {
      expect(imageSources.length).toBe(2)
    })

    // Should only preload previous and current (no next)
    expect(imageSources).toContain('/api/gallery/photo/photo4.jpg') // previous
    expect(imageSources).toContain('/api/gallery/photo/photo5.jpg') // current
    expect(imageSources).not.toContain('/api/gallery/photo/photo6.jpg') // no next
  })

  it('cleans up on unmount', () => {
    const { unmount } = renderHook(() =>
      useImagePreload({
        currentPhoto: mockPhotos[2],
        photos: mockPhotos,
        currentIndex: 2,
      })
    )

    // Should not throw when unmounting
    expect(() => unmount()).not.toThrow()
  })
})
