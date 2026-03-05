/**
 * Workaround for Zod 4 + @hookform/resolvers type incompatibility.
 * See: https://github.com/react-hook-form/resolvers/issues/800
 * TODO: Remove this file when resolvers#800 is fixed.
 */
import { zodResolver } from '@hookform/resolvers/zod';
import type { Resolver, FieldValues } from 'react-hook-form';
import type { z } from 'zod';

export function createZodResolver<T extends FieldValues>(
  schema: z.ZodType<T>,
): Resolver<T> {
  return zodResolver(
    schema as unknown as Parameters<typeof zodResolver>[0],
  ) as unknown as Resolver<T>;
}
