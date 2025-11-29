import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ThumbnailSkeleton from '../ThumbnailSkeleton'
import { HOVER_POPUP_CONFIG } from '../../constants/config'

describe('ThumbnailSkeleton', () => {
  describe('Rendering', () => {
    it('renders with default size (128px)', () => {
      const { container } = render(<ThumbnailSkeleton />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toBeInTheDocument()
      expect(skeleton).toHaveStyle({
        width: `${HOVER_POPUP_CONFIG.THUMBNAIL_SIZE}px`,
        height: `${HOVER_POPUP_CONFIG.THUMBNAIL_SIZE}px`,
      })
    })

    it('renders with custom size', () => {
      const customSize = 256
      const { container } = render(<ThumbnailSkeleton size={customSize} />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveStyle({
        width: `${customSize}px`,
        height: `${customSize}px`,
      })
    })

    it('accepts additional className', () => {
      const { container } = render(<ThumbnailSkeleton className="custom-class" />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveClass('custom-class')
    })

    it('has animate-pulse class applied', () => {
      const { container } = render(<ThumbnailSkeleton />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('has rounded corners (rounded-lg)', () => {
      const { container } = render(<ThumbnailSkeleton />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveClass('rounded-lg')
    })

    it('has gray background (bg-gray-200)', () => {
      const { container } = render(<ThumbnailSkeleton />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveClass('bg-gray-200')
    })
  })

  describe('Accessibility', () => {
    it('has correct ARIA role (status)', () => {
      render(<ThumbnailSkeleton />)

      const skeleton = screen.getByRole('status')
      expect(skeleton).toBeInTheDocument()
    })

    it('has aria-busy attribute set to true', () => {
      render(<ThumbnailSkeleton />)

      const skeleton = screen.getByRole('status')
      expect(skeleton).toHaveAttribute('aria-busy', 'true')
    })

    it('has aria-label "Loading thumbnail"', () => {
      render(<ThumbnailSkeleton />)

      const skeleton = screen.getByRole('status')
      expect(skeleton).toHaveAttribute('aria-label', 'Loading thumbnail')
    })
  })

  describe('Props', () => {
    it('uses HOVER_POPUP_CONFIG.THUMBNAIL_SIZE as default size', () => {
      const { container } = render(<ThumbnailSkeleton />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveStyle({
        width: `${HOVER_POPUP_CONFIG.THUMBNAIL_SIZE}px`,
        height: `${HOVER_POPUP_CONFIG.THUMBNAIL_SIZE}px`,
      })
    })

    it('handles zero size correctly', () => {
      const { container } = render(<ThumbnailSkeleton size={0} />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveStyle({
        width: '0px',
        height: '0px',
      })
    })

    it('handles large size values', () => {
      const largeSize = 512
      const { container } = render(<ThumbnailSkeleton size={largeSize} />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveStyle({
        width: `${largeSize}px`,
        height: `${largeSize}px`,
      })
    })

    it('merges className with default classes', () => {
      const { container } = render(<ThumbnailSkeleton className="extra-class" />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveClass('bg-gray-200')
      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('rounded-lg')
      expect(skeleton).toHaveClass('extra-class')
    })

    it('handles empty className string', () => {
      const { container } = render(<ThumbnailSkeleton className="" />)

      const skeleton = container.querySelector('[role="status"]')
      expect(skeleton).toHaveClass('bg-gray-200')
      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('rounded-lg')
    })
  })
})
