import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import useMapLightboxSync from '../useMapLightboxSync'

describe('useMapLightboxSync', () => {
  let mockMapRef
  let mockClusterMarker

  beforeEach(() => {
    // Mock map ref with Leaflet methods
    mockMapRef = {
      current: {
        flyTo: vi.fn(),
        setZoom: vi.fn(),
        getZoom: vi.fn(() => 13),
      },
    }

    // Mock cluster marker with getAllChildMarkers and spiderfy
    mockClusterMarker = {
      getAllChildMarkers: vi.fn(() => [
        {
          options: {
            path: 'cluster1_photo1.jpg',
            filename: 'cluster1_photo1.jpg',
            latitude: 37.7749,
            longitude: -122.4194,
            timestamp: 1234567890,
          },
        },
        {
          options: {
            path: 'cluster1_photo2.jpg',
            filename: 'cluster1_photo2.jpg',
            latitude: 37.7750,
            longitude: -122.4195,
            timestamp: 1234567891,
          },
        },
        {
          options: {
            path: 'cluster1_photo3.jpg',
            filename: 'cluster1_photo3.jpg',
            latitude: 37.7751,
            longitude: -122.4196,
            timestamp: 1234567892,
          },
        },
      ]),
      spiderfy: vi.fn(),
    }
  })

  describe('initialization', () => {
    it('initializes with lightbox closed', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      expect(result.current.isLightboxOpen).toBe(false)
      expect(result.current.currentPhoto).toBeNull()
      expect(result.current.highlightedPhotoPath).toBeNull()
    })

    it('initializes cluster navigation state', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      expect(result.current.clusterPhotos).toEqual([])
      expect(result.current.currentIndex).toBe(-1)
      expect(result.current.hasNext).toBe(false)
      expect(result.current.hasPrevious).toBe(false)
    })
  })

  describe('lightbox to map sync', () => {
    it('pans map when lightbox photo changes', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(mockMapRef.current.flyTo).toHaveBeenCalledWith(
        [37.7749, -122.4194],
        expect.any(Number)
      )
    })

    it('highlights current photo marker (sets highlightedPhotoPath)', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(result.current.highlightedPhotoPath).toBe('photo1.jpg')
    })

    it('auto-expands cluster when photo is clustered (spiderfy)', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'cluster1_photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo, mockClusterMarker)
      })

      expect(mockClusterMarker.spiderfy).toHaveBeenCalled()
    })

    it('handles photos without GPS gracefully', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photoWithoutGPS = {
        path: 'photo_no_gps.jpg',
        latitude: null,
        longitude: null,
      }

      act(() => {
        result.current.openLightbox(photoWithoutGPS)
      })

      // Should not crash, should not call flyTo
      expect(mockMapRef.current.flyTo).not.toHaveBeenCalled()
      expect(result.current.isLightboxOpen).toBe(true)
      expect(result.current.currentPhoto).toEqual(photoWithoutGPS)
      expect(result.current.highlightedPhotoPath).toBe('photo_no_gps.jpg')
    })

    it('handles photos with undefined GPS coordinates', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photoWithoutGPS = {
        path: 'photo_no_gps.jpg',
      }

      act(() => {
        result.current.openLightbox(photoWithoutGPS)
      })

      expect(mockMapRef.current.flyTo).not.toHaveBeenCalled()
      expect(result.current.isLightboxOpen).toBe(true)
    })

    it('updates map when selectPhoto called with new photo', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo1 = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      const photo2 = {
        path: 'photo2.jpg',
        latitude: 38.0,
        longitude: -123.0,
      }

      act(() => {
        result.current.openLightbox(photo1)
      })

      mockMapRef.current.flyTo.mockClear()

      act(() => {
        result.current.selectPhoto(photo2)
      })

      expect(mockMapRef.current.flyTo).toHaveBeenCalledWith([38.0, -123.0], expect.any(Number))
      expect(result.current.highlightedPhotoPath).toBe('photo2.jpg')
    })
  })

  describe('map to lightbox sync', () => {
    it('updates lightbox state when marker clicked', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      const mockMarker = {
        options: photo,
      }

      act(() => {
        result.current.onMarkerClick(mockMarker, photo)
      })

      expect(result.current.isLightboxOpen).toBe(true)
      expect(result.current.currentPhoto).toEqual(photo)
      expect(result.current.highlightedPhotoPath).toBe('photo1.jpg')
    })

    it('sets cluster navigation context on cluster marker click', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'cluster1_photo2.jpg',
        filename: 'cluster1_photo2.jpg',
        latitude: 37.7750,
        longitude: -122.4195,
        timestamp: 1234567891,
      }

      act(() => {
        result.current.onClusterClick(mockClusterMarker, clickedPhoto)
      })

      expect(result.current.isLightboxOpen).toBe(true)
      expect(result.current.clusterPhotos.length).toBe(3)
      expect(result.current.currentPhoto.path).toBe('cluster1_photo2.jpg')
    })

    it('extracts photos from cluster for navigation', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'cluster1_photo1.jpg',
        filename: 'cluster1_photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
        timestamp: 1234567890,
      }

      act(() => {
        result.current.onClusterClick(mockClusterMarker, clickedPhoto)
      })

      expect(mockClusterMarker.getAllChildMarkers).toHaveBeenCalled()
      expect(result.current.clusterPhotos).toEqual([
        {
          path: 'cluster1_photo1.jpg',
          filename: 'cluster1_photo1.jpg',
          latitude: 37.7749,
          longitude: -122.4194,
          timestamp: 1234567890,
        },
        {
          path: 'cluster1_photo2.jpg',
          filename: 'cluster1_photo2.jpg',
          latitude: 37.7750,
          longitude: -122.4195,
          timestamp: 1234567891,
        },
        {
          path: 'cluster1_photo3.jpg',
          filename: 'cluster1_photo3.jpg',
          latitude: 37.7751,
          longitude: -122.4196,
          timestamp: 1234567892,
        },
      ])
    })

    it('sets correct cluster photo index when cluster clicked', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'cluster1_photo2.jpg',
        filename: 'cluster1_photo2.jpg',
        latitude: 37.7750,
        longitude: -122.4195,
        timestamp: 1234567891,
      }

      act(() => {
        result.current.onClusterClick(mockClusterMarker, clickedPhoto)
      })

      expect(result.current.currentIndex).toBe(1) // Index 1 for second photo
    })
  })

  describe('marker highlighting', () => {
    it('applies highlight to current marker via highlightedPhotoPath', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(result.current.highlightedPhotoPath).toBe('photo1.jpg')
    })

    it('removes highlight from previous marker when photo changes', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo1 = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      const photo2 = {
        path: 'photo2.jpg',
        latitude: 38.0,
        longitude: -123.0,
      }

      act(() => {
        result.current.openLightbox(photo1)
      })

      expect(result.current.highlightedPhotoPath).toBe('photo1.jpg')

      act(() => {
        result.current.selectPhoto(photo2)
      })

      expect(result.current.highlightedPhotoPath).toBe('photo2.jpg')
    })

    it('restores original state on lightbox close', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(result.current.highlightedPhotoPath).toBe('photo1.jpg')

      act(() => {
        result.current.closeLightbox()
      })

      expect(result.current.highlightedPhotoPath).toBeNull()
    })
  })

  describe('state management', () => {
    it('tracks current photo', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      expect(result.current.currentPhoto).toBeNull()

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(result.current.currentPhoto).toEqual(photo)
    })

    it('tracks lightbox open/close state', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      expect(result.current.isLightboxOpen).toBe(false)

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(result.current.isLightboxOpen).toBe(true)

      act(() => {
        result.current.closeLightbox()
      })

      expect(result.current.isLightboxOpen).toBe(false)
    })

    it('resets state when lightbox closes', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      expect(result.current.currentPhoto).toEqual(photo)
      expect(result.current.highlightedPhotoPath).toBe('photo1.jpg')

      act(() => {
        result.current.closeLightbox()
      })

      expect(result.current.currentPhoto).toBeNull()
      expect(result.current.highlightedPhotoPath).toBeNull()
      expect(result.current.isLightboxOpen).toBe(false)
    })

    it('clears cluster navigation state when lightbox closes', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'cluster1_photo1.jpg',
        filename: 'cluster1_photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
        timestamp: 1234567890,
      }

      act(() => {
        result.current.onClusterClick(mockClusterMarker, clickedPhoto)
      })

      expect(result.current.clusterPhotos.length).toBe(3)
      expect(result.current.currentIndex).toBe(0)

      act(() => {
        result.current.closeLightbox()
      })

      expect(result.current.clusterPhotos).toEqual([])
      expect(result.current.currentIndex).toBe(-1)
    })
  })

  describe('cluster navigation integration', () => {
    it('provides cluster navigation when cluster opened', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'cluster1_photo2.jpg',
        filename: 'cluster1_photo2.jpg',
        latitude: 37.7750,
        longitude: -122.4195,
        timestamp: 1234567891,
      }

      act(() => {
        result.current.onClusterClick(mockClusterMarker, clickedPhoto)
      })

      expect(result.current.hasNext).toBe(true)
      expect(result.current.hasPrevious).toBe(true)

      act(() => {
        result.current.goNext()
      })

      expect(result.current.currentPhoto.path).toBe('cluster1_photo3.jpg')

      act(() => {
        result.current.goPrevious()
      })

      expect(result.current.currentPhoto.path).toBe('cluster1_photo2.jpg')
    })

    it('syncs map when navigating within cluster', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'cluster1_photo1.jpg',
        filename: 'cluster1_photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
        timestamp: 1234567890,
      }

      act(() => {
        result.current.onClusterClick(mockClusterMarker, clickedPhoto)
      })

      mockMapRef.current.flyTo.mockClear()

      act(() => {
        result.current.goNext()
      })

      expect(mockMapRef.current.flyTo).toHaveBeenCalledWith([37.7750, -122.4195], expect.any(Number))
      expect(result.current.highlightedPhotoPath).toBe('cluster1_photo2.jpg')
    })
  })

  describe('edge cases', () => {
    it('handles null mapRef gracefully', () => {
      const { result } = renderHook(() => useMapLightboxSync({ mapRef: { current: null } }))

      const photo = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.openLightbox(photo)
      })

      // Should not crash
      expect(result.current.isLightboxOpen).toBe(true)
    })

    it('handles cluster marker without spiderfy method', () => {
      const clusterWithoutSpiderfy = {
        getAllChildMarkers: vi.fn(() => [
          {
            options: {
              path: 'photo1.jpg',
              latitude: 37.7749,
              longitude: -122.4194,
              timestamp: 1234567890,
            },
          },
        ]),
      }

      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
        timestamp: 1234567890,
      }

      act(() => {
        result.current.onClusterClick(clusterWithoutSpiderfy, clickedPhoto)
      })

      // Should not crash
      expect(result.current.isLightboxOpen).toBe(true)
    })

    it('handles empty cluster marker', () => {
      const emptyCluster = {
        getAllChildMarkers: vi.fn(() => []),
        spiderfy: vi.fn(),
      }

      const { result } = renderHook(() => useMapLightboxSync({ mapRef: mockMapRef }))

      const clickedPhoto = {
        path: 'photo1.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
      }

      act(() => {
        result.current.onClusterClick(emptyCluster, clickedPhoto)
      })

      // Should open lightbox with single photo, not cluster navigation
      expect(result.current.isLightboxOpen).toBe(true)
      expect(result.current.clusterPhotos).toEqual([])
    })
  })
})
