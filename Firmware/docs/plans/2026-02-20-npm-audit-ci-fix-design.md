# Fix npm audit CI failures

## Problem

The `frontend-security` CI job runs `npm audit --audit-level=high` and fails with 10 vulnerabilities (9 high, 1 moderate). All are transitive devDependencies that never ship to production:

- **minimatch < 10.2.1** (9 high — ReDoS via repeated wildcards): pulled by eslint 9.39.2 (`@eslint/config-array`, `@eslint/eslintrc`, direct dep), `@typescript-eslint/typescript-estree`, `test-exclude` (via `@vitest/coverage-v8`), and `glob`
- **ajv < 8.18.0** (1 moderate — ReDoS with `$data` option): pulled by `@eslint/eslintrc` and eslint directly

## Approach

Two changes, applied together:

### 1. npm overrides for eslint chain

Add `overrides` to `package.json` forcing fixed transitive versions:

```json
"overrides": {
  "minimatch": ">=10.2.1"
}
```

eslint stays at 9.39.2 — no config changes. The overrides resolve minimatch vulnerabilities in the eslint chain.

**Note:** ajv override (`>=8.18.0`) was attempted but removed — ajv 6.x and 8.x have incompatible APIs, causing eslint to crash. The moderate-severity ajv vuln cannot be fixed without upgrading to eslint 10 (which drops `@eslint/eslintrc`). CI gates on `--audit-level=high` so this does not block.

### 2. Upgrade vitest 3 to 4

Upgrade `vitest`, `@vitest/coverage-v8`, and `@vitest/ui` from 3.2.4 to 4.0.18. Vitest 4's coverage-v8 drops the `test-exclude` dependency entirely, eliminating the remaining 4 vulnerabilities without overrides.

Vitest 4 breaking changes that affect our config:
- `poolOptions.forks.maxForks` becomes top-level `maxWorkers`
- `poolOptions.forks.minForks` removed (no equivalent)
- `poolOptions.forks.isolate` becomes top-level `isolate`
- `vi.fn().mock.invocationCallOrder` starts at 1 instead of 0

`vitest.config.js` update:

```js
// Before
pool: 'forks',
poolOptions: {
  forks: {
    minForks: 1,
    maxForks: process.env.CI ? 1 : 2,
    isolate: true,
  }
},

// After
pool: 'forks',
maxWorkers: process.env.CI ? 1 : 2,
isolate: true,
```

## Verification

1. `npm ci` — clean install
2. `npm audit --audit-level=high` — exit code 0 (moderate ajv remains but doesn't trigger gate)
3. `npx eslint src/ --max-warnings=0` — eslint works with overridden minimatch
4. `npx vitest run` — all tests pass with vitest 4
5. `npm run build` — production build unaffected

## Files Modified

- `webui/frontend/package.json` — add overrides, bump vitest devDependencies
- `webui/frontend/package-lock.json` — regenerated
- `webui/frontend/vitest.config.js` — poolOptions migration
