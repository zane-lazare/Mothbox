// Setup file for Vitest + React Testing Library
import '@testing-library/jest-dom'
import { afterEach, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Mock scrollIntoView which is not implemented in jsdom
Element.prototype.scrollIntoView = vi.fn()

// Auto cleanup after each test
afterEach(() => {
  cleanup()
})

// Force clear all timers after all tests to prevent hanging
afterAll(() => {
  vi.clearAllTimers()
  vi.useRealTimers()
})
