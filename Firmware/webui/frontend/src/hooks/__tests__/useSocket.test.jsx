import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import React from 'react'
import useSocket from '../useSocket'
import { SocketProvider } from '../../contexts/SocketContext'

// Mock socket.io-client
vi.mock('socket.io-client', () => {
  const handlers = {}
  const mockSocket = {
    on: vi.fn((event, cb) => { handlers[event] = cb }),
    off: vi.fn(),
    disconnect: vi.fn(),
  }
  return {
    io: vi.fn(() => mockSocket),
    __mockSocket: mockSocket,
    __handlers: handlers,
  }
})

const wrapper = ({ children }) => (
  <SocketProvider>{children}</SocketProvider>
)

describe('useSocket', () => {
  it('throws when used outside SocketProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => renderHook(() => useSocket())).toThrow(
      'useSocket must be used within a SocketProvider'
    )
    spy.mockRestore()
  })

  it('returns context when inside SocketProvider', () => {
    const { result } = renderHook(() => useSocket(), { wrapper })
    expect(result.current).toBeDefined()
  })

  it('has socket and connected properties', () => {
    const { result } = renderHook(() => useSocket(), { wrapper })
    expect(result.current).toHaveProperty('socket')
    expect(result.current).toHaveProperty('connected')
    expect(typeof result.current.connected).toBe('boolean')
  })

  it('has reconnecting property', () => {
    const { result } = renderHook(() => useSocket(), { wrapper })
    expect(result.current).toHaveProperty('reconnecting')
    expect(typeof result.current.reconnecting).toBe('boolean')
  })
})
