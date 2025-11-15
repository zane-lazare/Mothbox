import { describe, it, expect, beforeEach } from 'vitest';
import { imageCache } from '../imageCache';

describe('imageCache', () => {
  beforeEach(() => {
    imageCache.clear();
  });

  describe('Basic Operations', () => {
    it('caches loaded images', () => {
      const mockImage = new Image();
      mockImage.src = 'test.jpg';

      imageCache.set('photo1', mockImage);

      const cached = imageCache.get('photo1');
      expect(cached).toBe(mockImage);
    });

    it('retrieves cached images', () => {
      const mockImage1 = new Image();
      const mockImage2 = new Image();

      imageCache.set('photo1', mockImage1);
      imageCache.set('photo2', mockImage2);

      expect(imageCache.get('photo1')).toBe(mockImage1);
      expect(imageCache.get('photo2')).toBe(mockImage2);
    });

    it('returns null for non-existent keys', () => {
      const result = imageCache.get('non-existent');
      expect(result).toBeNull();
    });

    it('overwrites existing key', () => {
      const mockImage1 = new Image();
      const mockImage2 = new Image();

      imageCache.set('photo1', mockImage1);
      imageCache.set('photo1', mockImage2);

      expect(imageCache.get('photo1')).toBe(mockImage2);
    });

    it('clears cache on demand', () => {
      imageCache.set('photo1', new Image());
      imageCache.set('photo2', new Image());

      imageCache.clear();

      expect(imageCache.get('photo1')).toBeNull();
      expect(imageCache.get('photo2')).toBeNull();
    });
  });

  describe('LRU Eviction', () => {
    it('evicts least recently used when full', () => {
      // Fill cache to max (100 items)
      for (let i = 0; i < 100; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // Add one more - should evict first item
      imageCache.set('photo100', new Image());

      expect(imageCache.get('photo0')).toBeNull(); // First item evicted
      expect(imageCache.get('photo100')).not.toBeNull(); // New item exists
      expect(imageCache.get('photo99')).not.toBeNull(); // Recent items still exist
    });

    it('respects max size limit', () => {
      // Add 101 items
      for (let i = 0; i <= 100; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      const stats = imageCache.getStats();
      expect(stats.size).toBe(100); // Should not exceed max
      expect(stats.maxSize).toBe(100);
    });

    it('updates LRU on access', () => {
      // Fill cache
      for (let i = 0; i < 100; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // Access first item (moves to end of LRU)
      imageCache.get('photo0');

      // Add new item - should evict photo1, not photo0
      imageCache.set('photo100', new Image());

      expect(imageCache.get('photo0')).not.toBeNull(); // Still exists (recently accessed)
      expect(imageCache.get('photo1')).toBeNull(); // Evicted
    });

    it('setting existing key updates LRU position', () => {
      // Fill cache
      for (let i = 0; i < 100; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // Update first item (moves to end)
      imageCache.set('photo0', new Image());

      // Add new item
      imageCache.set('photo100', new Image());

      expect(imageCache.get('photo0')).not.toBeNull(); // Still exists
      expect(imageCache.get('photo1')).toBeNull(); // Evicted instead
    });

    it('evicts in correct order (FIFO when not accessed)', () => {
      // Add items 0-99
      for (let i = 0; i < 100; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // Add items 100-109 (should evict 0-9)
      for (let i = 100; i < 110; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // First 10 should be evicted
      expect(imageCache.get('photo0')).toBeNull();
      expect(imageCache.get('photo9')).toBeNull();

      // Recent ones should exist
      expect(imageCache.get('photo10')).not.toBeNull();
      expect(imageCache.get('photo109')).not.toBeNull();
    });
  });

  describe('Statistics', () => {
    it('tracks cache hits', () => {
      imageCache.set('photo1', new Image());

      imageCache.get('photo1'); // Hit
      imageCache.get('photo1'); // Hit

      const stats = imageCache.getStats();
      expect(stats.hits).toBe(2);
    });

    it('tracks cache misses', () => {
      imageCache.get('non-existent1'); // Miss
      imageCache.get('non-existent2'); // Miss

      const stats = imageCache.getStats();
      expect(stats.misses).toBe(2);
    });

    it('calculates hit ratio correctly', () => {
      imageCache.set('photo1', new Image());

      imageCache.get('photo1'); // Hit
      imageCache.get('photo1'); // Hit
      imageCache.get('missing'); // Miss

      const stats = imageCache.getStats();
      expect(stats.hits).toBe(2);
      expect(stats.misses).toBe(1);
      expect(stats.hitRatio).toBeCloseTo(2 / 3, 2);
    });

    it('provides cache size', () => {
      imageCache.set('photo1', new Image());
      imageCache.set('photo2', new Image());
      imageCache.set('photo3', new Image());

      const stats = imageCache.getStats();
      expect(stats.size).toBe(3);
    });

    it('provides max size', () => {
      const stats = imageCache.getStats();
      expect(stats.maxSize).toBe(100);
    });

    it('handles zero hits/misses (no division by zero)', () => {
      const stats = imageCache.getStats();
      expect(stats.hitRatio).toBe(0);
      expect(stats.hits).toBe(0);
      expect(stats.misses).toBe(0);
    });

    it('resets statistics on clear', () => {
      imageCache.set('photo1', new Image());
      imageCache.get('photo1');
      imageCache.get('missing');

      imageCache.clear();

      const stats = imageCache.getStats();
      expect(stats.size).toBe(0);
      expect(stats.hits).toBe(0);
      expect(stats.misses).toBe(0);
      expect(stats.hitRatio).toBe(0);
    });
  });

  describe('Edge Cases', () => {
    it('handles null values', () => {
      imageCache.set('null-key', null);

      expect(imageCache.get('null-key')).toBeNull();
    });

    it('handles undefined values', () => {
      imageCache.set('undefined-key', undefined);

      expect(imageCache.get('undefined-key')).toBeUndefined();
    });

    it('handles empty string key', () => {
      const mockImage = new Image();
      imageCache.set('', mockImage);

      expect(imageCache.get('')).toBe(mockImage);
    });

    it('handles numeric keys', () => {
      const mockImage = new Image();
      imageCache.set(123, mockImage);

      expect(imageCache.get(123)).toBe(mockImage);
    });

    it('handles object keys', () => {
      const keyObj = { id: 1 };
      const mockImage = new Image();

      imageCache.set(keyObj, mockImage);

      expect(imageCache.get(keyObj)).toBe(mockImage);
    });

    it('handles rapid successive operations', () => {
      for (let i = 0; i < 1000; i++) {
        imageCache.set(`photo${i % 50}`, new Image());
      }

      const stats = imageCache.getStats();
      expect(stats.size).toBeLessThanOrEqual(100);
    });

    it('maintains cache integrity after many operations', () => {
      // Mixed operations
      for (let i = 0; i < 200; i++) {
        imageCache.set(`photo${i}`, new Image());

        if (i % 10 === 0) {
          imageCache.get(`photo${i - 5}`);
        }
      }

      const stats = imageCache.getStats();
      expect(stats.size).toBe(100);
      expect(stats.hits + stats.misses).toBeGreaterThan(0);
    });
  });

  describe('Memory Efficiency', () => {
    it('does not grow beyond max size', () => {
      // Add 1000 items
      for (let i = 0; i < 1000; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      const stats = imageCache.getStats();
      expect(stats.size).toBe(100); // Should never exceed 100
    });

    it('properly removes old entries', () => {
      // Add 100 items
      for (let i = 0; i < 100; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // Add 50 more (should evict first 50)
      for (let i = 100; i < 150; i++) {
        imageCache.set(`photo${i}`, new Image());
      }

      // First 50 should be gone
      for (let i = 0; i < 50; i++) {
        expect(imageCache.get(`photo${i}`)).toBeNull();
      }

      // Last 100 should exist
      for (let i = 50; i < 150; i++) {
        expect(imageCache.get(`photo${i}`)).not.toBeNull();
      }
    });
  });

  describe('Concurrent Access Patterns', () => {
    it('handles alternating get/set operations', () => {
      imageCache.set('photo1', new Image());

      expect(imageCache.get('photo1')).not.toBeNull();

      imageCache.set('photo1', new Image());

      expect(imageCache.get('photo1')).not.toBeNull();

      const stats = imageCache.getStats();
      expect(stats.hits).toBe(2);
    });

    it('handles batch operations', () => {
      const batch1 = Array.from({ length: 50 }, (_, i) => [`batch1-${i}`, new Image()]);
      const batch2 = Array.from({ length: 50 }, (_, i) => [`batch2-${i}`, new Image()]);

      batch1.forEach(([key, img]) => imageCache.set(key, img));
      batch2.forEach(([key, img]) => imageCache.set(key, img));

      const stats = imageCache.getStats();
      expect(stats.size).toBe(100);
    });
  });
});
