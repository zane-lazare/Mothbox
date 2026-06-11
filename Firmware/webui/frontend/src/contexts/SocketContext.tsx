import React, { createContext, useState, useEffect, useMemo, ReactNode } from 'react'
import { io, Socket } from 'socket.io-client'

interface SocketContextValue {
  socket: Socket | null
  connected: boolean
  reconnecting: boolean
}

interface SocketProviderProps {
  children: ReactNode
}

const SocketContext = createContext<SocketContextValue | undefined>(undefined)

/**
 * SocketProvider - Centralized Socket.io connection provider (#368)
 *
 * Creates a single shared Socket.io connection on mount and exposes it
 * to all child components via context. This eliminates duplicate connections
 * previously created independently by Camera, Settings, and ActivationProgress.
 *
 * @important Components must NOT call socket.disconnect() in their cleanup.
 * Only use socket.off() to remove event listeners. The provider owns the
 * connection lifecycle and will disconnect on unmount.
 */
export function SocketProvider({ children }: SocketProviderProps) {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)

  useEffect(() => {
    const newSocket = io(window.location.origin, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    newSocket.on('connect', () => {
      setConnected(true)
      setReconnecting(false)
    })

    newSocket.on('disconnect', () => {
      setConnected(false)
    })

    newSocket.on('reconnect_attempt', () => {
      setReconnecting(true)
    })

    newSocket.on('reconnect', () => {
      setReconnecting(false)
    })

    newSocket.on('reconnect_failed', () => {
      setReconnecting(false)
    })

    setSocket(newSocket)

    return () => {
      newSocket.disconnect()
    }
  }, [])

  const contextValue = useMemo<SocketContextValue>(
    () => ({ socket, connected, reconnecting }),
    [socket, connected, reconnecting]
  )

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  )
}

export function useSocketContext(): SocketContextValue {
  const context = React.useContext(SocketContext)

  if (!context) {
    throw new Error('useSocketContext must be used within SocketProvider')
  }

  return context
}

export default SocketContext
