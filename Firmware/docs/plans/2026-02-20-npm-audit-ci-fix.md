# npm audit CI Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve all 10 npm audit vulnerabilities (9 high minimatch ReDoS + 1 moderate ajv ReDoS) so the `frontend-security` CI job passes.

**Architecture:** npm overrides force fixed transitive deps for eslint chain; vitest 3→4 upgrade eliminates the vulnerable test-exclude→minimatch→glob chain entirely.

**Tech Stack:** npm overrides, vitest 4.0.18, eslint 9.39.2 (unchanged)

---

### Task 1: Add npm overrides to package.json

**Files:**
- Modify: `webui/frontend/package.json`

**Step 1: Add overrides section**

In `webui/frontend/package.json`, add an `overrides` key at the top level (after `devDependencies`):

```json
  "overrides": {
    "minimatch": ">=10.2.1",
    "ajv": ">=8.18.0"
  }
```

**Step 2: Bump vitest packages to v4**

In `webui/frontend/package.json`, change these three devDependencies:

```
"@vitest/coverage-v8": "3.2.4"  →  "@vitest/coverage-v8": "^4.0.18"
"@vitest/ui": "3.2.4"           →  "@vitest/ui": "^4.0.18"
"vitest": "3.2.4"               →  "vitest": "^4.0.18"
```

**Step 3: Update test:local script for vitest 4 CLI**

In `webui/frontend/package.json`, change the `test:local` script:

```
"test:local": "vitest run --pool=forks --poolOptions.forks.maxForks=2 --no-file-parallelism"
```
→
```
"test:local": "vitest run --pool=forks --maxWorkers=2 --no-file-parallelism"
```

**Step 4: Install dependencies**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npm install`

This regenerates `package-lock.json` with the overrides and upgraded vitest packages.

**Step 5: Verify npm audit passes**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npm audit`
Expected: `found 0 vulnerabilities`

If any remain, investigate with `npm ls <package>` and adjust overrides.

**Step 6: Commit**

```bash
cd /home/zane/projects/Mothbox/Firmware
git add webui/frontend/package.json webui/frontend/package-lock.json
git commit -m "fix(deps): add npm overrides and upgrade vitest to v4

Add overrides for minimatch>=10.2.1 and ajv>=8.18.0 to fix
9 high + 1 moderate npm audit vulnerabilities in eslint chain.
Upgrade vitest, @vitest/coverage-v8, @vitest/ui from 3.2.4 to 4.0.18
which drops the vulnerable test-exclude dependency entirely."
```

---

### Task 2: Migrate vitest.config.js for vitest 4

**Files:**
- Modify: `webui/frontend/vitest.config.js`

**Step 1: Replace poolOptions with top-level config**

In `webui/frontend/vitest.config.js`, replace the pool configuration block (lines 30-37):

```js
// BEFORE
    pool: 'forks',
    poolOptions: {
      forks: {
        minForks: 1,
        maxForks: process.env.CI ? 1 : 2,  // Single fork in CI for memory safety
        isolate: true,  // Fresh process per test file - prevents memory accumulation
      }
    },
```

```js
// AFTER
    pool: 'forks',
    maxWorkers: process.env.CI ? 1 : 2,  // Single worker in CI for memory safety
    isolate: true,  // Fresh process per test file - prevents memory accumulation
```

`minForks` has no vitest 4 equivalent (removed). `maxForks` → `maxWorkers`. `isolate` moves to top level.

**Step 2: Run vitest to verify config is valid**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: Tests run and pass. No config errors about unknown options.

If vitest warns about deprecated config keys, fix them.

**Step 3: Verify eslint still works with overridden minimatch**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx eslint src/ 2>&1 | tail -10`
Expected: Normal lint output (warnings/errors about code, NOT crashes about minimatch incompatibility).

**Step 4: Verify production build**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds. Overrides and vitest changes are devDependencies only — build should be unaffected.

**Step 5: Commit**

```bash
cd /home/zane/projects/Mothbox/Firmware
git add webui/frontend/vitest.config.js
git commit -m "fix(config): migrate vitest.config.js for vitest 4

Replace removed poolOptions.forks with top-level maxWorkers
and isolate options per vitest 4 migration guide."
```

---

### Task 3: Final verification

**Step 1: Run npm audit one more time**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npm audit --audit-level=high`
Expected: `found 0 vulnerabilities` — matches what CI runs.

**Step 2: Run full test suite**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run`
Expected: All tests pass. Watch for:
- `invocationCallOrder` assertion failures (vitest 4 starts at 1 not 0)
- Mock behavior changes (`getMockName()` returns `vi.fn()` not `spy`)
- Any `poolOptions` deprecation warnings

If tests fail, investigate and fix before proceeding.
