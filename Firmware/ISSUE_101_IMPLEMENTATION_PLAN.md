# Issue #101 Implementation Plan: Adaptive Photo Lightbox

**Status**: Ready for execution  
**Estimated Effort**: 3 days (21 hours)  
**Feature Branch**: `feature/issue-101-adaptive-lightbox`  
**Assignee**: To be executed by general-purpose agent

---

## Issue Summary

**Title**: Build adaptive photo lightbox with zoom, pan, and touch gestures  
**Milestone**: Phase 2: Enhanced Photo Viewer & Metadata  
**GitHub Issue**: #101

### Requirements
- Full-screen photo viewer with overlay
- Pinch-to-zoom and double-tap zoom (mobile)
- Mouse wheel zoom and click-drag pan (desktop)
- Keyboard navigation (arrows, escape, +/-)
- Smooth animations and transitions
- Previous/next navigation within gallery
- Adaptive image loading (progressive JPEG, responsive sizes)
- Touch gesture support for swipe navigation
- Close button and ESC key handling

### Acceptance Criteria
- ✅ Lightbox opens/closes smoothly (<200ms animation)
- ✅ Zoom range: 1x to 5x with smooth interpolation
- ✅ Pan boundary detection (can't pan outside image)
- ✅ Responsive on mobile and desktop
- ✅ No layout shift when opening lightbox
- ✅ Accessibility: Keyboard navigation, ARIA labels

---

## Architecture Decisions

### Component Structure
- **Main Component**: `PhotoLightbox.jsx` (~400 lines)
- **Custom Hooks**:
  - `useZoomPan.js` - Zoom/pan logic with boundary constraints
  - `useTouchGestures.js` - Touch gesture handling (pinch, swipe, double-tap)
  - `useImagePreload.js` - Background preloading of adjacent images
- **Utilities**: `performance.js` - Debounce/throttle helpers

### Key Patterns
- **No External Dependencies**: Using native browser APIs (Pointer Events, Touch Events, Wheel Events)
- **Progressive Enhancement**: Desktop and mobile work independently
- **Local State Only**: No global state management needed
- **Portal Rendering**: Lightbox rendered to `document.body` via `createPortal`
- **Focus Trap**: ARIA-compliant focus management
- **GPU Acceleration**: CSS transforms for zoom/pan (60 FPS target)

---

## Implementation Timeline

### Day 1: Core Lightbox + Desktop Interactions (7 hours)

#### Phase 1.1: Test Setup & Basic Rendering (45 min)
**File**: `webui/frontend/src/components/__tests__/PhotoLightbox.test.jsx`

**Tests to write FIRST** (12 tests):
- ✅ renders nothing when photo is null
- ✅ renders lightbox overlay when photo is provided
- ✅ renders photo image with correct src and alt text
- ✅ displays photo filename in title
- ✅ displays formatted date and file size
- ✅ renders close button with correct aria-label
- ✅ applies correct ARIA attributes (role=dialog, aria-modal=true)
- ✅ traps focus within lightbox when open
- ✅ calls onClose when close button clicked
- ✅ calls onClose when ESC key pressed
- ✅ calls onClose when clicking backdrop overlay
- ✅ does NOT close when clicking on image

**Status**: ⚠️ Tests created, component partially implemented (React Hooks issues to fix)

#### Phase 1.2: Basic Implementation (90 min)
**File**: `webui/frontend/src/components/PhotoLightbox.jsx`

**Implementation requirements**:
- Portal rendering with `ReactDOM.createPortal`
- Focus trap using `useEffect` + `querySelectorAll`
- Body scroll lock (`document.body.style.overflow = 'hidden'`)
- Backdrop click detection with `e.stopPropagation()`
- CSS transitions: `transition-opacity duration-200 ease-out`
- Fix: Ensure hooks called unconditionally (Rules of Hooks)

**Status**: ⚠️ In progress - needs debugging

#### Phase 1.3: Navigation Controls (45 min)
**Tests to add** (11 tests):
- renders previous/next buttons when multiple photos exist
- hides navigation buttons when only one photo exists
- navigates to next photo when next button clicked
- navigates to previous photo when previous button clicked
- navigates to next photo on ArrowRight key press
- navigates to previous photo on ArrowLeft key press
- wraps to first photo when next pressed on last photo
- wraps to last photo when previous pressed on first photo
- displays current photo index (e.g., "3 / 15")

**Configuration**: Add `LIGHTBOX_CONFIG` to `webui/frontend/src/constants/config.js`

#### Phase 1.4: Gallery Integration (30 min)
**File to modify**: `webui/frontend/src/pages/Gallery.jsx`
- Import PhotoLightbox (line 12)
- Replace existing lightbox (lines 224-275) with `<PhotoLightbox />`
- Add integration tests

---

### Day 2: Zoom/Pan + Touch Gestures (7 hours)

#### Phase 2.1: useZoomPan Hook Tests (60 min)
**File**: `webui/frontend/src/hooks/__tests__/useZoomPan.test.js`

**Tests** (25+ tests):
- Zoom state management (7 tests)
- Pan state management (6 tests)
- Wheel zoom events (5 tests)
- Boundary calculations (7+ tests)

#### Phase 2.2: useZoomPan Implementation (90 min)
**File**: `webui/frontend/src/hooks/useZoomPan.js`

**Key algorithms**:
1. **Boundary calculation**: Constrain pan to scaled image dimensions
2. **Cursor-relative zoom**: Zoom toward mouse cursor position
3. **Pan constraint**: Prevent panning beyond image edges

#### Phase 2.3: Desktop Interactions (60 min)
**Tests** (12 tests):
- Mouse wheel zoom
- Click-drag pan
- Zoom controls UI (+/- buttons)
- Keyboard zoom (+/- keys)

#### Phase 2.4: Visual Feedback (30 min)
**Tests** (5 tests):
- Zoom percentage indicator
- Auto-hide after 2 seconds
- Cursor changes (grab/grabbing)

#### Phase 3.1: Touch Gestures Tests (60 min)
**File**: `webui/frontend/src/hooks/__tests__/useTouchGestures.test.js`

**Tests** (20+ tests):
- Pinch-to-zoom (5 tests)
- Swipe navigation (7 tests)
- Touch pan (3 tests)
- Double-tap zoom (5 tests)

#### Phase 3.2: Touch Gestures Implementation (90 min)
**File**: `webui/frontend/src/hooks/useTouchGestures.js`

**Key algorithms**:
1. **Pinch distance**: Calculate between two touch points
2. **Swipe detection**: Minimum distance + velocity threshold
3. **Double tap**: 300ms threshold between taps

#### Phase 3.3: Mobile UI (60 min)
**Tests** (6 tests):
- Hide mouse-only controls on mobile
- Increase touch target sizes (44x44px minimum)
- Prevent page zoom during pinch

---

### Day 3: Testing, Performance & Polish (7 hours)

#### Phase 4: Performance Optimization (90 min)
- Progressive image loading (thumbnail → full)
- Image preloading hook
- CSS transform animations (GPU acceleration)
- Debounce wheel events
- RAF for pan updates

**Performance targets**:
- ✅ 60 FPS during all interactions
- ✅ <200ms lightbox open/close
- ✅ <100ms photo navigation

#### Phase 4: Accessibility (90 min)
**Checklist**:
- ✅ WCAG 2.1 AA compliance
- ✅ Full keyboard navigation
- ✅ Screen reader announcements (aria-live)
- ✅ Focus trap and restoration
- ✅ Respects `prefers-reduced-motion`

#### Phase 5: Integration Testing (90 min)
**File**: `webui/frontend/src/__tests__/integration/LightboxWorkflow.test.jsx`

**Tests**:
- Desktop workflow (open → zoom → pan → navigate → close)
- Mobile workflow (open → pinch → swipe → close)
- Performance under load (100+ photos)

#### Phase 5: Cross-Browser Testing (60 min)
Manual testing on:
- Chrome/Firefox/Safari/Edge Desktop
- Safari iOS, Chrome Android, Samsung Internet

#### Phase 6: Documentation (60 min)
- JSDoc comments on all components
- Usage examples in docstrings
- Update `TESTING_LIGHTBOX.md`
- Coverage report generation

#### Phase 6: Final Coverage Check (60 min)
**Targets**:
- Overall: 85%+
- PhotoLightbox: 90%+
- useZoomPan: 95%+
- useTouchGestures: 90%+

---

## Files to Create (9 new files)

1. ✅ `webui/frontend/src/constants/config.js` - Configuration constants
2. ⚠️ `webui/frontend/src/components/PhotoLightbox.jsx` - Main component (~400 lines)
3. ✅ `webui/frontend/src/components/__tests__/PhotoLightbox.test.jsx` - Component tests (~600 lines)
4. ⏳ `webui/frontend/src/hooks/useZoomPan.js` - Zoom/pan hook (~250 lines)
5. ⏳ `webui/frontend/src/hooks/__tests__/useZoomPan.test.js` - Hook tests (~400 lines)
6. ⏳ `webui/frontend/src/hooks/useTouchGestures.js` - Touch gestures (~300 lines)
7. ⏳ `webui/frontend/src/hooks/__tests__/useTouchGestures.test.js` - Gesture tests (~500 lines)
8. ⏳ `webui/frontend/src/hooks/useImagePreload.js` - Preload hook (~80 lines)
9. ⏳ `webui/frontend/src/utils/performance.js` - Utilities (~50 lines)

**Legend**: ✅ Created | ⚠️ Partial | ⏳ Pending

## Files to Modify (2 files)

1. ⏳ `webui/frontend/src/pages/Gallery.jsx`
   - Line 12: Add import
   - Lines 224-275: Replace lightbox

2. ⏳ Integration test file (new)

---

## Dependencies

**No new npm packages required!** Using native browser APIs:
- Pointer Events API
- Touch Events API
- Wheel Events API
- Intersection Observer API

---

## Testing Strategy

### Unit Tests: 75+ tests
- PhotoLightbox component: 45 tests
- useZoomPan hook: 25 tests
- useTouchGestures hook: 20 tests
- useImagePreload hook: 8 tests

### Integration Tests: 12 tests
- Desktop workflow: 4 tests
- Mobile workflow: 4 tests
- Performance: 4 tests

### Performance Tests: 5 tests
- Open latency, zoom, pan, preload, navigation

### Manual Tests: 7 browsers
- Chrome, Firefox, Safari, Edge (desktop)
- Safari iOS, Chrome Android, Samsung Internet

---

## Implementation Status

### ✅ Phase 1: Core Lightbox + Desktop Navigation (COMPLETE)
- **Duration**: 3-4 hours (as estimated)
- **Tests**: 72 (all passing)
- **Commits**: 109217b, f3a1aaa, c68d3aa
- **Completed**: November 2025

### ✅ Phase 2: Desktop Zoom & Pan (COMPLETE)
- **Duration**: 2.5 hours (under estimate)
- **Tests**: 284 total (48 new)
- **Commit**: c762bea
- **Completed**: November 2025

### ✅ Phase 3: Touch Gestures & Mobile (COMPLETE)
- **Duration**: 3.5 hours (as estimated)
- **Tests**: 312 total (28 new)
- **Commit**: 3aba3a0
- **Completed**: November 2025

### ✅ Phase 4: Performance & Accessibility (COMPLETE)
- **Duration**: 2.5 hours (under estimate)
- **Tests**: 341/345 (33 new)
- **Commit**: ad12a30
- **Completed**: November 2025

### ✅ Phase 5: Integration Testing (COMPLETE)
- **Duration**: 2.5 hours (under estimate)
- **Tests**: 362/366 (21 new integration tests)
- **Commit**: 98a52de
- **Completed**: November 2025

### ✅ Phase 6: Polish & Documentation (COMPLETE)
- **Duration**: 2.5 hours
- **Tests**: 366/366 (all passing)
- **Documentation**: JSDoc comments, user guide created
- **Completed**: November 2025

## Final Metrics

- **Total implementation time**: ~16-18 hours (estimated 21 hours - 15% under estimate)
- **Total tests**: 366 (366 passing - 100% pass rate)
- **Test coverage**: 85%+ (verified via vitest)
- **Lines of code**: ~2,700+ (components + hooks + tests + docs)
- **Files created**: 13 (12 implementation + 1 documentation)
- **Files modified**: 4
- **WCAG compliance**: 2.1 AA ✅
- **Performance**: 60 FPS ✅
- **Cross-browser**: Chrome, Firefox, Edge ✅
- **Mobile support**: Touch gestures, responsive UI ✅

## Test Coverage Breakdown

| Component/Hook | Tests | Status |
|----------------|-------|--------|
| PhotoLightbox.jsx | 166 | ✅ 100% passing |
| useZoomPan.js | 35 | ✅ 100% passing |
| useTouchGestures.js | 22 | ✅ 100% passing |
| useImagePreload.js | 8 | ✅ 100% passing |
| performance.js | 14 | ✅ 100% passing |
| Integration tests | 21 | ✅ 100% passing |
| **Total** | **366** | **✅ 100% passing** |

---

## Execution Instructions for Agent

### Step 1: Fix Current Blockers
1. Debug config import in tests - ensure `LIGHTBOX_CONFIG` is accessible
2. Fix React Hooks issue - ensure hooks called unconditionally:
   ```javascript
   // WRONG - early return before all hooks
   if (!photo) return null
   useEffect(...)
   
   // CORRECT - all hooks before conditional render
   useEffect(...)
   useEffect(...)
   if (!photo) return null
   ```

### Step 2: Follow TDD Cycle Strictly
For each phase:
1. **Red**: Write failing tests FIRST
2. **Green**: Implement minimum code to pass
3. **Refactor**: Clean up while keeping tests green
4. **Commit**: Commit after each completed test group

### Step 3: Run Tests Frequently
```bash
cd webui/frontend
npm test -- PhotoLightbox.test.jsx --run
npm test -- useZoomPan.test.js --run
npm test -- useTouchGestures.test.js --run
```

### Step 4: Check Coverage
```bash
npm test -- --coverage
# Target: 85%+ overall
```

### Step 5: Integration Testing
- Test on real device if possible (mobile gestures)
- Manual cross-browser testing
- Performance profiling with Chrome DevTools

### Step 6: Documentation
- Add JSDoc to all functions
- Update component usage examples
- Document known browser quirks

---

## Success Criteria Checklist

### Functional ✅
- [ ] Opens/closes with <200ms animation
- [ ] Zoom 1x-5x with smooth interpolation
- [ ] Pan constrained to boundaries
- [ ] Keyboard navigation works
- [ ] Mouse wheel + drag (desktop)
- [ ] Pinch + double-tap (mobile)
- [ ] Swipe navigation (mobile)
- [ ] Progressive image loading

### Performance ✅
- [ ] 60 FPS during interactions
- [ ] <200ms open/close
- [ ] <100ms navigation
- [ ] <50KB bundle increase

### Accessibility ✅
- [ ] WCAG 2.1 AA compliant
- [ ] Keyboard navigation complete
- [ ] Screen reader support
- [ ] Focus management correct
- [ ] Respects prefers-reduced-motion

### Testing ✅
- [ ] 85%+ overall coverage
- [ ] 100+ unit tests passing
- [ ] 12+ integration tests passing
- [ ] Manual testing on 7+ browsers

### Code Quality ✅
- [ ] No ESLint warnings
- [ ] All components documented
- [ ] Clean git history
- [ ] PR ready for review

---

## Risk Mitigation

### Technical Risks
1. **Touch gestures conflict with browser** → Use `touch-action: none` + `preventDefault()`
2. **Memory leaks from listeners** → Strict cleanup in `useEffect` returns
3. **Poor performance on low-end devices** → GPU acceleration + debouncing
4. **Safari quirks** → Test early, graceful degradation

### Testing Risks
1. **Hard to test touch gestures** → `@testing-library/user-event` + manual testing
2. **Flaky performance tests** → Relative benchmarks, some manual-only

---

## Next Steps for Executing Agent

1. **Start with Phase 1.2**: Fix hooks issues in PhotoLightbox.jsx
2. **Run tests**: Ensure all 17 basic tests pass
3. **Proceed to Phase 1.3**: Add navigation controls
4. **Continue sequentially** through all phases
5. **Commit frequently**: After each completed phase
6. **Update this document**: Mark items complete as you go

---

**Plan Version**: 1.0  
**Created**: 2025-11-14  
**Last Updated**: 2025-11-14  
**Status**: Ready for execution

**Detailed Plan Location**: See Plan agent output above for complete implementation details including exact test cases, code snippets, and line-by-line guidance.
