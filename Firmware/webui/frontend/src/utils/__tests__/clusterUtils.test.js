import { describe, it, expect, beforeEach } from 'vitest'
import {
  extractPhotosFromCluster,
  findPhotoIndexInCluster,
  sortPhotosByTimestamp,
} from '../clusterUtils'

/**
 * Unit Tests for Cluster Utilities
 *
 * These tests verify the utility functions used for extracting photo lists
 * from cluster markers for lightbox navigation in the Map-Lightbox Integration.
 *
 * Test Coverage Requirements:
 * - extractPhotosFromCluster: Extract all photos from cluster marker
 * - findPhotoIndexInCluster: Find index of specific photo in cluster
 * - sortPhotosByTimestamp: Sort photos by timestamp ascending
 * - Edge cases: Empty clusters, missing data, invalid inputs
 *
 * Coverage Target: 85%+
 */

describe('clusterUtils', () => {
  // Mock cluster marker data structure (based on react-leaflet-cluster)
  let mockClusterMarker
  let mockNonClusterMarker
  let mockPhotos

  beforeEach(() => {
    // Mock photo data structure (from usePhotoLocations)
    mockPhotos = [
      {
        filename: 'photo_001.jpg',
        path: '2024-11-10/photo_001.jpg',
        latitude: 37.7749,
        longitude: -122.4194,
        timestamp: 1699639800, // Earlier timestamp
      },
      {
        filename: 'photo_002.jpg',
        path: '2024-11-10/photo_002.jpg',
        latitude: 37.7750,
        longitude: -122.4195,
        timestamp: 1699639860, // Middle timestamp
      },
      {
        filename: 'photo_003.jpg',
        path: '2024-11-10/photo_003.jpg',
        latitude: 37.7751,
        longitude: -122.4196,
        timestamp: 1699639920, // Later timestamp
      },
    ]

    // Mock cluster marker with getAllChildMarkers method
    mockClusterMarker = {
      getAllChildMarkers: () => [
        {
          options: {
            // Photo data is stored in marker options
            ...mockPhotos[0],
          },
        },
        {
          options: {
            ...mockPhotos[1],
          },
        },
        {
          options: {
            ...mockPhotos[2],
          },
        },
      ],
    }

    // Mock non-cluster marker (individual marker without getAllChildMarkers)
    mockNonClusterMarker = {
      options: {
        ...mockPhotos[0],
      },
    }
  })

  describe('extractPhotosFromCluster', () => {
    it('extracts all photos from cluster marker', () => {
      const photos = extractPhotosFromCluster(mockClusterMarker)

      expect(photos).toHaveLength(3)
      expect(photos[0].filename).toBe('photo_001.jpg')
      expect(photos[0].path).toBe('2024-11-10/photo_001.jpg')
      expect(photos[1].filename).toBe('photo_002.jpg')
      expect(photos[2].filename).toBe('photo_003.jpg')
    })

    it('returns empty array for non-cluster marker', () => {
      const photos = extractPhotosFromCluster(mockNonClusterMarker)

      expect(photos).toEqual([])
    })

    it('returns empty array for null/undefined marker', () => {
      expect(extractPhotosFromCluster(null)).toEqual([])
      expect(extractPhotosFromCluster(undefined)).toEqual([])
    })

    it('returns empty array for marker without getAllChildMarkers method', () => {
      const invalidMarker = { options: { some: 'data' } }
      const photos = extractPhotosFromCluster(invalidMarker)

      expect(photos).toEqual([])
    })

    it('handles empty cluster (no child markers)', () => {
      const emptyCluster = {
        getAllChildMarkers: () => [],
      }

      const photos = extractPhotosFromCluster(emptyCluster)

      expect(photos).toEqual([])
    })

    it('handles nested clusters (spiderfied)', () => {
      // When clusters are spiderfied, they may have nested structure
      const nestedCluster = {
        getAllChildMarkers: () => [
          {
            options: {
              ...mockPhotos[0],
            },
          },
          {
            // Nested cluster marker
            getAllChildMarkers: () => [
              {
                options: {
                  ...mockPhotos[1],
                },
              },
              {
                options: {
                  ...mockPhotos[2],
                },
              },
            ],
          },
        ],
      }

      const photos = extractPhotosFromCluster(nestedCluster)

      // Should flatten nested clusters
      expect(photos).toHaveLength(3)
      expect(photos[0].filename).toBe('photo_001.jpg')
      expect(photos[1].filename).toBe('photo_002.jpg')
      expect(photos[2].filename).toBe('photo_003.jpg')
    })

    it('preserves photo order by timestamp (ascending)', () => {
      // Create cluster with unsorted photos
      const unsortedCluster = {
        getAllChildMarkers: () => [
          {
            options: {
              ...mockPhotos[2], // Latest
            },
          },
          {
            options: {
              ...mockPhotos[0], // Earliest
            },
          },
          {
            options: {
              ...mockPhotos[1], // Middle
            },
          },
        ],
      }

      const photos = extractPhotosFromCluster(unsortedCluster)

      // Should be sorted by timestamp ascending
      expect(photos[0].timestamp).toBe(1699639800) // Earliest
      expect(photos[1].timestamp).toBe(1699639860) // Middle
      expect(photos[2].timestamp).toBe(1699639920) // Latest
    })

    it('handles missing options in child markers', () => {
      const clusterWithMissingOptions = {
        getAllChildMarkers: () => [
          {
            options: {
              ...mockPhotos[0],
            },
          },
          {
            // Missing options
          },
          {
            options: null,
          },
        ],
      }

      const photos = extractPhotosFromCluster(clusterWithMissingOptions)

      // Should only extract valid photo data
      expect(photos).toHaveLength(1)
      expect(photos[0].filename).toBe('photo_001.jpg')
    })

    it('handles markers with partial photo data', () => {
      const clusterWithPartialData = {
        getAllChildMarkers: () => [
          {
            options: {
              filename: 'photo_001.jpg',
              // Missing path, lat, lon, timestamp
            },
          },
          {
            options: {
              ...mockPhotos[1], // Complete data with timestamp
            },
          },
        ],
      }

      const photos = extractPhotosFromCluster(clusterWithPartialData)

      // Should include both, even with partial data
      expect(photos).toHaveLength(2)
      // Photo with timestamp comes first (sorted)
      expect(photos[0].filename).toBe('photo_002.jpg')
      expect(photos[1].filename).toBe('photo_001.jpg')
    })
  })

  describe('findPhotoIndexInCluster', () => {
    it('finds index of specific photo in cluster by path', () => {
      const index = findPhotoIndexInCluster(mockPhotos, '2024-11-10/photo_002.jpg')

      expect(index).toBe(1)
    })

    it('returns -1 for photo not in cluster', () => {
      const index = findPhotoIndexInCluster(mockPhotos, '2024-11-10/nonexistent.jpg')

      expect(index).toBe(-1)
    })

    it('returns -1 for null/undefined photo path', () => {
      expect(findPhotoIndexInCluster(mockPhotos, null)).toBe(-1)
      expect(findPhotoIndexInCluster(mockPhotos, undefined)).toBe(-1)
    })

    it('returns -1 for empty photos array', () => {
      const index = findPhotoIndexInCluster([], '2024-11-10/photo_001.jpg')

      expect(index).toBe(-1)
    })

    it('returns -1 for null/undefined photos array', () => {
      expect(findPhotoIndexInCluster(null, '2024-11-10/photo_001.jpg')).toBe(-1)
      expect(findPhotoIndexInCluster(undefined, '2024-11-10/photo_001.jpg')).toBe(-1)
    })

    it('handles photos without path field gracefully', () => {
      const photosWithoutPath = [
        { filename: 'photo_001.jpg' },
        { filename: 'photo_002.jpg' },
      ]

      const index = findPhotoIndexInCluster(photosWithoutPath, '2024-11-10/photo_002.jpg')

      expect(index).toBe(-1)
    })

    it('finds first occurrence when duplicate paths exist', () => {
      const photosWithDuplicates = [
        { path: '2024-11-10/photo_001.jpg', filename: 'photo_001.jpg' },
        { path: '2024-11-10/photo_002.jpg', filename: 'photo_002.jpg' },
        { path: '2024-11-10/photo_001.jpg', filename: 'photo_001_copy.jpg' }, // Duplicate path
      ]

      const index = findPhotoIndexInCluster(photosWithDuplicates, '2024-11-10/photo_001.jpg')

      // Should return first occurrence
      expect(index).toBe(0)
    })

    it('performs exact path matching (case-sensitive)', () => {
      const index1 = findPhotoIndexInCluster(mockPhotos, '2024-11-10/photo_001.jpg')
      const index2 = findPhotoIndexInCluster(mockPhotos, '2024-11-10/PHOTO_001.JPG')

      expect(index1).toBe(0) // Exact match
      expect(index2).toBe(-1) // Case mismatch
    })
  })

  describe('sortPhotosByTimestamp', () => {
    it('sorts photos by timestamp ascending (earliest first)', () => {
      const unsortedPhotos = [
        { ...mockPhotos[2] }, // Latest
        { ...mockPhotos[0] }, // Earliest
        { ...mockPhotos[1] }, // Middle
      ]

      const sorted = sortPhotosByTimestamp(unsortedPhotos)

      expect(sorted[0].timestamp).toBe(1699639800) // Earliest
      expect(sorted[1].timestamp).toBe(1699639860) // Middle
      expect(sorted[2].timestamp).toBe(1699639920) // Latest
    })

    it('returns copy of array (does not mutate original)', () => {
      const unsortedPhotos = [
        { ...mockPhotos[2] },
        { ...mockPhotos[0] },
        { ...mockPhotos[1] },
      ]

      const originalFirstTimestamp = unsortedPhotos[0].timestamp

      const sorted = sortPhotosByTimestamp(unsortedPhotos)

      // Original array should not be mutated
      expect(unsortedPhotos[0].timestamp).toBe(originalFirstTimestamp)
      expect(sorted).not.toBe(unsortedPhotos) // Different array reference
    })

    it('handles missing timestamps (places at end)', () => {
      const photosWithMissingTimestamp = [
        { filename: 'photo_001.jpg', timestamp: 1699639800 },
        { filename: 'photo_002.jpg' }, // Missing timestamp
        { filename: 'photo_003.jpg', timestamp: 1699639920 },
        { filename: 'photo_004.jpg' }, // Missing timestamp
      ]

      const sorted = sortPhotosByTimestamp(photosWithMissingTimestamp)

      // Photos with timestamps should come first, sorted
      expect(sorted[0].timestamp).toBe(1699639800)
      expect(sorted[1].timestamp).toBe(1699639920)

      // Photos without timestamps should come last
      expect(sorted[2].timestamp).toBeUndefined()
      expect(sorted[2].filename).toBe('photo_002.jpg')
      expect(sorted[3].timestamp).toBeUndefined()
      expect(sorted[3].filename).toBe('photo_004.jpg')
    })

    it('handles null/undefined timestamps', () => {
      const photosWithNullTimestamp = [
        { filename: 'photo_001.jpg', timestamp: 1699639800 },
        { filename: 'photo_002.jpg', timestamp: null },
        { filename: 'photo_003.jpg', timestamp: undefined },
      ]

      const sorted = sortPhotosByTimestamp(photosWithNullTimestamp)

      expect(sorted[0].timestamp).toBe(1699639800)
      expect(sorted[1].timestamp).toBeNull()
      expect(sorted[2].timestamp).toBeUndefined()
    })

    it('returns empty array for empty input', () => {
      const sorted = sortPhotosByTimestamp([])

      expect(sorted).toEqual([])
    })

    it('returns empty array for null/undefined input', () => {
      expect(sortPhotosByTimestamp(null)).toEqual([])
      expect(sortPhotosByTimestamp(undefined)).toEqual([])
    })

    it('handles single photo', () => {
      const sorted = sortPhotosByTimestamp([mockPhotos[0]])

      expect(sorted).toHaveLength(1)
      expect(sorted[0].filename).toBe('photo_001.jpg')
    })

    it('handles duplicate timestamps (maintains relative order)', () => {
      const photosWithDuplicateTimestamps = [
        { filename: 'photo_003.jpg', timestamp: 1699639920 },
        { filename: 'photo_001.jpg', timestamp: 1699639800 },
        { filename: 'photo_002.jpg', timestamp: 1699639800 }, // Same timestamp as photo_001
      ]

      const sorted = sortPhotosByTimestamp(photosWithDuplicateTimestamps)

      expect(sorted[0].timestamp).toBe(1699639800)
      expect(sorted[1].timestamp).toBe(1699639800)
      expect(sorted[2].timestamp).toBe(1699639920)

      // First two should be photo_001 and photo_002 (stable sort maintains order)
      expect(sorted[0].filename).toBe('photo_001.jpg')
      expect(sorted[1].filename).toBe('photo_002.jpg')
    })

    it('handles string timestamps (parses to number)', () => {
      const photosWithStringTimestamps = [
        { filename: 'photo_002.jpg', timestamp: '1699639860' },
        { filename: 'photo_001.jpg', timestamp: '1699639800' },
        { filename: 'photo_003.jpg', timestamp: '1699639920' },
      ]

      const sorted = sortPhotosByTimestamp(photosWithStringTimestamps)

      // Should sort correctly even with string timestamps
      expect(sorted[0].filename).toBe('photo_001.jpg')
      expect(sorted[1].filename).toBe('photo_002.jpg')
      expect(sorted[2].filename).toBe('photo_003.jpg')
    })

    it('handles invalid timestamp values gracefully', () => {
      const photosWithInvalidTimestamps = [
        { filename: 'photo_001.jpg', timestamp: 1699639800 },
        { filename: 'photo_002.jpg', timestamp: 'invalid' },
        { filename: 'photo_003.jpg', timestamp: NaN },
        { filename: 'photo_004.jpg', timestamp: 1699639920 },
      ]

      const sorted = sortPhotosByTimestamp(photosWithInvalidTimestamps)

      // Valid timestamps should come first
      expect(sorted[0].timestamp).toBe(1699639800)
      expect(sorted[1].timestamp).toBe(1699639920)

      // Invalid timestamps should be at end
      expect(sorted[2].filename).toBe('photo_002.jpg')
      expect(sorted[3].filename).toBe('photo_003.jpg')
    })
  })
})
