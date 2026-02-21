import { render, type RenderOptions } from '@testing-library/react';
import {
  FormProvider,
  useForm,
  type UseFormProps,
  type FieldValues,
  type UseFormReturn,
  type Resolver,
} from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { ReactElement } from 'react';
import type { ZodType } from 'zod';

interface RenderWithFormOptions<T extends FieldValues>
  extends Omit<RenderOptions, 'wrapper'> {
  /** Default form values */
  defaultValues?: T;
  /** Zod schema for validation */
  schema?: ZodType;
  /** Additional useForm options */
  formOptions?: Omit<UseFormProps<T>, 'defaultValues' | 'resolver'>;
}

// Store for capturing form methods from inside the wrapper
let _capturedMethods: UseFormReturn<FieldValues> | null = null;

/**
 * Render a component wrapped in a FormProvider for testing.
 * Returns all @testing-library/react utilities plus form methods.
 *
 * @example
 * ```tsx
 * const { getByRole } = renderWithForm(
 *   <FormField name="email" label="Email">
 *     <input />
 *   </FormField>,
 *   { defaultValues: { email: '' } }
 * );
 * ```
 */
export function renderWithForm<T extends FieldValues = FieldValues>(
  ui: ReactElement,
  options: RenderWithFormOptions<T> = {},
) {
  const { defaultValues, schema, formOptions, ...renderOptions } = options;

  // Reset captured methods
  _capturedMethods = null;

  // Build the resolver with a type assertion. The zodResolver overloads
  // expect the schema's input type to be FieldValues (Record<string, any>),
  // but Zod 4's ZodType uses `unknown` for the input parameter by default.
  // The cast is safe because the schema validates the same shape as T at
  // runtime — we go through `unknown` to avoid `any`.
  const resolver = schema
    ? (zodResolver(schema as unknown as Parameters<typeof zodResolver>[0]) as Resolver<T>)
    : undefined;

  // Wrapper component that creates the form context
  function FormWrapper({ children }: { children: React.ReactNode }) {
    const methods = useForm<T>({
      defaultValues: defaultValues as UseFormProps<T>['defaultValues'],
      resolver,
      ...formOptions,
    });

    // Capture methods so they can be returned to the caller
    _capturedMethods = methods as UseFormReturn<FieldValues>;

    return <FormProvider {...methods}>{children}</FormProvider>;
  }

  const result = render(ui, {
    wrapper: FormWrapper,
    ...renderOptions,
  });

  return {
    ...result,
    /** Access to the underlying react-hook-form methods */
    formMethods: _capturedMethods as unknown as UseFormReturn<T>,
  };
}
