import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'
import useUndoToast from '../useUndoToast'

// Mock react-hot-toast
vi.mock('react-hot-toast', () => {
  const toast = vi.fn(() => 'toast-id-123')
  toast.dismiss = vi.fn()
  return { default: toast }
})

describe('useUndoToast', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('showUndoToast', () => {
    it('should show toast with success message', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      expect(toast).toHaveBeenCalledTimes(1)
      expect(toast).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          duration: 5000,
          position: 'bottom-center',
        })
      )
    })

    it('should render toast with message and Undo button', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      // Get the render function that was passed to toast
      const renderFunction = toast.mock.calls[0][0]
      const mockToast = { id: 'toast-id-123' }

      // Execute the render function to get the JSX
      const toastContent = renderFunction(mockToast)

      // Verify the structure contains message
      expect(toastContent.props.children[0].props.children).toBe('Tag deleted')

      // Verify there's a button element
      expect(toastContent.props.children[1].type).toBe('button')
      expect(toastContent.props.children[1].props.children).toBe('Undo')
    })

    it('should return toast ID', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      let toastId
      act(() => {
        toastId = result.current.showUndoToast('Tag deleted', onUndo)
      })

      expect(toastId).toBe('toast-id-123')
    })

    it('should execute onUndo callback when Undo button is clicked', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      // Get the render function and execute it
      const renderFunction = toast.mock.calls[0][0]
      const mockToast = { id: 'toast-id-123' }
      const toastContent = renderFunction(mockToast)

      // Get the button's onClick handler
      const undoButton = toastContent.props.children[1]
      const onClick = undoButton.props.onClick

      // Click the Undo button
      act(() => {
        onClick()
      })

      expect(onUndo).toHaveBeenCalledTimes(1)
    })

    it('should dismiss toast immediately when Undo button is clicked', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      // Get the render function and execute it
      const renderFunction = toast.mock.calls[0][0]
      const mockToast = { id: 'toast-id-123' }
      const toastContent = renderFunction(mockToast)

      // Get the button's onClick handler
      const undoButton = toastContent.props.children[1]
      const onClick = undoButton.props.onClick

      // Click the Undo button
      act(() => {
        onClick()
      })

      expect(toast.dismiss).toHaveBeenCalledTimes(1)
      expect(toast.dismiss).toHaveBeenCalledWith('toast-id-123')
    })

    it('should call onUndo before dismissing toast', () => {
      const { result } = renderHook(() => useUndoToast())
      const callOrder = []
      const onUndo = vi.fn(() => callOrder.push('onUndo'))
      toast.dismiss.mockImplementation(() => callOrder.push('dismiss'))

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      // Get the render function and execute it
      const renderFunction = toast.mock.calls[0][0]
      const mockToast = { id: 'toast-id-123' }
      const toastContent = renderFunction(mockToast)

      // Click the Undo button
      const undoButton = toastContent.props.children[1]
      act(() => {
        undoButton.props.onClick()
      })

      expect(callOrder).toEqual(['onUndo', 'dismiss'])
    })

    it('should auto-dismiss after 5 seconds', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      expect(toast).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          duration: 5000,
        })
      )
    })

    it('should display toast at bottom-center position', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo = vi.fn()

      act(() => {
        result.current.showUndoToast('Tag deleted', onUndo)
      })

      expect(toast).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          position: 'bottom-center',
        })
      )
    })
  })

  describe('dismissToast', () => {
    it('should dismiss specific toast by ID', () => {
      const { result } = renderHook(() => useUndoToast())

      act(() => {
        result.current.dismissToast('toast-id-456')
      })

      expect(toast.dismiss).toHaveBeenCalledTimes(1)
      expect(toast.dismiss).toHaveBeenCalledWith('toast-id-456')
    })
  })

  describe('Multiple toasts', () => {
    it('should allow multiple undo toasts to be shown', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo1 = vi.fn()
      const onUndo2 = vi.fn()

      // Mock toast to return different IDs for each call
      toast.mockReturnValueOnce('toast-id-1').mockReturnValueOnce('toast-id-2')

      let toastId1, toastId2
      act(() => {
        toastId1 = result.current.showUndoToast('First deleted', onUndo1)
        toastId2 = result.current.showUndoToast('Second deleted', onUndo2)
      })

      expect(toast).toHaveBeenCalledTimes(2)
      expect(toastId1).toBe('toast-id-1')
      expect(toastId2).toBe('toast-id-2')
    })

    it('should have independent undo callbacks for each toast', () => {
      const { result } = renderHook(() => useUndoToast())
      const onUndo1 = vi.fn()
      const onUndo2 = vi.fn()

      // Mock toast to return different IDs for each call
      toast.mockReturnValueOnce('toast-id-1').mockReturnValueOnce('toast-id-2')

      act(() => {
        result.current.showUndoToast('First deleted', onUndo1)
        result.current.showUndoToast('Second deleted', onUndo2)
      })

      // Get the first toast's render function and execute it
      const renderFunction1 = toast.mock.calls[0][0]
      const mockToast1 = { id: 'toast-id-1' }
      const toastContent1 = renderFunction1(mockToast1)

      // Get the second toast's render function and execute it
      const renderFunction2 = toast.mock.calls[1][0]
      const mockToast2 = { id: 'toast-id-2' }
      const toastContent2 = renderFunction2(mockToast2)

      // Click Undo on first toast
      const undoButton1 = toastContent1.props.children[1]
      act(() => {
        undoButton1.props.onClick()
      })

      expect(onUndo1).toHaveBeenCalledTimes(1)
      expect(onUndo2).not.toHaveBeenCalled()

      // Click Undo on second toast
      const undoButton2 = toastContent2.props.children[1]
      act(() => {
        undoButton2.props.onClick()
      })

      expect(onUndo1).toHaveBeenCalledTimes(1)
      expect(onUndo2).toHaveBeenCalledTimes(1)
    })
  })

  describe('Hook stability', () => {
    it('should return stable function references', () => {
      const { result, rerender } = renderHook(() => useUndoToast())

      const firstShowUndoToast = result.current.showUndoToast
      const firstDismissToast = result.current.dismissToast

      rerender()

      expect(result.current.showUndoToast).toBe(firstShowUndoToast)
      expect(result.current.dismissToast).toBe(firstDismissToast)
    })
  })
})
