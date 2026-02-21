import { describe, it, expect } from 'vitest';
import { useFormContext } from 'react-hook-form';
import { z } from 'zod';
import { renderWithForm } from '../renderWithForm';

// A minimal component that consumes form context
function TestInput({ name }: { name: string }) {
  const { register, formState } = useFormContext();
  const error = formState.errors[name];
  return (
    <div>
      <input data-testid="test-input" {...register(name)} />
      {error && <span data-testid="error">{String(error.message)}</span>}
    </div>
  );
}

describe('renderWithForm', () => {
  it('renders a component inside a FormProvider', () => {
    const { getByTestId } = renderWithForm(<TestInput name="email" />, {
      defaultValues: { email: '' },
    });

    expect(getByTestId('test-input')).toBeTruthy();
  });

  it('provides default values to the form', () => {
    const { getByTestId } = renderWithForm(<TestInput name="email" />, {
      defaultValues: { email: 'test@example.com' },
    });

    const input = getByTestId('test-input') as HTMLInputElement;
    expect(input.value).toBe('test@example.com');
  });

  it('exposes formMethods for programmatic access', () => {
    const { formMethods } = renderWithForm(<TestInput name="email" />, {
      defaultValues: { email: 'hello' },
    });

    expect(formMethods).toBeTruthy();
    expect(formMethods.getValues('email')).toBe('hello');
  });

  it('works with a Zod schema', () => {
    const schema = z.object({
      email: z.string().min(1, 'Required'),
    });

    const { getByTestId } = renderWithForm(<TestInput name="email" />, {
      defaultValues: { email: '' },
      schema,
    });

    expect(getByTestId('test-input')).toBeTruthy();
  });
});
