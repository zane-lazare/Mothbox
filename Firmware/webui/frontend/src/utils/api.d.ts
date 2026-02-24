/**
 * Type declarations for api.js
 *
 * Provides TypeScript types during the gradual migration.
 * Uses permissive types to support both production usage and vi.mock() in tests.
 */
import type { AxiosInstance } from 'axios'

export declare const api: AxiosInstance

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export declare function getPhotoSidecarMetadata(filename: string): Promise<any>

export declare function updatePhotoSidecarMetadata(
  filename: string,
  updates: Record<string, unknown>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<any>

export declare function getAllTags(params?: Record<string, unknown>): Promise<any>

export declare function getAllSpecies(params?: Record<string, unknown>): Promise<any>

export declare function searchPhotos(
  query: string,
  options?: { limit?: number; offset?: number }
): Promise<{ photos: unknown[]; total: number }>
