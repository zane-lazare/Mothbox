import { render, act, cleanup } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import React from 'react'

// Mock socket.io-client before importing SocketProvider
const handlers = {}
const mockSocket = {
  on: vi.fn((event, cb) => { handlers[event] = cb }),
  off: vi.fn(),
  disconnect: vi.fn(),
}

vi.mock('socket.io-client', () => ({
  io: vi.fn(() => mockSocket),
}))

import { SocketProvider, useSocketContext } from '../SocketContext'

// Test consumer that reads and displays context values
function TestConsumer({ onContextReady }) {
  const ctx = useSocketContext()
  React.useEffect(() => {
    onContextReady(ctx)
  })
  return null
}

describe('SocketContext', () => {
  let ctx

  beforeEach(() => {
    ctx = null
    // Clear handlers between tests
    Object.keys(handlers).forEach(key => delete handlers[key])
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  const setupContext = () => {
    return new Promise((resolve) => {
      render(
        <SocketProvider>
          <TestConsumer onContextReady={(c) => { ctx = c; resolve() }} />
        </SocketProvider>
      )
    })
  }

  describe('Initial State', () => {
    it('provides socket and connected state to consumers', async () => {
      await setupContext()
      expect(ctx).toBeDefined()
      expect(ctx).toHaveProperty('socket')
      expect(ctx).toHaveProperty('connected')
    })

    it('has socket object from socket.io-client', async () => {
      await setupContext()
      expect(ctx.socket).toBe(mockSocket)
    })

    it('has connected state initially false', async () => {
      await setupContext()
      expect(ctx.connected).toBe(false)
    })
  })

  describe('Connection Events', () => {
    it('updates connected state to true on socket connect event', async () => {
      await setupContext()
      expect(ctx.connected).toBe(false)

      await act(async () => {
        handlers['connect']()
      })

      expect(ctx.connected).toBe(true)
    })

    it('updates connected state to false on socket disconnect event', async () => {
      await setupContext()

      // First connect
      await act(async () => {
        handlers['connect']()
      })
      expect(ctx.connected).toBe(true)

      // Then disconnect
      await act(async () => {
        handlers['disconnect']()
      })
      expect(ctx.connected).toBe(false)
    })

    it('registers connect and disconnect handlers on the socket', async () => {
      await setupContext()
      expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
    })
  })

  describe('Reconnection', () => {
    it('provides reconnecting state initially false', async () => {
      await setupContext()
      expect(ctx.reconnecting).toBe(false)
    })

    it('sets reconnecting to true on reconnect_attempt event', async () => {
      await setupContext()
      expect(ctx.reconnecting).toBe(false)

      await act(async () => {
        handlers['reconnect_attempt']()
      })

      expect(ctx.reconnecting).toBe(true)
    })

    it('sets reconnecting to false on reconnect event', async () => {
      await setupContext()

      // Start reconnecting
      await act(async () => {
        handlers['reconnect_attempt']()
      })
      expect(ctx.reconnecting).toBe(true)

      // Successfully reconnected
      await act(async () => {
        handlers['reconnect']()
      })
      expect(ctx.reconnecting).toBe(false)
    })

    it('sets reconnecting to false on reconnect_failed event', async () => {
      await setupContext()

      // Start reconnecting
      await act(async () => {
        handlers['reconnect_attempt']()
      })
      expect(ctx.reconnecting).toBe(true)

      // Gave up
      await act(async () => {
        handlers['reconnect_failed']()
      })
      expect(ctx.reconnecting).toBe(false)
    })
  })

  describe('Unmount Cleanup', () => {
    it('disconnects socket on unmount', async () => {
      const { unmount } = render(
        <SocketProvider>
          <TestConsumer onContextReady={(c) => { ctx = c }} />
        </SocketProvider>
      )

      unmount()
      expect(mockSocket.disconnect).toHaveBeenCalled()
    })
  })

  describe('Context Default', () => {
    it('returns null when used outside SocketProvider', () => {
      let value
      function BareConsumer() {
        value = useSocketContext()
        return null
      }

      render(<BareConsumer />)
      expect(value).toBeNull()
    })
  })
})
