# Vitest 4 Test Compatibility Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 174 test failures caused by vitest 4 breaking changes to mock constructors and spy validation.

**Architecture:** Change arrow functions to regular functions in `vi.fn()` mocks used as constructors, and replace `vi.spyOn` on undefined `window.alert` with direct `vi.fn()` assignment.

**Tech Stack:** vitest 4.0.18, happy-dom

---

### Task 1: Fix shared gallery IntersectionObserver mock

**Files:**
- Modify: `webui/frontend/src/pages/__tests__/gallery-test-helpers.jsx:86`

**Step 1: Change arrow function to regular function**

In `gallery-test-helpers.jsx`, line 86, change:

```js
  const IntersectionObserverMock = vi.fn((callback) => {
```

to:

```js
  const IntersectionObserverMock = vi.fn(function (callback) {
```

Only this one line changes. The rest of the function body stays identical.

**Step 2: Run affected Gallery tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/pages/__tests__/Gallery.empty-states.test.jsx src/pages/__tests__/Gallery.filters.test.jsx src/pages/__tests__/Gallery.infinite-scroll.errors.test.jsx src/pages/__tests__/Gallery.infinite-scroll.lightbox.test.jsx src/pages/__tests__/Gallery.infinite-scroll.loading.test.jsx src/pages/__tests__/Gallery.integration.test.jsx src/pages/__tests__/Gallery.search.test.jsx src/pages/__tests__/Gallery.series.test.jsx`

Expected: All pass (these 8 files use the shared helper).

**Step 3: Commit**

```bash
cd /home/zane/projects/Mothbox/Firmware
git add webui/frontend/src/pages/__tests__/gallery-test-helpers.jsx
git commit -m "fix(tests): use regular function in shared IntersectionObserver mock

