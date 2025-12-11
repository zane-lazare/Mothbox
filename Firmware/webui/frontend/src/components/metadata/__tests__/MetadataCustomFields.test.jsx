import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MetadataCustomFields from '../MetadataCustomFields'

describe('MetadataCustomFields', () => {
  it('test_renders_existing_key_value_pairs', () => {
    const fields = {
      'Location': 'Forest',
      'Weather': 'Sunny',
      'Temperature': '72F'
    }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    // Check that all key inputs are rendered with correct values
    expect(screen.getByDisplayValue('Location')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Forest')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Weather')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Sunny')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Temperature')).toBeInTheDocument()
    expect(screen.getByDisplayValue('72F')).toBeInTheDocument()

    // Check that delete buttons are rendered for each field
    const deleteButtons = screen.getAllByLabelText(/Delete field/i)
    expect(deleteButtons).toHaveLength(3)
  })

  it('test_add_field_button_creates_new_pair', () => {
    const fields = { 'existing': 'value' }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    const addButton = screen.getByRole('button', { name: /Add custom field/i })
    fireEvent.click(addButton)

    expect(onChange).toHaveBeenCalledTimes(1)
    const newFields = onChange.mock.calls[0][0]

    // Should have the existing field plus a new empty field
    expect(Object.keys(newFields).length).toBe(2)
    expect(newFields['existing']).toBe('value')

    // New field should have an auto-generated key and empty value
    const newKey = Object.keys(newFields).find(k => k !== 'existing')
    expect(newKey).toBeTruthy()
    expect(newFields[newKey]).toBe('')
  })

  it('test_editing_key_calls_onChange', () => {
    const fields = { 'OldKey': 'value' }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    const keyInput = screen.getByDisplayValue('OldKey')
    fireEvent.change(keyInput, { target: { value: 'NewKey' } })

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith({ 'NewKey': 'value' })
  })

  it('test_editing_value_calls_onChange', () => {
    const fields = { 'key': 'OldValue' }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    const valueInput = screen.getByDisplayValue('OldValue')
    fireEvent.change(valueInput, { target: { value: 'NewValue' } })

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith({ 'key': 'NewValue' })
  })

  it('test_delete_button_removes_pair', () => {
    const fields = {
      'Field1': 'Value1',
      'Field2': 'Value2'
    }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    const deleteButton = screen.getByLabelText('Delete field Field1')
    fireEvent.click(deleteButton)

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith({ 'Field2': 'Value2' })
  })

  it('test_validates_unique_keys', () => {
    const fields = {
      'existing': 'value1',
      'another': 'value2'
    }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    // Try to change 'another' to 'existing' (duplicate)
    const keyInput = screen.getByDisplayValue('another')
    fireEvent.change(keyInput, { target: { value: 'existing' } })

    // Should show error message
    expect(screen.getByText('Key "existing" already exists')).toBeInTheDocument()

    // onChange should not be called due to validation error
    expect(onChange).not.toHaveBeenCalled()
  })

  it('test_max_100_custom_fields', () => {
    // Create 100 fields
    const fields = {}
    for (let i = 0; i < 100; i++) {
      fields[`field${i}`] = `value${i}`
    }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} />)

    const addButton = screen.getByRole('button', { name: /Add custom field/i })

    // Button should be disabled
    expect(addButton).toBeDisabled()

    // Should show max limit message
    expect(screen.getByText(/max 100/i)).toBeInTheDocument()
  })

  it('test_empty_state_shows_add_button', () => {
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={{}} onChange={onChange} />)

    // Should show empty state message
    expect(screen.getByText('No custom fields')).toBeInTheDocument()

    // Should still show add button
    expect(screen.getByRole('button', { name: /Add custom field/i })).toBeInTheDocument()
  })

  it('test_disabled_state', () => {
    const fields = { 'key': 'value' }
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={fields} onChange={onChange} disabled={true} />)

    // Input fields should be disabled
    const keyInput = screen.getByDisplayValue('key')
    const valueInput = screen.getByDisplayValue('value')
    expect(keyInput).toBeDisabled()
    expect(valueInput).toBeDisabled()

    // Delete button should be disabled
    const deleteButton = screen.getByLabelText('Delete field key')
    expect(deleteButton).toBeDisabled()

    // Add button should be disabled
    const addButton = screen.getByRole('button', { name: /Add custom field/i })
    expect(addButton).toBeDisabled()
  })

  it('test_key_placeholder', () => {
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={{}} onChange={onChange} />)

    // Click add to create a new empty field
    const addButton = screen.getByRole('button', { name: /Add custom field/i })
    fireEvent.click(addButton)

    // Re-render with the new field
    const newFields = onChange.mock.calls[0][0]
    render(<MetadataCustomFields fields={newFields} onChange={onChange} />)

    // Should show "Field name" placeholder
    const keyInput = screen.getByPlaceholderText('Field name')
    expect(keyInput).toBeInTheDocument()
  })

  it('test_value_placeholder', () => {
    const onChange = vi.fn()

    render(<MetadataCustomFields fields={{}} onChange={onChange} />)

    // Click add to create a new empty field
    const addButton = screen.getByRole('button', { name: /Add custom field/i })
    fireEvent.click(addButton)

    // Re-render with the new field
    const newFields = onChange.mock.calls[0][0]
    render(<MetadataCustomFields fields={newFields} onChange={onChange} />)

    // Should show "Value" placeholder
    const valueInput = screen.getByPlaceholderText('Value')
    expect(valueInput).toBeInTheDocument()
  })
})
