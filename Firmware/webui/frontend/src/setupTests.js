// Setup file for Vitest + React Testing Library
import '@testing-library/jest-dom'

// Mock scrollIntoView which is not implemented in jsdom
Element.prototype.scrollIntoView = vi.fn()
