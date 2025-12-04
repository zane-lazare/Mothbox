import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AccordionSection from '../AccordionSection'
import { TagIcon } from '@heroicons/react/24/outline'

// Mock ChevronDownIcon
vi.mock('@heroicons/react/24/outline', () => ({
  ChevronDownIcon: ({ className }) => <div data-testid="chevron-icon" className={className}>ChevronDown</div>,
  TagIcon: () => <div data-testid="tag-icon">Tag</div>,
}))

describe('AccordionSection', () => {
  it('test_renders_header_and_content', () => {
    render(
      <AccordionSection title="Test Section" icon={<TagIcon />}>
        <div>Test Content</div>
      </AccordionSection>
    )

    expect(screen.getByText('Test Section')).toBeInTheDocument()
    expect(screen.getByTestId('tag-icon')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
    expect(screen.getByTestId('chevron-icon')).toBeInTheDocument()
  })

  it('test_starts_expanded_by_default', () => {
    render(
      <AccordionSection title="Test Section">
        <div>Test Content</div>
      </AccordionSection>
    )

    const content = screen.getByText('Test Content')
    expect(content).toBeVisible()

    const header = screen.getByRole('button')
    expect(header).toHaveAttribute('aria-expanded', 'true')
  })

  it('test_starts_collapsed_when_defaultExpanded_false', () => {
    render(
      <AccordionSection title="Test Section" defaultExpanded={false}>
        <div>Test Content</div>
      </AccordionSection>
    )

    const header = screen.getByRole('button')
    expect(header).toHaveAttribute('aria-expanded', 'false')

    // Content div should have max-h-0 class when collapsed
    const contentContainer = screen.getByText('Test Content').parentElement.parentElement
    expect(contentContainer.className).toContain('max-h-0')
  })

  it('test_toggles_on_header_click', () => {
    render(
      <AccordionSection title="Test Section" defaultExpanded={true}>
        <div>Test Content</div>
      </AccordionSection>
    )

    const header = screen.getByRole('button')

    // Initially expanded
    expect(header).toHaveAttribute('aria-expanded', 'true')

    // Click to collapse
    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'false')

    // Click to expand again
    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'true')
  })

  it('test_has_proper_aria_attributes', () => {
    render(
      <AccordionSection title="Test Section">
        <div>Test Content</div>
      </AccordionSection>
    )

    const header = screen.getByRole('button')

    // Check aria-expanded
    expect(header).toHaveAttribute('aria-expanded')

    // Check aria-controls
    expect(header).toHaveAttribute('aria-controls')
    const controlsId = header.getAttribute('aria-controls')
    expect(controlsId).toBeTruthy()

    // Check that controlled element exists with matching id
    const contentElement = document.getElementById(controlsId)
    expect(contentElement).toBeInTheDocument()
  })

  it('test_keyboard_space_toggles', () => {
    render(
      <AccordionSection title="Test Section" defaultExpanded={true}>
        <div>Test Content</div>
      </AccordionSection>
    )

    const header = screen.getByRole('button')

    // Initially expanded
    expect(header).toHaveAttribute('aria-expanded', 'true')

    // Press Space to collapse
    fireEvent.keyDown(header, { key: ' ', code: 'Space' })
    expect(header).toHaveAttribute('aria-expanded', 'false')

    // Press Space to expand again
    fireEvent.keyDown(header, { key: ' ', code: 'Space' })
    expect(header).toHaveAttribute('aria-expanded', 'true')
  })

  it('test_keyboard_enter_toggles', () => {
    render(
      <AccordionSection title="Test Section" defaultExpanded={true}>
        <div>Test Content</div>
      </AccordionSection>
    )

    const header = screen.getByRole('button')

    // Initially expanded
    expect(header).toHaveAttribute('aria-expanded', 'true')

    // Press Enter to collapse
    fireEvent.keyDown(header, { key: 'Enter', code: 'Enter' })
    expect(header).toHaveAttribute('aria-expanded', 'false')

    // Press Enter to expand again
    fireEvent.keyDown(header, { key: 'Enter', code: 'Enter' })
    expect(header).toHaveAttribute('aria-expanded', 'true')
  })

  it('test_icon_rotates_on_expand', () => {
    render(
      <AccordionSection title="Test Section" defaultExpanded={false}>
        <div>Test Content</div>
      </AccordionSection>
    )

    const chevronIcon = screen.getByTestId('chevron-icon')
    const header = screen.getByRole('button')

    // Initially collapsed - no rotation
    expect(chevronIcon.className).not.toContain('rotate-180')

    // Click to expand - should rotate
    fireEvent.click(header)
    expect(chevronIcon.className).toContain('rotate-180')

    // Click to collapse - rotation removed
    fireEvent.click(header)
    expect(chevronIcon.className).not.toContain('rotate-180')
  })

  it('test_applies_custom_className', () => {
    const customClass = 'custom-accordion-class'
    const { container } = render(
      <AccordionSection title="Test Section" className={customClass}>
        <div>Test Content</div>
      </AccordionSection>
    )

    // The wrapper div should have the custom class
    const wrapper = container.firstChild
    expect(wrapper.className).toContain(customClass)
  })
})
