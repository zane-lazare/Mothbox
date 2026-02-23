/**
 * Type declarations for cameraControlMapping.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with cameraControlMapping.js.
 */

/**
 * Convert a camelCase frontend key to its snake_case backend equivalent.
 * Returns the original key if no mapping exists.
 */
export declare function toBackendKey(camelKey: string): string
