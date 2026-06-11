# Mothbox Frontend Migration & Consolidation Plan

**Status:** Planning Phase  
**Last Updated:** June 11, 2026  
**Estimated Timeline:** 10-15 weeks  
**Complexity:** Medium-High  

---

## Executive Summary

This comprehensive plan outlines the migration strategy for modernizing the Mothbox React frontend, covering component consolidation, TypeScript migration, UI design system implementation, page decomposition, and architectural reorganization.

### Key Metrics
- **Current State**: 276 component files (198 .jsx, 78 .tsx), ~18,379 LOC
- **TypeScript Adoption**: 28% → Target: 100%
- **Components to Consolidate**: 315+ instances
- **Duplicate Code to Eliminate**: ~2,000 lines
- **Large Pages to Decompose**: Camera (2,329 lines), Settings (2,510 lines)

### Strategic Goals
1. **Consolidation**: Merge Gallery/gallery directories, unify 25 modal patterns
2. **TypeScript**: Complete migration to 100% TypeScript
3. **Design System**: Build 10 core UI primitives to replace 315+ instances
4. **Page Decomposition**: Break monolithic pages into <200 line components
5. **Architecture**: Modern feature-first folder structure

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Quick Wins (Immediate Value)](#quick-wins-immediate-value)
3. [Component Consolidation Strategy](#component-consolidation-strategy)
4. [TypeScript Migration Roadmap](#typescript-migration-roadmap)
5. [UI Design System Implementation](#ui-design-system-implementation)
6. [Page Decomposition Plans](#page-decomposition-plans)
7. [Folder Architecture Migration](#folder-architecture-migration)
8. [Phased Implementation Timeline](#phased-implementation-timeline)
9. [Risk Assessment & Mitigation](#risk-assessment--mitigation)
10. [Success Metrics](#success-metrics)

---

## Current State Analysis

### Component Inventory
```
src/
├── components/              # 145 non-test files
│   ├── Gallery/ (1)         # Case inconsistency issue
│   ├── gallery/ (21)        # Lowercase variant
│   ├── scheduler/ (94)      # Well-organized feature
│   ├── metadata/ (20)       # Well-organized feature
│   ├── export/ (13)         # Well-organized feature
│   ├── filters/ (23)        # Well-organized feature
│   ├── form/ (3)            # Incomplete primitives
│   ├── common/ (1)          # Underutilized
│   └── [24 root files]      # Scattered components
├── pages/ (8)               # Large monolithic files
├── hooks/ (27)              # Mixed feature/shared
├── utils/ (26)              # Mixed feature/shared
├── contexts/ (4)            # Mixed feature/shared
├── constants/ (2)           # Configuration files
└── schemas/ (14)            # Zod validation schemas
```

### Critical Issues Identified

#### 1. Directory Case Inconsistency
- `components/Gallery/` (capitalized) - 1 file
- `components/gallery/` (lowercase) - 21 files
- **Impact**: Import confusion, potential Linux issues

#### 2. Monolithic Page Components
- `Camera.jsx`: **2,329 lines** (20+ useState hooks)
- `Settings.jsx`: **2,510 lines** (multiple form states)
- **Impact**: Hard to maintain, test, and reuse

#### 3. Duplicate Modal Patterns
- 25 modals using `createPortal` individually
- 3 variants of SavePresetModal (duplication)
- **Impact**: 300+ lines of duplicate code

#### 4. Missing UI Primitives
- 70+ inline button patterns
- 90+ form input patterns
- No shared Card/Badge components
- **Impact**: Inconsistent UI, maintenance burden

#### 5. Partial TypeScript Migration
- 23% TypeScript adoption
- 693 PropTypes usages remaining
- **Impact**: Weaker type safety, larger bundle

---

## Quick Wins (Immediate Value)

### Priority 1: Gallery Directory Merge (5 minutes)
**Impact:** Eliminates directory confusion

```bash
# Move GpsTagBanner to lowercase directory
mv src/components/Gallery/GpsTagBanner.jsx src/components/gallery/
rmdir src/components/Gallery

# Update single import in Gallery.jsx
# Line 43: import GpsTagBanner from '../components/gallery/GpsTagBanner'
```

**Risk:** LOW  
**Estimated Time:** 5 minutes  
**Files Changed:** 2 (1 move, 1 import update)

### Priority 2: Remove Duplicate Preset Modal (15 minutes)
**Impact:** Remove dead code

```bash
# Investigate which is actively used:
grep -r "SavePresetModal" src/components/filters/
grep -r "SaveFilterPresetModal" src/components/filters/

# Delete unused variant
# Update remaining imports
```

**Risk:** LOW  
**Estimated Time:** 15 minutes  
**Files Changed:** 3-5 imports

### Priority 3: Create Form Input Components (4 hours)
**Impact:** Eliminates 50+ duplicate input patterns

**New Components:**
- `FormTextInput.tsx`
- `FormTextarea.tsx`
- `FormCheckbox.tsx`
- `FormRadioGroup.tsx`

**Risk:** MEDIUM  
**Estimated Time:** 4 hours  
**Files Changed:** 50+ for migration

---

## Component Consolidation Strategy

### 1. Modal Consolidation (HIGH PRIORITY)

**Current State:**
- 25 modal implementations
- 13 use createPortal
- Duplicate escape handling, backdrop logic

**Proposed Solution:**
```typescript
// Base Modal component
<Modal isOpen={isOpen} onClose={onClose} size="md" title="Save Preset">
  <ModalBody>
    {/* Content */}
  </ModalBody>
  <ModalFooter>
    <Button variant="secondary" onClick={onClose}>Cancel</Button>
    <Button onClick={handleSave}>Save</Button>
  </ModalFooter>
</Modal>
```

**Migration Impact:**
- **Modals to Refactor:** 25
- **Lines Saved:** ~300
- **Estimated Effort:** 20 hours
- **Risk:** Medium

### 2. Loading State Consolidation

**Current Components:**
- `LoadingSpinner.jsx` (already good)
- `PhotoSkeleton.jsx`
- `ThumbnailSkeleton.jsx`
- `MetadataSkeleton.jsx`

**Proposed Unified Component:**
```typescript
<Skeleton variant="photo" />
<Skeleton variant="thumbnail" size={128} />
<Skeleton variant="metadata" rows={6} />
```

**Migration Impact:**
- **Components to Replace:** 4
- **Lines Saved:** ~80
- **Estimated Effort:** 4 hours
- **Risk:** Low

### 3. Chip/Badge Consolidation

**Current Components:**
- `TagChip.jsx` (well-designed, keep as base)
- Internal `FilterChip` in ActiveFilterChips
- Various badge patterns

**Proposed Enhancement:**
```typescript
<Badge variant="primary" shape="pill" onRemove={handleRemove}>
  Tag Name
</Badge>
```

**Migration Impact:**
- **Instances to Replace:** 45+
- **Lines Saved:** ~100
- **Estimated Effort:** 6 hours
- **Risk:** Low

---

## TypeScript Migration Roadmap

### Overview: 4 Phases, 210 Hours (~10-11 weeks)

### Phase 1: Foundation (40 hours)
**Goal:** Create type infrastructure and migrate utilities

**Tasks:**
1. Create `/types` directory with domain types
   ```typescript
   // types/domain.ts
   export interface Photo { path, filename, timestamp, ... }
   export interface PhotoMetadata { camera, iso, aperture, ... }
   export interface GPSData { latitude, longitude, altitude }
   ```

2. Migrate utilities (15 hours)
   - `utils/thumbnailUrl.js` → `.ts`
   - `utils/uuid.js` → `.ts`
   - `utils/helpers.js` → `.ts`
   - `utils/queryKeys.js` → `.ts` ⭐ High impact

3. Migrate constants (8 hours)
   - `constants/config.js` → `.ts` ⭐ Critical for type safety
   - Export typed configuration objects

4. API utilities (12 hours)
   - `utils/metadataFormatters.js` → `.ts`
   - `utils/clusterUtils.js` → `.ts`

**Deliverables:**
- Complete type definitions in `/types`
- 20+ utility files migrated
- Foundation for component migration

### Phase 2: Hooks & Contexts (60 hours)
**Goal:** Migrate data layer for type inference

**Simple Hooks (20 hours):**
- `useSocket.js` → `.ts`
- `usePhotoMetadata.js` → `.ts` (has .d.ts already)
- `useTags.js` → `.ts` (has .d.ts already)
- `useSpecies.js` → `.ts` (has .d.ts already)

**API Modules (15 hours):**
- `utils/api.js` → `.ts` ⭐ Central API client
- `utils/exportApi.js` → `.ts`
- `utils/schedulerApi.js` → `.ts`

**Complex Hooks (15 hours):**
- `useSidecarMetadata.js` → `.ts`
- `useFilters.js` → `.ts`
- `useSchedules.js` → `.ts`

**Contexts (10 hours):**
- `FilterContext.jsx` → `.tsx`
- `SelectionContext.jsx` → `.tsx`
- `SocketContext.jsx` → `.tsx`

### Phase 3: Components (80 hours)
**Goal:** Migrate all remaining components

**Priority Order:**
1. Simple components (20h): ViewModeToggle, PhotoSkeleton, ErrorBoundary
2. Metadata components (10h): Remaining .jsx files
3. Export components (12h): ExportJobList, FormatSelector
4. Filter components (15h): FilterDrawer, DateRangeFilter
5. Gallery components (13h): SearchBar, BulkActionsToolbar
6. Scheduler components (10h): Remaining .jsx calendar/timeline files

### Phase 4: Pages & Cleanup (30 hours)
**Goal:** Complete migration, remove PropTypes

**Pages (20 hours):**
- `Gallery.jsx` → `.tsx` (1,033 lines)
- `Camera.jsx` → `.tsx` (2,329 lines)
- `Settings.jsx` → `.tsx` (2,510 lines)

**Complex Components (10 hours):**
- `PhotoLightbox.jsx` → `.tsx` (852 lines)
- `VirtualPhotoGrid.jsx` → `.tsx`
- `MapView.jsx` → `.tsx`

**Cleanup:**
- Remove 693 PropTypes usages
- Remove `prop-types` dependency

---

## UI Design System Implementation

### Core Components to Build

#### 1. Button Component (70+ instances)
```typescript
<Button variant="primary" size="md" isLoading={saving}>
  Save Changes
</Button>

// Variants: primary, secondary, success, danger, ghost, link
// Sizes: xs, sm, md, lg
```

**Usage:** 70+ instances across 40+ files  
**Effort:** 8 hours (build + migrate)

#### 2. Modal Component (25+ instances)
```typescript
<Modal isOpen={isOpen} onClose={onClose} size="lg" title="Bulk Tag Photos">
  <ModalBody>
    {/* Form content */}
  </ModalBody>
  <ModalFooter>
    <Button variant="secondary" onClick={onClose}>Cancel</Button>
    <Button onClick={handleSubmit}>Apply Tags</Button>
  </ModalFooter>
</Modal>
```

**Usage:** 25 modal implementations  
**Effort:** 12 hours (build + migrate)

#### 3. Form Components (90+ instances)
```typescript
<Input type="text" error={errors.name} placeholder="Enter name" />
<Textarea rows={4} error={errors.description} />
<Checkbox label="Enable GPS tagging" helperText="..." />
<Radio label="Option 1" description="..." />
```

**Usage:** 90+ scattered input patterns  
**Effort:** 16 hours (build + migrate)

#### 4. Card Component (45+ instances)
```typescript
<Card variant="elevated" padding="lg">
  <CardHeader>
    <CardTitle>Photo Details</CardTitle>
    <CardDescription>Capture metadata</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

**Usage:** 45+ card patterns  
**Effort:** 8 hours (build + migrate)

#### 5. Badge Component (45+ instances)
```typescript
<Badge variant="success" shape="pill" count={5} onRemove={handleRemove}>
  Wildlife
</Badge>
```

**Usage:** 45+ badge/chip instances  
**Effort:** 6 hours (build + migrate)

### Design Tokens
```typescript
// colors.ts - Extracted from 52+ files using blue-600, green-600, etc.
// spacing.ts - Standardized spacing scale
// typography.ts - Font sizes, weights
// shadows.ts - Shadow levels for elevation
// borderRadius.ts - Consistent corner radii
```

### Implementation Timeline
- **Week 1-2**: Foundation (Button, Modal, Input)
- **Week 3**: Form components (Checkbox, Radio, Textarea)
- **Week 4**: Containers (Card, Alert, Badge)
- **Week 5-8**: Migration (315+ instances)

---

## Page Decomposition Plans

### Camera.jsx (2,329 lines → ~150 lines)

#### Current Structure Issues
- 20+ useState hooks in single component
- Mixed concerns: state, WebSocket, UI, business logic
- Difficult to test individual features

#### Proposed Breakdown

**Custom Hooks (5 hooks):**
1. `useCamera.js` (~120 lines) - Camera state & control
2. `useCameraPresets.js` (~150 lines) - Preset management
3. `useLiveControls.js` (~180 lines) - Real-time controls
4. `useSocketCamera.js` (~100 lines) - WebSocket events
5. `useCoordinateTransform.js` (~80 lines) - Viewport transforms

**UI Components (9 components):**
1. `CameraPreview.jsx` (~150 lines) - Live view display
2. `MetadataOverlay.jsx` (~100 lines) - Metadata display
3. `LiveControlsOverlay.jsx` (~350 lines) - Control sliders
4. `QuickActionsOverlay.jsx` (~120 lines) - Action buttons
5. `SettingsTransferOverlay.jsx` (~60 lines) - Copy settings
6. `TestCaptureOverlay.jsx` (~90 lines) - Test capture
7. `CaptureControlOverlay.jsx` (~70 lines) - Main capture
8. `ConnectionStatus.jsx` (~30 lines) - Status indicator
9. `LiveViewInfo.jsx` (~50 lines) - Stream info

**Result:** Camera.jsx reduced to ~150 lines of composition

**Effort:** 44-54 hours  
**Risk:** Medium (complex state management)

### Settings.jsx (2,510 lines → ~120 lines)

#### Current Structure Issues
- Multiple form states (controls, camera, webui)
- Complex preset initialization logic
- 5 tabs with deeply nested cards

#### Proposed Breakdown

**Custom Hooks (6 hooks):**
1. `useSettingsTabs.js` - Tab state
2. `useCollapsibleCards.js` - Card expand/collapse
3. `useSettingsForms.js` (~150 lines) - Form state + dirty tracking
4. `usePhotoPresets.js` (~180 lines) - Photo presets
5. `useLiveViewPresets.js` (~180 lines) - Live view presets
6. `useFocusStrategy.js` (~100 lines) - Unified focus mode

**Tab Components (5 tabs + 22 cards):**
1. `SystemInfoTab.jsx` (2 cards)
2. `DiagnosticTab.jsx` (3 cards)
3. `HardwareControlsTab.jsx` (1 form)
4. `CameraSettingsTab.jsx` (7 cards)
5. `LiveViewSettingsTab.jsx` (8 cards)

**Result:** Settings.jsx reduced to ~120 lines of tab switching

**Effort:** 60 hours  
**Risk:** Medium-High (complex form sync)

---

## Folder Architecture Migration

### Proposed Structure: Feature-First with UI Layer

```
src/
├── features/                    # Feature modules
│   ├── gallery/
│   │   ├── components/
│   │   │   ├── grid/           # PhotoGridItem, VirtualPhotoGrid
│   │   │   ├── list/           # PhotoListItem
│   │   │   ├── lightbox/       # PhotoLightbox
│   │   │   ├── search/         # SearchBar, AdvancedSearch
│   │   │   ├── selection/      # BulkActions, BulkModals
│   │   │   └── tags/           # TagChip, QuickTag
│   │   ├── hooks/
│   │   ├── contexts/
│   │   ├── utils/
│   │   └── index.ts            # Public API
│   ├── map/
│   ├── filters/
│   ├── export/
│   ├── metadata/
│   ├── scheduler/
│   ├── camera/
│   └── image/                  # LazyImage, ProgressiveImage
│
├── ui/                         # Shared UI library
│   ├── buttons/
│   ├── feedback/               # LoadingSpinner, ErrorBoundary
│   ├── layout/                 # Card, CollapsibleCard
│   ├── forms/                  # Input, Checkbox, FormField
│   ├── dialogs/                # Modal, ConfirmDialog
│   └── index.ts
│
├── shared/                     # Cross-cutting
│   ├── hooks/                  # useInfiniteScroll
│   ├── contexts/               # SocketContext
│   └── utils/                  # api.js, helpers.js
│
├── config/                     # Constants
├── schemas/                    # Zod schemas by feature
├── pages/                      # Route components
└── types/                      # Global TypeScript types
```

### Migration Strategy: Incremental (4-6 weeks) ⭐ RECOMMENDED

**Week 1-2:** Create structure, move UI components  
**Week 3:** Migrate small features (camera, deployment)  
**Week 4:** Migrate medium features (export, metadata)  
**Week 5:** Migrate large features (gallery, filters, scheduler)  
**Week 6:** Migrate map, shared utils, cleanup

**Benefits:**
- ✅ Lower risk than big bang
- ✅ Continuous testing
- ✅ Allows parallel work
- ✅ Easy to rollback individual features

---

## Phased Implementation Timeline

### Overall Timeline: 10-15 Weeks

### Phase 1: Quick Wins & Foundation (Week 1-2)
**Goals:** Immediate improvements, setup infrastructure

**Tasks:**
- [ ] Merge Gallery/gallery directories (5 min)
- [ ] Remove duplicate SavePresetModal (15 min)
- [ ] Create `/types` directory structure
- [ ] Migrate utilities to TypeScript (15h)
- [ ] Create design system tokens (4h)
- [ ] Build Button component (4h)
- [ ] Build Modal component (4h)

**Deliverables:**
- Directory consolidation complete
- Type definitions created
- 2 core UI components ready
- 20+ utilities migrated to TypeScript

**Estimated Effort:** 40 hours

### Phase 2: UI Design System (Week 3-4)
**Goals:** Build core UI primitives library

**Tasks:**
- [ ] Build Input, Textarea components (6h)
- [ ] Build Checkbox, Radio components (6h)
- [ ] Build Card, Alert components (6h)
- [ ] Build Badge component (3h)
- [ ] Enhance LoadingSpinner (2h)
- [ ] Migrate 50 button instances (8h)
- [ ] Migrate 25 modal instances (12h)
- [ ] Create Storybook setup (8h)

**Deliverables:**
- 10 reusable UI components
- 100+ instances migrated
- Component documentation

**Estimated Effort:** 50 hours

### Phase 3: TypeScript Migration - Data Layer (Week 5-6)
**Goals:** Migrate hooks, contexts, API layer

**Tasks:**
- [ ] Migrate simple hooks (20h)
- [ ] Migrate API modules (15h)
- [ ] Migrate complex hooks (15h)
- [ ] Migrate contexts (10h)
- [ ] Update component imports for typed hooks

**Deliverables:**
- 50+ hooks migrated
- All contexts typed
- API layer fully typed

**Estimated Effort:** 60 hours

### Phase 4: Page Decomposition (Week 7-8)
**Goals:** Break down monolithic pages

**Tasks:**
- [ ] Decompose Camera.jsx (44-54h)
  - Extract 5 hooks
  - Create 9 UI components
  - Refactor page to composition
- [ ] Decompose Settings.jsx (60h)
  - Extract 6 hooks
  - Create 5 tab components + 22 cards
  - Refactor page to tab switcher

**Deliverables:**
- Camera.jsx: 2,329 → ~150 lines
- Settings.jsx: 2,510 → ~120 lines
- 15 new testable hooks
- 36 new focused components

**Estimated Effort:** 100-114 hours

### Phase 5: Component TypeScript Migration (Week 9-11)
**Goals:** Complete component migration

**Tasks:**
- [ ] Migrate simple components (20h)
- [ ] Migrate metadata components (10h)
- [ ] Migrate export components (12h)
- [ ] Migrate filter components (15h)
- [ ] Migrate gallery components (13h)
- [ ] Migrate scheduler components (10h)

**Deliverables:**
- 100+ components migrated
- PropTypes removed
- Type coverage: 100%

**Estimated Effort:** 80 hours

### Phase 6: Folder Architecture Migration (Week 12-13)
**Goals:** Reorganize to feature-first structure

**Tasks:**
- [ ] Create feature directories
- [ ] Move gallery feature (8h)
- [ ] Move map feature (4h)
- [ ] Move filters feature (4h)
- [ ] Move export feature (4h)
- [ ] Move metadata feature (4h)
- [ ] Move scheduler feature (6h)
- [ ] Create barrel exports (4h)
- [ ] Update all imports (16h)
- [ ] Clean up old structure (4h)

**Deliverables:**
- Modern folder structure
- Clear feature boundaries
- Public API pattern

**Estimated Effort:** 54 hours

### Phase 7: Final Migration & Cleanup (Week 14-15)
**Goals:** Complete pages, final cleanup

**Tasks:**
- [ ] Migrate Gallery.jsx to TypeScript (6h)
- [ ] Migrate Camera.jsx to TypeScript (6h)
- [ ] Migrate Settings.jsx to TypeScript (6h)
- [ ] Migrate complex components (10h)
- [ ] Remove all PropTypes (4h)
- [ ] Update documentation (8h)
- [ ] Full regression testing (16h)
- [ ] Performance benchmarks (4h)

**Deliverables:**
- 100% TypeScript codebase
- All pages migrated
- Complete documentation
- Performance validated

**Estimated Effort:** 60 hours

---

## Risk Assessment & Mitigation

### High-Risk Areas

#### 1. Large Page Refactoring (Camera, Settings)
**Risk:** Breaking functionality during decomposition

**Mitigation:**
- Extract hooks before components
- Comprehensive unit tests for each hook
- Manual testing after each extraction
- Feature flags for gradual rollout
- Keep original files until fully validated

#### 2. Import Path Updates (540+ files)
**Risk:** Missing imports, broken builds

**Mitigation:**
- Use automated find/replace scripts
- TypeScript compiler catches errors
- Incremental migration by feature
- Run full test suite after each batch
- Keep old paths working during transition

#### 3. Modal Consolidation (25 instances)
**Risk:** Subtle behavior differences breaking UX

**Mitigation:**
- Start with simple modals (ConfirmDialog)
- Visual regression tests (Playwright snapshots)
- User acceptance testing
- Preserve existing behavior exactly

### Medium-Risk Areas

#### 1. TypeScript Complex State (Contexts, Reducers)
**Risk:** Type errors in complex state management

**Mitigation:**
- Use discriminated unions for actions
- Reference existing TypeScript patterns (SchedulerContext)
- Extensive type testing
- Gradual strictness increase

#### 2. Barrel Export Performance
**Risk:** Bundle size increase from barrel imports

**Mitigation:**
- Feature-scoped barrels (not monolithic)
- Monitor bundle size with vite-bundle-visualizer
- Tree-shaking validation
- Lazy load features by route

### Low-Risk Areas

- Utility function migration (pure functions)
- Simple component migration (presentational)
- Constants migration (no runtime logic)
- Directory reorganization (structural only)

---

## Success Metrics

### Code Quality
- ✅ TypeScript Coverage: 28% → 100%
- ✅ Component Count: 276 → ~200 (after consolidation)
- ✅ Average Component Size: 300 lines → <200 lines
- ✅ Duplicate Code: Baseline → <5%
- ✅ Test Coverage: 85% → 90%+

### Architecture
- ✅ Feature Module Count: 8-10 well-defined features
- ✅ UI Component Library: 10+ reusable primitives
- ✅ Import Path Clarity: Feature paths clear (`@/features/gallery`)
- ✅ Barrel Export Usage: 90%+ of cross-module imports

### Performance
- ✅ Bundle Size: Monitor, target <5% increase
- ✅ Build Time: Baseline → <10% increase
- ✅ Hot Module Replacement: <200ms (maintain)
- ✅ Gallery Page Load: <1s (maintain)

### Developer Experience
- ✅ Time to Create Component: 50% faster with design system
- ✅ Type Safety: 100% (no `any` types)
- ✅ IDE Autocomplete: Full IntelliSense support
- ✅ Test Writing Speed: 30% faster with typed hooks

---

## Implementation Guidelines

### For Each Phase

**Before Starting:**
1. Create feature branch: `feat/frontend-migration-phaseN`
2. Review phase goals and tasks
3. Set up tracking (GitHub project board)

**During Implementation:**
1. Follow TDD for hooks and utilities
2. Update imports incrementally
3. Run tests after each significant change
4. Visual QA in browser for UI changes
5. Document decisions in code comments

**After Completion:**
1. Full test suite run
2. Visual regression testing
3. Performance benchmarks
4. Code review
5. Merge to main branch
6. Update this document with actuals

### Code Standards

**TypeScript:**
- Strict mode enabled
- Explicit return types for functions
- No `any` types without justification
- Interface over type for objects

**Components:**
- One component per file
- Co-located tests
- Props interface at top
- Barrel exports for public API

**Testing:**
- Unit tests for hooks and utilities
- Integration tests for complex components
- E2E tests for critical workflows
- 90%+ coverage target

---

## Next Steps

### Immediate Actions (This Week)
1. ✅ Review this plan with team
2. ⬜ Choose migration approach (recommend Incremental)
3. ⬜ Set up project tracking board
4. ⬜ Execute Quick Wins (5-20 minutes each)
5. ⬜ Create Phase 1 branch

### Week 1 Goals
- Complete Quick Wins
- Set up `/types` directory
- Migrate first 10 utilities to TypeScript
- Build Button and Modal components
- Update team on progress

### How to Use This Document
- **Project Managers**: Track phases, estimate timelines
- **Developers**: Follow implementation guidelines per phase
- **Reviewers**: Use metrics to validate progress
- **Stakeholders**: Monitor success metrics

---

## Appendix

### Related Documents
- `CLAUDE.md` - Project overview and development guidelines
- `Firmware/webui/frontend/README.md` - Frontend setup and testing
- `TESTING_PROCEDURE.md` - Manual testing procedures

### Tools & Dependencies
- `class-variance-authority` - Component variant management
- `clsx` + `tailwind-merge` - Classname utilities
- `@playwright/test` - Visual regression testing
- `vite-bundle-visualizer` - Bundle analysis

### Key Files for Reference
- `src/components/scheduler/` - Example of well-organized feature
- `src/components/filters/index.js` - Barrel export pattern
- `src/components/form/FormField.tsx` - TypeScript component pattern
- `src/schemas/scheduler/interval.ts` - Zod schema pattern

---

**Last Updated:** June 11, 2026  
**Maintainers:** Development Team  
**Status:** Ready for Implementation
