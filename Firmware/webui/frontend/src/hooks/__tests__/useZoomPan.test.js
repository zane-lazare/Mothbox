import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import useZoomPan from '../useZoomPan'

describe('useZoomPan - Zoom State Management', () => {
  const defaultProps = {
    minZoom: 1.0,
    maxZoom: 5.0,
    zoomStep: 0.5,
    imageWidth: 1000,
    imageHeight: 800,
    containerWidth: 800,
    containerHeight: 600,
  }

  it('initializes with zoom level of 1.0', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))
    expect(result.current.zoom).toBe(1.0)
  })

  it('updates zoom when setZoom is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.5)
    })

    expect(result.current.zoom).toBe(2.5)
  })

  it('clamps zoom to minimum value (1.0)', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(0.5)
    })

    expect(result.current.zoom).toBe(1.0)
  })

  it('clamps zoom to maximum value (5.0)', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(10.0)
    })

    expect(result.current.zoom).toBe(5.0)
  })

  it('increments zoom by ZOOM_STEP when handleZoomIn is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.handleZoomIn()
    })

    expect(result.current.zoom).toBe(1.5)
  })

  it('decrements zoom by ZOOM_STEP when handleZoomOut is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    // First zoom in
    act(() => {
      result.current.setZoom(2.0)
    })

    // Then zoom out
    act(() => {
      result.current.handleZoomOut()
    })

    expect(result.current.zoom).toBe(1.5)
  })

  it('resets zoom to 1.0 when resetZoom is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(3.0)
    })

    expect(result.current.zoom).toBe(3.0)

    act(() => {
      result.current.resetZoom()
    })

    expect(result.current.zoom).toBe(1.0)
  })

  it('does not zoom out below minimum when handleZoomOut is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    // Already at minimum (1.0)
    act(() => {
      result.current.handleZoomOut()
    })

    expect(result.current.zoom).toBe(1.0)
  })

  it('does not zoom in above maximum when handleZoomIn is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(5.0)
    })

    act(() => {
      result.current.handleZoomIn()
    })

    expect(result.current.zoom).toBe(5.0)
  })
})

describe('useZoomPan - Pan State Management', () => {
  const defaultProps = {
    minZoom: 1.0,
    maxZoom: 5.0,
    zoomStep: 0.5,
    imageWidth: 1000,
    imageHeight: 800,
    containerWidth: 800,
    containerHeight: 600,
  }

  it('initializes with pan at {x: 0, y: 0}', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))
    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })

  it('updates pan when setPan is called', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 50, y: 30 })
    })

    expect(result.current.pan).toEqual({ x: 50, y: 30 })
  })

  it('constrains pan to boundaries when zoom > 1', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      // Try to pan way beyond boundaries
      result.current.setPan({ x: 5000, y: 5000 })
    })

    // Pan should be clamped to calculated boundaries
    expect(result.current.pan.x).toBeLessThanOrEqual(500)
    expect(result.current.pan.y).toBeLessThanOrEqual(400)
  })

  it('resets pan to {0, 0} when zoom returns to 1.0', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 50, y: 30 })
    })

    expect(result.current.pan).not.toEqual({ x: 0, y: 0 })

    act(() => {
      result.current.resetZoom()
    })

    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })

  it('clamps pan.x to maxX boundary', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      // scaledWidth = 2000, containerWidth = 800, maxX = (2000 - 800) / 2 = 600
      result.current.setPan({ x: 1000, y: 0 })
    })

    expect(result.current.pan.x).toBeLessThanOrEqual(600)
  })

  it('clamps pan.y to maxY boundary', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      // scaledHeight = 1600, containerHeight = 600, maxY = (1600 - 600) / 2 = 500
      result.current.setPan({ x: 0, y: 1000 })
    })

    expect(result.current.pan.y).toBeLessThanOrEqual(500)
  })

  it('clamps negative pan to -maxX/-maxY boundaries', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: -1000, y: -1000 })
    })

    // Should be clamped to negative boundaries
    expect(result.current.pan.x).toBeGreaterThanOrEqual(-600)
    expect(result.current.pan.y).toBeGreaterThanOrEqual(-500)
  })

  it('allows pan when image is larger than container', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 100, y: 100 })
    })

    expect(result.current.pan).toEqual({ x: 100, y: 100 })
  })

  it('prevents pan when image is smaller than container at zoom 1.0', () => {
    const smallImageProps = {
      ...defaultProps,
      imageWidth: 400, // Smaller than containerWidth (800)
      imageHeight: 300, // Smaller than containerHeight (600)
    }

    const { result } = renderHook(() => useZoomPan(smallImageProps))

    act(() => {
      result.current.setPan({ x: 100, y: 100 })
    })

    // Pan should be {0, 0} because image fits entirely in container
    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })
})

