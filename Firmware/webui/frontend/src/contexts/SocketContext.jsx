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

  useEffect(() => {
    const newSocket = io(window.location.origin, {
      transports: ['websocket', 'polling'],
    })

    newSocket.on('connect', () => {
      setConnected(true)
    })

    newSocket.on('disconnect', () => {
      setConnected(false)
    })

    setSocket(newSocket)

    return () => {
      newSocket.disconnect()
    }
  }, [])

  const contextValue = useMemo(
    () => ({ socket, connected }),
    [socket, connected]
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
