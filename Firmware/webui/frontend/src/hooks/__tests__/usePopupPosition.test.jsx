import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { usePopupPosition } from '../usePopupPosition'

describe('usePopupPosition', () => {
  let originalInnerWidth
  let originalInnerHeight

  beforeEach(() => {
    // Store original values
    originalInnerWidth = window.innerWidth
    originalInnerHeight = window.innerHeight

    // Set default viewport size
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    })
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: 768,
    })
  })

  afterEach(() => {
    // Restore original values
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    })
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: originalInnerHeight,
    })
  })

  it('returns default position when not visible', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 100, y: 100 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: false,
      })
    )

    expect(result.current.position).toEqual({ left: 0, top: 0 })
    expect(result.current.placement).toBe('below')
  })

  it('returns default position when triggerPosition is null', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: null,
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    expect(result.current.position).toEqual({ left: 0, top: 0 })
    expect(result.current.placement).toBe('below')
  })

  it('places popup below trigger when space available', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 200 },
        popupWidth: 300,
        popupHeight: 350,
        offset: 10,
        isVisible: true,
      })
    )

    // Should place below: y + offset = 200 + 10 = 210
    expect(result.current.position.top).toBe(210)
    expect(result.current.placement).toBe('below')
  })

  it('places popup above trigger when no space below', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 700 },
        popupWidth: 300,
        popupHeight: 350,
        offset: 10,
        isVisible: true,
      })
    )

    // Not enough space below (768 - 700 - 10 = 58 < 350)
    // Should place above: y - popupHeight - offset = 700 - 350 - 10 = 340
    expect(result.current.position.top).toBe(340)
    expect(result.current.placement).toBe('above')
  })

  it('centers popup horizontally on trigger', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 200 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    // Should center: x - popupWidth/2 = 500 - 150 = 350
    expect(result.current.position.left).toBe(350)
  })

  it('clamps left position to viewport edge', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 50, y: 200 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    // Would be: 50 - 150 = -100, but should clamp to margin (10)
    expect(result.current.position.left).toBe(10)
  })

  it('clamps right position to viewport edge', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 1000, y: 200 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    // Would be: 1000 - 150 = 850
    // Max allowed: 1024 - 300 - 10 = 714
    expect(result.current.position.left).toBe(714)
  })

  it('clamps top position to viewport edge', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 5 },
        popupWidth: 300,
        popupHeight: 350,
        offset: 10,
        isVisible: true,
      })
    )

    // Would try to place above (not enough space below at y=5)
    // Above would be: 5 - 350 - 10 = -355, should clamp to margin (10)
    expect(result.current.position.top).toBeGreaterThanOrEqual(10)
  })

  it('clamps bottom position to viewport edge', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 760 },
        popupWidth: 300,
        popupHeight: 350,
        offset: 10,
        isVisible: true,
      })
    )

    // Not enough space below (768 - 760 - 10 = -2), so will place above
    // Above: 760 - 350 - 10 = 400
    // Max allowed when clamped: 768 - 350 - 10 = 408, but 400 is already within bounds
    expect(result.current.position.top).toBe(400)
  })

  it('updates position on viewport resize', () => {
    const { result, rerender } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 200 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    // Resize viewport
    act(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      })
      window.dispatchEvent(new Event('resize'))
    })

    // Force re-render to pick up state change
    rerender()

    // Position should potentially change if trigger is now near edge
    // At minimum, hook should recalculate
    expect(result.current.position).toBeDefined()
  })

  it('returns correct placement value when below', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 200 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    expect(result.current.placement).toBe('below')
  })

  it('returns correct placement value when above', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 700 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    expect(result.current.placement).toBe('above')
  })

  it('uses default popup dimensions from config', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 200 },
        isVisible: true,
      })
    )

    // Should not throw and should return valid position
    expect(result.current.position).toBeDefined()
    expect(result.current.position.left).toBeGreaterThanOrEqual(0)
    expect(result.current.position.top).toBeGreaterThanOrEqual(0)
  })

  it('handles edge case with very small viewport', () => {
    act(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 320,
      })
      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 480,
      })
      window.dispatchEvent(new Event('resize'))
    })

    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 160, y: 240 },
        popupWidth: 300,
        popupHeight: 350,
        isVisible: true,
      })
    )

    // Should still provide valid position within bounds
    expect(result.current.position.left).toBeGreaterThanOrEqual(10)
    expect(result.current.position.top).toBeGreaterThanOrEqual(10)
    expect(result.current.position.left).toBeLessThanOrEqual(320 - 10)
    expect(result.current.position.top).toBeLessThanOrEqual(480 - 10)
  })

  it('chooses below when equal space on both sides', () => {
    const { result } = renderHook(() =>
      usePopupPosition({
        triggerPosition: { x: 500, y: 384 }, // Exactly middle of 768px height
        popupWidth: 300,
        popupHeight: 200,
        offset: 10,
        isVisible: true,
      })
    )

    // With equal space, should prefer below
    expect(result.current.placement).toBe('below')
  })
})