Vitest 4 requires constructable mocks to use function keyword
instead of arrow functions. Arrow functions cannot be called
with new."
```

---

### Task 2: Fix per-file IntersectionObserver mocks

**Files:**
- Modify: `webui/frontend/src/hooks/__tests__/useInViewport.test.js:11`
- Modify: `webui/frontend/src/hooks/__tests__/useInfiniteScroll.test.js:20`
- Modify: `webui/frontend/src/components/__tests__/LazyImage.integration.test.jsx:11,70`

**Step 1: Fix useInViewport.test.js line 11**

Change:
```js
    global.IntersectionObserver = vi.fn((callback) => {
```
to:
```js
    global.IntersectionObserver = vi.fn(function (callback) {
```

**Step 2: Fix useInfiniteScroll.test.js line 20**

Change:
```js
    IntersectionObserverMock = vi.fn((callback, options) => {
```
to:
```js
    IntersectionObserverMock = vi.fn(function (callback, options) {
```

**Step 3: Fix LazyImage.integration.test.jsx line 11**

Change:
```js
    global.IntersectionObserver = vi.fn((callback) => {
```
to:
```js
    global.IntersectionObserver = vi.fn(function (callback) {
```

**Step 4: Fix LazyImage.integration.test.jsx line 70 (second mock)**

Change:
```js
    global.IntersectionObserver = vi.fn((callback) => {
```
to:
```js
    global.IntersectionObserver = vi.fn(function (callback) {
```

**Step 5: Run affected tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/hooks/__tests__/useInViewport.test.js src/hooks/__tests__/useInfiniteScroll.test.js src/components/__tests__/LazyImage.integration.test.jsx`

Expected: All pass.

**Step 6: Commit**

```bash
cd /home/zane/projects/Mothbox/Firmware
git add webui/frontend/src/hooks/__tests__/useInViewport.test.js webui/frontend/src/hooks/__tests__/useInfiniteScroll.test.js webui/frontend/src/components/__tests__/LazyImage.integration.test.jsx
git commit -m "fix(tests): use regular function in per-file IntersectionObserver mocks

Same vitest 4 constructor fix applied to useInViewport,
useInfiniteScroll, and LazyImage integration tests."
```

---

### Task 3: Fix inline IntersectionObserver mocks + ResizeObserver mock

**Files:**
- Modify: `webui/frontend/src/pages/__tests__/Gallery.bulk-selection.test.jsx:98`
- Modify: `webui/frontend/src/pages/__tests__/Gallery.view-mode.test.jsx:61`
- Modify: `webui/frontend/src/hooks/__tests__/useVirtualGrid.test.js:28`

**Step 1: Fix Gallery.bulk-selection.test.jsx line 98**

Change:
```js
    globalThis.IntersectionObserver = vi.fn(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    }))
```
to:
```js
    globalThis.IntersectionObserver = vi.fn(function () {
      return {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      }
    })
```

Note: arrow returning object literal `() => ({...})` must become `function () { return {...} }`.

**Step 2: Fix Gallery.view-mode.test.jsx line 61**

Same change as Step 1 — identical code pattern:

```js
    globalThis.IntersectionObserver = vi.fn(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    }))
```
to:
```js
    globalThis.IntersectionObserver = vi.fn(function () {
      return {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      }
    })
```

**Step 3: Fix useVirtualGrid.test.js line 28**

Change:
```js
    global.ResizeObserver = vi.fn((callback) => {
```
to:
```js
    global.ResizeObserver = vi.fn(function (callback) {
```

**Step 4: Run affected tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/pages/__tests__/Gallery.bulk-selection.test.jsx src/pages/__tests__/Gallery.view-mode.test.jsx src/hooks/__tests__/useVirtualGrid.test.js`

Expected: All pass.

**Step 5: Commit**

```bash
cd /home/zane/projects/Mothbox/Firmware
git add webui/frontend/src/pages/__tests__/Gallery.bulk-selection.test.jsx webui/frontend/src/pages/__tests__/Gallery.view-mode.test.jsx webui/frontend/src/hooks/__tests__/useVirtualGrid.test.js
git commit -m "fix(tests): use regular function in remaining Observer mocks

Fix IntersectionObserver mocks in Gallery.bulk-selection and
Gallery.view-mode, and ResizeObserver mock in useVirtualGrid."
```

---

### Task 4: Fix window.alert spy in FilterPresetManager

**Files:**
- Modify: `webui/frontend/src/components/filters/__tests__/FilterPresetManager.test.jsx:188,243,453`

**Step 1: Fix line 188**

Change:
```js
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
```
to:
```js
      window.alert = vi.fn()
      const alertSpy = window.alert
```

**Step 2: Fix line 243**

Same change:
```js
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
```
to:
```js
      window.alert = vi.fn()
      const alertSpy = window.alert
```

**Step 3: Fix line 453**

Same change:
```js
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
```
to:
```js
      window.alert = vi.fn()
      const alertSpy = window.alert
```

Also remove the `alertSpy.mockRestore()` calls on lines 196, 262, and 482 since there's no original to restore (happy-dom doesn't define `window.alert`).

**Step 4: Run FilterPresetManager tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/filters/__tests__/FilterPresetManager.test.jsx`

Expected: All pass.

**Step 5: Commit**

```bash
cd /home/zane/projects/Mothbox/Firmware
git add webui/frontend/src/components/filters/__tests__/FilterPresetManager.test.jsx
git commit -m "fix(tests): replace vi.spyOn(window.alert) with vi.fn()

happy-dom doesn't define window.alert, and vitest 4 rejects
spying on undefined properties. Use direct vi.fn() assignment."
```

---

### Task 5: Final verification

**Step 1: Run full test suite**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run`

Expected: 5834 passed, 0 failed (matching vitest 3 baseline).

If any failures remain, investigate — they may be additional vitest 4 breaking changes not yet identified.

**Step 2: Run npm audit**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npm audit --audit-level=high; echo "EXIT: $?"`

Expected: EXIT: 0