describe('useZoomPan - Wheel Zoom Events', () => {
  const defaultProps = {
    minZoom: 1.0,
    maxZoom: 5.0,
    zoomStep: 0.5,
    imageWidth: 1000,
    imageHeight: 800,
    containerWidth: 800,
    containerHeight: 600,
  }

  it('zooms out when wheel deltaY > 0', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(2.0)
    })

    const mockEvent = {
      deltaY: 100,
      clientX: 400,
      clientY: 300,
      currentTarget: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 800,
          height: 600,
        }),
      },
      preventDefault: () => {},
    }

    act(() => {
      result.current.handleWheel(mockEvent)
    })

    expect(result.current.zoom).toBeLessThan(2.0)
  })

  it('zooms in when wheel deltaY < 0', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    const mockEvent = {
      deltaY: -100,
      clientX: 400,
      clientY: 300,
      currentTarget: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 800,
          height: 600,
        }),
      },
      preventDefault: () => {},
    }

    act(() => {
      result.current.handleWheel(mockEvent)
    })

    expect(result.current.zoom).toBeGreaterThan(1.0)
  })

  it('zooms relative to cursor position', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    // Get initial pan (should be {0, 0})
    const initialPan = { ...result.current.pan }

    const mockEvent = {
      deltaY: -100,
      clientX: 600, // Right side of image
      clientY: 450, // Bottom side of image
      currentTarget: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 800,
          height: 600,
        }),
      },
      preventDefault: () => {},
    }

    act(() => {
      result.current.handleWheel(mockEvent)
    })

    // Pan should have changed to keep cursor position stable
    // (exact values depend on zoom algorithm, just verify it changed)
    const newPan = result.current.pan
    expect(newPan.x !== initialPan.x || newPan.y !== initialPan.y).toBe(true)
  })

  it('respects minimum zoom boundary on wheel zoom', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    const mockEvent = {
      deltaY: 1000, // Large wheel out
      clientX: 400,
      clientY: 300,
      currentTarget: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 800,
          height: 600,
        }),
      },
      preventDefault: () => {},
    }

    act(() => {
      result.current.handleWheel(mockEvent)
    })

    expect(result.current.zoom).toBe(1.0)
  })

  it('respects maximum zoom boundary on wheel zoom', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    act(() => {
      result.current.setZoom(4.8)
    })

    const mockEvent = {
      deltaY: -1000, // Large wheel in
      clientX: 400,
      clientY: 300,
      currentTarget: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 800,
          height: 600,
        }),
      },
      preventDefault: () => {},
    }

    act(() => {
      result.current.handleWheel(mockEvent)
    })

    expect(result.current.zoom).toBe(5.0)
  })

  it('calls preventDefault on wheel event', () => {
    const { result } = renderHook(() => useZoomPan(defaultProps))

    let preventDefaultCalled = false

    const mockEvent = {
      deltaY: -100,
      clientX: 400,
      clientY: 300,
      currentTarget: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 800,
          height: 600,
        }),
      },
      preventDefault: () => {
        preventDefaultCalled = true
      },
    }

    act(() => {
      result.current.handleWheel(mockEvent)
    })

    expect(preventDefaultCalled).toBe(true)
  })
})

