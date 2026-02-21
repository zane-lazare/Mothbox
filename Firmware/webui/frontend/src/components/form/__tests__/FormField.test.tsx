import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FormField } from '../FormField'
import { FormSelect } from '../FormSelect'
import { FormNumberInput } from '../FormNumberInput'

// ---------------------------------------------------------------------------
// FormField
// ---------------------------------------------------------------------------
describe('FormField', () => {
  it('renders label with htmlFor', () => {
    render(
      <FormField name="username" label="Username">
        <input />
      </FormField>
    )

    const label = screen.getByText('Username')
    expect(label).toBeInTheDocument()
    expect(label.tagName).toBe('LABEL')
    expect(label).toHaveAttribute('for', 'username')
  })

  it('renders child with id matching name', () => {
    render(
      <FormField name="email">
        <input data-testid="child-input" />
      </FormField>
    )

    const input = screen.getByTestId('child-input')
    expect(input).toHaveAttribute('id', 'email')
  })

  it('renders error message with role="alert"', () => {
    render(
      <FormField name="email" error={{ message: 'Email is required' }}>
        <input />
      </FormField>
    )

    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
    expect(alert).toHaveTextContent('Email is required')
    expect(alert).toHaveAttribute('id', 'email-error')
  })

  it('sets aria-invalid on child when error exists', () => {
    render(
      <FormField name="email" error={{ message: 'Invalid' }}>
        <input data-testid="child-input" />
      </FormField>
    )

    const input = screen.getByTestId('child-input')
    expect(input).toHaveAttribute('aria-invalid', 'true')
  })

  it('sets aria-describedby pointing to error element', () => {
    render(
      <FormField name="email" error={{ message: 'Bad email' }}>
        <input data-testid="child-input" />
      </FormField>
    )

    const input = screen.getByTestId('child-input')
    expect(input).toHaveAttribute('aria-describedby', 'email-error')
  })

  it('renders helper text when no error', () => {
    render(
      <FormField name="email" helperText="We will never share your email">
        <input />
      </FormField>
    )

    expect(screen.getByText('We will never share your email')).toBeInTheDocument()
  })

  it('hides helper text when error is shown', () => {
    render(
      <FormField
        name="email"
        error={{ message: 'Required' }}
        helperText="We will never share your email"
      >
        <input />
      </FormField>
    )

    expect(screen.getByText('Required')).toBeInTheDocument()
    expect(screen.queryByText('We will never share your email')).not.toBeInTheDocument()
  })

  it('sets aria-describedby pointing to helper text when no error', () => {
    render(
      <FormField name="email" helperText="Helpful hint">
        <input data-testid="child-input" />
      </FormField>
    )

    const input = screen.getByTestId('child-input')
    expect(input).toHaveAttribute('aria-describedby', 'email-help')
  })

  it('renders without label', () => {
    render(
      <FormField name="email">
        <input data-testid="child-input" />
      </FormField>
    )

    expect(screen.queryByRole('label')).not.toBeInTheDocument()
    const input = screen.getByTestId('child-input')
    expect(input).toHaveAttribute('id', 'email')
  })

  it('renders without error or helper', () => {
    render(
      <FormField name="email">
        <input data-testid="child-input" />
      </FormField>
    )

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    const input = screen.getByTestId('child-input')
    expect(input).toHaveAttribute('aria-invalid', 'false')
    expect(input).not.toHaveAttribute('aria-describedby')
  })
})

// ---------------------------------------------------------------------------
// FormSelect
// ---------------------------------------------------------------------------
describe('FormSelect', () => {
  const defaultOptions = [
    { value: 'a', label: 'Alpha' },
    { value: 'b', label: 'Beta' },
    { value: 'c', label: 'Gamma' },
  ]

  it('renders options', () => {
    render(<FormSelect name="letter" options={defaultOptions} />)

    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()

    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(3)
    expect(options[0]).toHaveTextContent('Alpha')
    expect(options[1]).toHaveTextContent('Beta')
    expect(options[2]).toHaveTextContent('Gamma')
  })

  it('displays error message', () => {
    render(
      <FormSelect
        name="letter"
        options={defaultOptions}
        error={{ message: 'Selection required' }}
      />
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Selection required')

    const select = screen.getByRole('combobox')
    expect(select).toHaveAttribute('aria-invalid', 'true')
    expect(select).toHaveAttribute('aria-describedby', 'letter-error')
  })

  it('applies disabled state', () => {
    render(
      <FormSelect name="letter" options={defaultOptions} disabled />
    )

    const select = screen.getByRole('combobox')
    expect(select).toBeDisabled()
  })

  it('renders label with htmlFor', () => {
    render(
      <FormSelect name="letter" label="Pick a letter" options={defaultOptions} />
    )

    const label = screen.getByText('Pick a letter')
    expect(label.tagName).toBe('LABEL')
    expect(label).toHaveAttribute('for', 'letter')
  })

  it('renders helper text when no error', () => {
    render(
      <FormSelect
        name="letter"
        options={defaultOptions}
        helperText="Choose wisely"
      />
    )

    expect(screen.getByText('Choose wisely')).toBeInTheDocument()
  })

  it('hides helper text when error is shown', () => {
    render(
      <FormSelect
        name="letter"
        options={defaultOptions}
        error={{ message: 'Oops' }}
        helperText="Choose wisely"
      />
    )

    expect(screen.getByText('Oops')).toBeInTheDocument()
    expect(screen.queryByText('Choose wisely')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// FormNumberInput
// ---------------------------------------------------------------------------
describe('FormNumberInput', () => {
  it('renders with min/max/step', () => {
    render(
      <FormNumberInput name="count" min={0} max={100} step={5} />
    )

    const input = screen.getByRole('spinbutton')
    expect(input).toHaveAttribute('type', 'number')
    expect(input).toHaveAttribute('min', '0')
    expect(input).toHaveAttribute('max', '100')
    expect(input).toHaveAttribute('step', '5')
  })

  it('displays error message', () => {
    render(
      <FormNumberInput
        name="count"
        error={{ message: 'Must be positive' }}
      />
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Must be positive')

    const input = screen.getByRole('spinbutton')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'count-error')
  })

  it('applies disabled state', () => {
    render(
      <FormNumberInput name="count" disabled />
    )

    const input = screen.getByRole('spinbutton')
    expect(input).toBeDisabled()
  })

  it('renders label with htmlFor', () => {
    render(
      <FormNumberInput name="count" label="Item Count" />
    )

    const label = screen.getByText('Item Count')
    expect(label.tagName).toBe('LABEL')
    expect(label).toHaveAttribute('for', 'count')
  })

  it('renders helper text when no error', () => {
    render(
      <FormNumberInput name="count" helperText="Enter a number" />
    )

    expect(screen.getByText('Enter a number')).toBeInTheDocument()
  })

  it('hides helper text when error is shown', () => {
    render(
      <FormNumberInput
        name="count"
        error={{ message: 'Too large' }}
        helperText="Enter a number"
      />
    )

    expect(screen.getByText('Too large')).toBeInTheDocument()
    expect(screen.queryByText('Enter a number')).not.toBeInTheDocument()
  })
})
