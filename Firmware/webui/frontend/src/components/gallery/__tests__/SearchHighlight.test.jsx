import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SearchHighlight from '../SearchHighlight'

describe('SearchHighlight', () => {
  it('renders nothing when highlights is null', () => {
    const { container } = render(<SearchHighlight highlights={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when highlights is empty object', () => {
    const { container } = render(<SearchHighlight highlights={{}} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when highlights has no <mark> tags', () => {
    const { container } = render(
      <SearchHighlight highlights={{ tags: 'no marks here' }} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders highlighted text with mark tags', () => {
    render(
      <SearchHighlight
        highlights={{ tags: '<mark>luna</mark> moth nocturnal' }}
      />
    )

    // Should show the field label
    expect(screen.getByText(/tags:/i)).toBeInTheDocument()

    // Should show the highlighted text in a <mark> element
    const mark = screen.getByText('luna')
    expect(mark.tagName).toBe('MARK')

    // Should show surrounding text
    expect(screen.getByText(/moth nocturnal/)).toBeInTheDocument()
  })

  it('renders multiple fields with highlights', () => {
    render(
      <SearchHighlight
        highlights={{
          tags: '<mark>luna</mark> moth',
          species: 'Actias <mark>luna</mark>'
        }}
      />
    )

    // Should show both field labels
    expect(screen.getByText(/tags:/i)).toBeInTheDocument()
    expect(screen.getByText(/species:/i)).toBeInTheDocument()

    // Should have two <mark> elements
    const marks = screen.getAllByRole('mark')
    expect(marks).toHaveLength(2)
  })

  it('respects maxFields limit', () => {
    render(
      <SearchHighlight
        highlights={{
          tags: '<mark>luna</mark>',
          species: '<mark>actias</mark>',
          notes: '<mark>beautiful</mark>'
        }}
        maxFields={2}
      />
    )

    // Should only show 2 fields
    const marks = screen.getAllByRole('mark')
    expect(marks).toHaveLength(2)
  })

  it('handles multiple highlights in one field', () => {
    render(
      <SearchHighlight
        highlights={{
          notes: 'The <mark>luna</mark> moth is a beautiful <mark>specimen</mark>'
        }}
      />
    )

    // Should have two <mark> elements
    const marks = screen.getAllByRole('mark')
    expect(marks).toHaveLength(2)
    expect(marks[0]).toHaveTextContent('luna')
    expect(marks[1]).toHaveTextContent('specimen')
  })

  it('applies custom className', () => {
    const { container } = render(
      <SearchHighlight
        highlights={{ tags: '<mark>luna</mark>' }}
        className="custom-class"
      />
    )

    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('escapes potentially dangerous content', () => {
    // Attempt to inject script via highlight
    render(
      <SearchHighlight
        highlights={{
          tags: '<mark><script>alert("xss")</script></mark>'
        }}
      />
    )

    // The content should be rendered as text, not as script
    // The parseHighlight function extracts text between <mark> tags safely
    const mark = screen.getByRole('mark')
    expect(mark).toHaveTextContent('<script>alert("xss")</script>')
  })
})