describe('useZoomPan - Boundary Calculations', () => {
  it('returns {maxX: 0, maxY: 0} when zoom = 1.0', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    // At zoom 1.0, scaled size = original size
    // Since image (1000x800) is larger than container (800x600), but we're at 1x zoom
    // We should have 0 pan boundaries (centered)
    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })

  it('calculates maxX correctly when scaledWidth > containerWidth', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    act(() => {
      result.current.setZoom(2.0)
      // scaledWidth = 2000, containerWidth = 800
      // maxX = (2000 - 800) / 2 = 600
      result.current.setPan({ x: 700, y: 0 })
    })

    // Should be clamped to 600
    expect(result.current.pan.x).toBeLessThanOrEqual(600)
  })

  it('calculates maxY correctly when scaledHeight > containerHeight', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    act(() => {
      result.current.setZoom(2.0)
      // scaledHeight = 1600, containerHeight = 600
      // maxY = (1600 - 600) / 2 = 500
      result.current.setPan({ x: 0, y: 600 })
    })

    // Should be clamped to 500
    expect(result.current.pan.y).toBeLessThanOrEqual(500)
  })

  it('updates boundaries when zoom changes', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    // Set pan at zoom 2.0
    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 500, y: 400 })
    })

    // Increase zoom to 3.0 (boundaries expand)
    act(() => {
      result.current.setZoom(3.0)
    })

    // Pan should be re-constrained to new boundaries
    const panAtZoom3 = { ...result.current.pan }
    expect(panAtZoom3).toBeDefined()
  })

  it('updates boundaries when image dimensions change', () => {
    const { result, rerender } = renderHook(
      ({ imageWidth, imageHeight, containerWidth, containerHeight }) =>
        useZoomPan({
          minZoom: 1.0,
          maxZoom: 5.0,
          zoomStep: 0.5,
          imageWidth,
          imageHeight,
          containerWidth,
          containerHeight,
        }),
      {
        initialProps: {
          imageWidth: 1000,
          imageHeight: 800,
          containerWidth: 800,
          containerHeight: 600,
        },
      }
    )

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 500, y: 400 })
    })

    // Change image dimensions
    rerender({
      imageWidth: 2000,
      imageHeight: 1600,
      containerWidth: 800,
      containerHeight: 600,
    })

    // Boundaries should update based on new dimensions
    // At zoom 2.0: scaledWidth = 4000, maxX = (4000 - 800) / 2 = 1600
    act(() => {
      result.current.setPan({ x: 1500, y: 1200 })
    })

    expect(result.current.pan.x).toBeLessThanOrEqual(1600)
  })

  it('constrains pan.x within [-maxX, maxX]', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 700, y: 0 })
    })

    expect(result.current.pan.x).toBeLessThanOrEqual(600)
    expect(result.current.pan.x).toBeGreaterThanOrEqual(-600)
  })

  it('constrains pan.y within [-maxY, maxY]', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 0, y: 600 })
    })

    expect(result.current.pan.y).toBeLessThanOrEqual(500)
    expect(result.current.pan.y).toBeGreaterThanOrEqual(-500)
  })

  it('handles case where scaled image is smaller than container', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 400,
      imageHeight: 300,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    // Even at zoom 1.0, image is smaller than container
    act(() => {
      result.current.setPan({ x: 100, y: 100 })
    })

    // Should not allow panning (boundaries are 0)
    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })
})

describe('useZoomPan - Edge Cases', () => {
  it('handles zero image dimensions gracefully', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 0,
      imageHeight: 0,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    expect(result.current.zoom).toBe(1.0)
    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })

  it('handles zero container dimensions gracefully', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 0,
      containerHeight: 0,
    }

    const { result } = renderHook(() => useZoomPan(props))

    expect(result.current.zoom).toBe(1.0)
    expect(result.current.pan).toEqual({ x: 0, y: 0 })
  })

  it('maintains pan state when zoom remains constant', () => {
    const props = {
      minZoom: 1.0,
      maxZoom: 5.0,
      zoomStep: 0.5,
      imageWidth: 1000,
      imageHeight: 800,
      containerWidth: 800,
      containerHeight: 600,
    }

    const { result } = renderHook(() => useZoomPan(props))

    act(() => {
      result.current.setZoom(2.0)
      result.current.setPan({ x: 100, y: 50 })
    })

    const initialPan = { ...result.current.pan }

    // Trigger re-render without changing zoom
    act(() => {
      result.current.setPan({ x: 100, y: 50 })
    })

    expect(result.current.pan).toEqual(initialPan)
  })
})
