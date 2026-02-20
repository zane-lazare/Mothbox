# Fix vitest 4 test failures

## Problem

The vitest 3→4 upgrade introduced 174 test failures across 15 files. All pass on vitest 3 (5834/5834). Two vitest 4 breaking changes are the root cause:

1. **Arrow functions not constructable**: `vi.fn((callback) => {...})` can no longer be called with `new`. Vitest 4 requires `function` keyword for constructable mocks.
2. **Stricter `vi.spyOn`**: `vi.spyOn(window, 'alert')` fails because `happy-dom` doesn't define `window.alert`, and vitest 4 rejects spying on undefined properties.

## Approach

Minimal in-place fixes — change arrow functions to regular functions, replace `vi.spyOn` on undefined properties with direct `vi.fn()` assignment.

### IntersectionObserver mocks (171 failures, 14 files)

Change `vi.fn((callback) => {...})` → `vi.fn(function (callback) {...})` in 7 locations:

1. **Shared helper** `gallery-test-helpers.jsx` — fixes 7 Gallery test files at once
2. **Per-file mocks** in `useInViewport.test.js`, `useInfiniteScroll.test.js`, `LazyImage.integration.test.jsx`, `Gallery.bulk-selection.test.jsx`, `Gallery.view-mode.test.jsx`

### ResizeObserver mock (14 failures, 1 file)

Same arrow → function fix in `useVirtualGrid.test.js`.

### window.alert spy (3 failures, 1 file)

Replace `vi.spyOn(window, 'alert').mockImplementation(() => {})` with `window.alert = vi.fn()` in `FilterPresetManager.test.jsx` (3 locations). happy-dom doesn't define `window.alert`, so there's nothing to spy on — direct assignment is correct.

## Files Modified

| File | Change |
|------|--------|
| `src/pages/__tests__/gallery-test-helpers.jsx` | arrow → function in `setupIntersectionObserver` |
| `src/hooks/__tests__/useInViewport.test.js` | arrow → function |
| `src/hooks/__tests__/useInfiniteScroll.test.js` | arrow → function |
| `src/hooks/__tests__/useVirtualGrid.test.js` | arrow → function (ResizeObserver) |
| `src/components/__tests__/LazyImage.integration.test.jsx` | arrow → function |
| `src/pages/__tests__/Gallery.bulk-selection.test.jsx` | arrow → function |
| `src/pages/__tests__/Gallery.view-mode.test.jsx` | arrow → function |
| `src/components/filters/__tests__/FilterPresetManager.test.jsx` | vi.spyOn → vi.fn() assignment |

## Verification

`npx vitest run` — 5834 passed, 0 failed (matching vitest 3 baseline).
