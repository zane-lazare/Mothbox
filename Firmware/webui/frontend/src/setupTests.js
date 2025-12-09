// Setup file for Vitest + React Testing Library
import '@testing-library/jest-dom'
import { afterEach, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Mock scrollIntoView which is not implemented in jsdom
Element.prototype.scrollIntoView = vi.fn()

// ============================================================================
// Global Network Mocks - Prevent real HTTP requests from hanging tests
// ============================================================================

// Mock fetch globally - tests should explicitly mock API calls
// This prevents hanging tests when fetch is accidentally called without mocking
global.fetch = vi.fn(() =>
  Promise.reject(new Error('Unmocked fetch call in test - please mock the API'))
)

// Mock XMLHttpRequest to prevent jsdom from making real network requests
// jsdom's XHR can hang for 30+ minutes waiting for responses
const createMockXHR = () => ({
  open: vi.fn(),
  send: vi.fn(function() {
    // Immediately trigger error to prevent hanging
    setTimeout(() => {
      if (this.onerror) {
        this.onerror(new Error('Unmocked XMLHttpRequest in test'))
      }
    }, 0)
  }),
  setRequestHeader: vi.fn(),
  abort: vi.fn(),
  getAllResponseHeaders: vi.fn(() => ''),
  getResponseHeader: vi.fn(() => null),
  onload: null,
  onerror: null,
  onreadystatechange: null,
  onabort: null,
  ontimeout: null,
  onprogress: null,
  readyState: 0,
  status: 0,
  statusText: '',
  response: null,
  responseText: '',
  responseType: '',
  responseURL: '',
  timeout: 0,
  withCredentials: false,
  upload: {
    onprogress: null,
    onload: null,
    onerror: null,
  },
})
global.XMLHttpRequest = vi.fn(() => createMockXHR())

// Auto cleanup after each test
afterEach(() => {
  cleanup()
})

// Force clear all timers after all tests to prevent hanging
afterAll(() => {
  vi.clearAllTimers()
  vi.useRealTimers()
})
