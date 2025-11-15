import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetadataField from '../MetadataField'

// Mock CopyButton component
vi.mock('../CopyButton', () => ({
  default: ({ text }) => <button data-testid="copy-button">Copy {text}</button>
}))

describe('MetadataField', () => {
  describe('Rendering', () => {
    it('renders label and value', () => {
      render(<MetadataField label="Camera Model" value="Arducam OwlSight" />)

      expect(screen.getByText('Camera Model')).toBeInTheDocument()
      expect(screen.getByText('Arducam OwlSight')).toBeInTheDocument()
    })

    it('renders N/A for null value', () => {
      render(<MetadataField label="GPS Location" value={null} />)

      expect(screen.getByText('GPS Location')).toBeInTheDocument()
      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('renders N/A for undefined value', () => {
      render(<MetadataField label="Altitude" value={undefined} />)

      expect(screen.getByText('Altitude')).toBeInTheDocument()
      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('renders N/A for empty string value', () => {
      render(<MetadataField label="Description" value="" />)

      expect(screen.getByText('Description')).toBeInTheDocument()
      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('renders zero as a valid value', () => {
      render(<MetadataField label="ISO" value={0} />)

      expect(screen.getByText('ISO')).toBeInTheDocument()
      expect(screen.getByText('0')).toBeInTheDocument()
      expect(screen.queryByText('N/A')).not.toBeInTheDocument()
    })

    it('renders false as a valid value', () => {
      render(<MetadataField label="HDR Mode" value={false} />)

      expect(screen.getByText('HDR Mode')).toBeInTheDocument()
      expect(screen.getByText('false')).toBeInTheDocument()
      expect(screen.queryByText('N/A')).not.toBeInTheDocument()
    })
  })

  describe('CopyButton Integration', () => {
    it('renders CopyButton when copyable is true', () => {
      render(<MetadataField label="Filename" value="IMG_001.jpg" copyable />)

      expect(screen.getByTestId('copy-button')).toBeInTheDocument()
      expect(screen.getByText('Copy IMG_001.jpg')).toBeInTheDocument()
    })

    it('does not render CopyButton when copyable is false', () => {
      render(<MetadataField label="Filename" value="IMG_001.jpg" copyable={false} />)

      expect(screen.queryByTestId('copy-button')).not.toBeInTheDocument()
    })

    it('does not render CopyButton when copyable is not provided', () => {
      render(<MetadataField label="Filename" value="IMG_001.jpg" />)

      expect(screen.queryByTestId('copy-button')).not.toBeInTheDocument()
    })

    it('does not render CopyButton when value is N/A', () => {
      render(<MetadataField label="GPS Location" value={null} copyable />)

      expect(screen.getByText('N/A')).toBeInTheDocument()
      expect(screen.queryByTestId('copy-button')).not.toBeInTheDocument()
    })

    it('passes the correct text to CopyButton', () => {
      render(<MetadataField label="Coordinates" value="12.345, -67.890" copyable />)

      expect(screen.getByText('Copy 12.345, -67.890')).toBeInTheDocument()
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className to container', () => {
      const { container } = render(
        <MetadataField label="Test" value="Value" className="custom-field" />
      )

      const fieldElement = container.querySelector('.custom-field')
      expect(fieldElement).toBeInTheDocument()
    })

    it('combines custom className with default classes', () => {
      const { container } = render(
        <MetadataField label="Test" value="Value" className="mt-4" />
      )

      const fieldElement = container.querySelector('.mt-4')
      expect(fieldElement).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('renders label and value in separate elements', () => {
      render(<MetadataField label="Camera" value="OwlSight" />)

      const labelElement = screen.getByText('Camera')
      const valueElement = screen.getByText('OwlSight')

      expect(labelElement).toBeInTheDocument()
      expect(valueElement).toBeInTheDocument()
      expect(labelElement).not.toBe(valueElement)
    })

    it('renders with proper semantic structure', () => {
      const { container } = render(
        <MetadataField label="Test Label" value="Test Value" />
      )

      // Should have a container div
      expect(container.firstChild).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('Edge Cases', () => {
    it('handles very long values without breaking layout', () => {
      const longValue = 'A'.repeat(200)
      render(<MetadataField label="Long Value" value={longValue} />)

      expect(screen.getByText(longValue)).toBeInTheDocument()
    })

    it('handles special characters in value', () => {
      const specialValue = '!@#$%^&*()_+-={}[]|\\:";\'<>?,./'
      render(<MetadataField label="Special" value={specialValue} />)

      expect(screen.getByText(specialValue)).toBeInTheDocument()
    })

    it('handles Unicode characters in value', () => {
      const unicodeValue = '测试 🦋 ñ é'
      render(<MetadataField label="Unicode" value={unicodeValue} />)

      expect(screen.getByText(unicodeValue)).toBeInTheDocument()
    })

    it('handles numeric values correctly', () => {
      render(<MetadataField label="Number" value={42.5} />)

      expect(screen.getByText('42.5')).toBeInTheDocument()
    })
  })
})
