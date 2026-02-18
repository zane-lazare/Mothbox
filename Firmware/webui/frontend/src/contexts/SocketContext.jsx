import React, { createContext, useState, useEffect, useMemo } from 'react'
import { io } from 'socket.io-client'

const SocketContext = createContext(null)

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
export function SocketProvider({ children }) {
  const [socket, setSocket] = useState(null)
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

  const contextValue = useMemo(
    () => ({ socket, connected, reconnecting }),
    [socket, connected, reconnecting]
  )

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  )
}

export function useSocketContext() {
  return React.useContext(SocketContext)
}

export default SocketContext
