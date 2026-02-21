import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import vitestPlugin from '@vitest/eslint-plugin'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
  {
    // TypeScript files
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
  {
    // Context files export both Provider and hooks - this is a valid pattern
    files: ['**/contexts/**/*.{js,jsx,ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    // Config files run in Node.js environment
    files: ['*.config.js', '*.config.mjs'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  {
    // Deprecated validation utilities — warn on new imports (#197)
    files: ['**/*.{js,jsx,ts,tsx}'],
    rules: {
      'no-restricted-imports': ['warn', {
        paths: [
          { name: '../utils/gpsValidation', message: 'Deprecated: use schemas/gps-settings.ts instead (#197)' },
          { name: '../../utils/gpsValidation', message: 'Deprecated: use schemas/gps-settings.ts instead (#197)' },
          { name: '../utils/presetValidation', message: 'Deprecated: use schemas/camera-preset.ts instead (#197)' },
          { name: '../../utils/presetValidation', message: 'Deprecated: use schemas/camera-preset.ts instead (#197)' },
          { name: '../utils/gpsCoordinates', message: 'Deprecated: use schemas/coordinates.ts instead (#197)' },
          { name: '../../utils/gpsCoordinates', message: 'Deprecated: use schemas/coordinates.ts instead (#197)' },
        ],
        patterns: [
          { group: ['**/utils/gpsValidation'], message: 'Deprecated: use schemas/gps-settings.ts instead (#197)' },
          { group: ['**/utils/presetValidation'], message: 'Deprecated: use schemas/camera-preset.ts instead (#197)' },
          { group: ['**/utils/gpsCoordinates'], message: 'Deprecated: use schemas/coordinates.ts instead (#197)' },
        ],
      }],
    },
  },
  {
    // Test files configuration with Vitest plugin
    files: ['**/__tests__/**/*.{js,jsx,ts,tsx}', '**/*.test.{js,jsx,ts,tsx}', '**/*.spec.{js,jsx,ts,tsx}'],
    plugins: {
      vitest: vitestPlugin,
    },
    rules: {
      ...vitestPlugin.configs.recommended.rules,
      // Tests use `as any` intentionally to test error handling with invalid inputs
      '@typescript-eslint/no-explicit-any': 'off',
    },
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        ...vitestPlugin.environments.env.globals,
      },
    },
  },
])
