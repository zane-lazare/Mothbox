# Gallery Enhancement Development Roadmap

**Project**: Mothbox Photo Gallery Enhancement
**Timeline**: Phased deployment over 5 months
**Developer**: Solo developer (full-time, 30-40 hours/week)
**Methodology**: TDD strict, deploy and validate after each phase
**GitHub Project**: [Photo Gallery Enhancement #2](https://github.com/users/zane-lazare/projects/2)

---

## Executive Summary

This roadmap guides the development of a research-grade photo gallery for the Mothbox insect camera trap system. The enhancement is divided into 5 phases, each deployable independently with user validation checkpoints.

**Key Metrics**:
- 43 issues across 5 phases
- ~88-98 development days estimated effort
- With full-time capacity: ~17-20 calendar weeks
- 85%+ test coverage requirement throughout

---

## Timeline Overview

```
Phase 1: Weeks 1-3   (Performance Foundation)
Phase 2: Weeks 4-6   (Photo Viewer & Metadata)
Phase 3: Weeks 7-9   (Series Grouping & Map View)
Phase 4: Weeks 10-13 (Tagging, Search & Filtering)
Phase 5: Weeks 14-18 (Export System)
```

**Deployment Schedule**:
- Week 3: Deploy Phase 1 → User validation
- Week 6: Deploy Phase 2 → User validation
- Week 9: Deploy Phase 3 → User validation
- Week 13: Deploy Phase 4 → User validation
- Week 18: Deploy Phase 5 → Final validation

---

## Phase 1: Performance Foundation (Weeks 1-3)

**Goal**: Fast, scalable gallery with caching and pagination
**Milestone**: [Phase 1: Performance Foundation](https://github.com/zane-lazare/Mothbox/milestone/1)
**Estimated Effort**: 13-14 days

### Issues & Dependencies

```
Week 1:
├─ #134: Thumbnail caching service (3 days) ✓ Start here
└─ #135: Pagination API (2 days) ✓ Parallel with #134

Week 2:
├─ #136: Infinite scroll (2 days) ← Requires #135
├─ #137: Grid/List toggle (2 days) ← Requires #136
└─ #138: Loading states (2 days) ← Can integrate with #136-137

Week 3:
├─ #139: Performance tests (2 days) ← Requires #134-138 complete
└─ #140: Documentation (1 day) ← Requires #134-139 complete
```

### Success Criteria
- [ ] Gallery loads in <2s with 500 photos (cold cache)
- [ ] Thumbnail cache hit rate >80% after warmup
- [ ] Mobile lightbox loads in <1s
- [ ] All unit tests pass with ≥85% coverage
- [ ] Performance benchmarks documented

### Deployment Checklist
- [ ] Run `pytest Tests/integration/test_gallery_performance.py`
- [ ] Benchmark on real Pi 4/5 hardware
- [ ] Deploy to test instance
- [ ] User validation: test with 200+ photos
- [ ] Tag release: `v5.1.0-phase1`

### TDD Workflow Reference
- **Backend service tests**: See `Tests/unit/test_tuning_loader.py` (mocking pattern)
- **API route tests**: See `Tests/unit/test_gallery_routes.py` (existing gallery tests)
- **React component tests**: See `webui/frontend/src/components/__tests__/` (Jest + RTL)

---

## Phase 2: Enhanced Photo Viewer & Metadata (Weeks 4-6)

**Goal**: Rich photo viewer with GPS and camera metadata
**Milestone**: [Phase 2: Enhanced Photo Viewer & Metadata](https://github.com/zane-lazare/Mothbox/milestone/2)
**Estimated Effort**: 15-20 days

### Issues & Dependencies

```
Week 4:
├─ #104: GPS utilities (2 days) ✓ COMPLETE (Python + TypeScript, 153 tests, 87-99% coverage)
├─ #98: GPS EXIF embedding (3 days) ← Requires #104 ✓
└─ #99: Metadata parser (2 days) ← Parallel with #98

Week 5:
├─ #100: Metadata API (2 days) ← Requires #99
├─ #101: Adaptive lightbox (3 days) ← Requires Phase 1 lightbox
└─ #105: Virtualized gallery (3 days) ← Parallel with #101

Week 6:
├─ #103: Metadata panel (3 days) ← Requires #100, #101 ✓ COMPLETE
├─ #106: E2E tests (2 days) ← Requires #98-105 complete
└─ Deploy & validate
```

### Phase 2 Progress Summary
- ✅ **#104**: GPS coordinate utilities (Python + TypeScript implementations)
  - 70 Python tests (87% coverage), 83 TypeScript tests (99% coverage)
  - All conversions <1ms (performance target met)
  - Comprehensive documentation: `docs/GPS_COORDINATE_UTILITIES.md`
- ✅ **#103**: Metadata panel component (React + TypeScript)
  - Error boundary, retry mechanism, timestamp parsing
  - Fully tested with Jest + React Testing Library
- 🔄 **#98**: GPS EXIF embedding (refactored to use #104 utilities)
  - Eliminates code duplication
  - 208 tests passing (no regression)

### Success Criteria
- [ ] GPS EXIF embedded in all new photos (validate with exiftool)
- [ ] Metadata parser handles all EXIF fields correctly
- [ ] Lightbox works perfectly on mobile and desktop
- [ ] Zoom/pan responsive and smooth (60 FPS)
- [ ] E2E tests cover full viewer workflow

### Deployment Checklist
- [ ] Capture test photos with GPS enabled
- [ ] Verify EXIF tags with: `exiftool photo.jpg | grep GPS`
- [ ] Test lightbox on mobile device (real Pi touchscreen)
- [ ] User validation: metadata accuracy and UX
- [ ] Tag release: `v5.2.0-phase2`

### Key Integration Points
- **GPS EXIF**: Post-processing script adds GPS to photos after capture, preserves firmware integrity (see [Issue #98 Implementation Spec](https://github.com/zane-lazare/Mothbox/issues/98#issuecomment-3513641316))
- **Metadata API**: New Flask blueprint `routes/metadata.py`
- **Lightbox**: Enhance existing `webui/frontend/src/pages/Gallery.jsx`

---

## Phase 3: Series Grouping & Map View (Weeks 7-9)

**Goal**: Organized view of HDR/FB series and deployment locations
**Milestone**: [Phase 3: Series Grouping & Map View](https://github.com/zane-lazare/Mothbox/milestone/3)
**Estimated Effort**: 14-15 days

### Issues & Dependencies

```
Week 7:
├─ #110: Series detection (2 days) ✓ Start here
├─ #113: Leaflet map infrastructure (3 days) ✓ Parallel with #110
└─ #111: Stacked card UI (2 days) ← Requires #110

Week 8:
├─ #115: Location clustering (2 days) ← Requires #113
├─ #117: Hover popups (2 days) ← Requires #113, #115
└─ #119: Map-lightbox integration (2 days) ← Requires #117

Week 9:
├─ #121: Mobile testing & optimization (2 days) ← Requires all above
└─ Deploy & validate
```

### Success Criteria
- [ ] Series detection >95% accuracy for HDR and FB patterns
- [ ] Map clusters locations within 10m tolerance
- [ ] Hover popups load thumbnails in <500ms
- [ ] Map works perfectly on mobile (touch gestures)
- [ ] Lighthouse mobile score >85

### Deployment Checklist
- [ ] Test with real HDR photo series
- [ ] Verify haversine clustering accuracy
- [ ] Test map on tablet/phone (touch interactions)
- [ ] User validation: map usability and series grouping
- [ ] Tag release: `v5.3.0-phase3`

### Dependencies to Add
```bash
# Frontend
cd webui/frontend
npm install leaflet react-leaflet
```

---

## Phase 4: Tagging, Search & Filtering (Weeks 10-13)

**Goal**: Full tagging system and powerful search/filter
**Milestone**: [Phase 4: Tagging, Search & Filtering](https://github.com/zane-lazare/Mothbox/milestone/4)
**Estimated Effort**: 19-22 days

### Issues & Dependencies

```
Week 10:
├─ #102: JSON sidecar metadata (3 days) ✓ Start here (foundational)
├─ #107: Metadata CRUD API (2 days) ← Requires #102
└─ #133: Migration script (2 days) ← Requires #102

Week 11:
├─ #124: Tag autocomplete (2 days) ← Requires #107
├─ #108: Quick-tag dropdown (3 days) ← Requires #107, #124
└─ #109: Metadata panel (3 days) ← Requires #107

Week 12:
├─ #131: Full-text search (3 days) ← Requires #107
├─ #132: Filter drawer (3 days) ← Requires #131
└─ #130: Bulk tagging (3 days) ← Requires #108

Week 13:
└─ Integration testing & deploy
```

### Success Criteria
- [ ] Tagging workflow <30s per photo
- [ ] Search returns results in <500ms (10,000+ photos)
- [ ] Filter combinations work correctly
- [ ] Autocomplete provides relevant suggestions
- [ ] Migration script handles existing photo libraries

### Deployment Checklist
- [ ] Run migration script on test data: `python migrate_metadata.py --dry-run`
- [ ] Test concurrent tagging (simulate multiple browser tabs)
- [ ] Benchmark search performance with 1000+ photos
- [ ] User validation: tagging UX and search accuracy
- [ ] Tag release: `v5.4.0-phase4`

### Critical Implementation Notes
- **File locking**: Use `fcntl.flock()` for .meta.json writes
- **Search engine**: SQLite FTS5 for full-text search (<200ms target)
- **Tag autocomplete**: Implement frequency ranking + fuzzy matching

---

## Phase 5: Export System (Weeks 14-18)

**Goal**: Complete export functionality for all formats
**Milestone**: [Phase 5: Export System](https://github.com/zane-lazare/Mothbox/milestone/5)
**Estimated Effort**: 24 days

### Issues & Dependencies

```
Week 14:
├─ #112: Export metadata service (2 days) ✓ Start here
├─ #114: Deployment manager (3 days) ← Requires #112
└─ #123: Export presets (2 days) ← Parallel

Week 15:
├─ #116: Darwin Core exporter (2 days) ← Requires #112, #114
├─ #118: iNaturalist exporter (2 days) ← Requires #112, #114
└─ #120: JSON/CSV exporters (2 days) ← Requires #112

Week 16:
├─ #122: Export API routes (2 days) ← Requires #116-120
├─ #128: ZIP optimization (2 days) ← Requires #118, #122
└─ #125: Export page UI (3 days) ← Requires #122

Week 17:
├─ #126: Context menus (2 days) ← Requires #122, #125
├─ #127: Bulk export toolbar (2 days) ← Requires #126
└─ #129: Documentation (2 days) ← Parallel

Week 18:
└─ Final integration testing & deploy
```

### Success Criteria
- [ ] Export workflow requires <5 clicks
- [ ] ZIP generation <5s for 50 photos
- [ ] Darwin Core CSV validates against GBIF schema
- [ ] iNaturalist exports include proper XMP tags
- [ ] Export presets save/load correctly
- [ ] Documentation complete (user guide + developer guide)

### Deployment Checklist
- [ ] Validate Darwin Core CSV with GBIF validator
- [ ] Test iNaturalist upload workflow (upload test export to iNat)
- [ ] Benchmark ZIP generation: 50 photos <5s, 100 photos <15s
- [ ] User validation: complete export workflow
- [ ] Tag release: `v5.5.0-complete`

### Export Format Validation
```bash
# Test Darwin Core export
python -c "import pandas as pd; df = pd.read_csv('export.csv'); print(df.columns)"

# Test iNaturalist XMP
unzip inaturalist_export.zip
ls -la *.xmp
```

---

## TDD Workflow Guide

### Overview
All development follows **strict TDD**: write tests first, then implement features. This ensures 85%+ coverage and catches issues early.

### Test-First Workflow (Standard Pattern)

```bash
# 1. Create test file FIRST
touch Tests/unit/test_feature.py

# 2. Write failing tests
# See reference patterns below

# 3. Run tests (they should fail)
pytest Tests/unit/test_feature.py -v

# 4. Implement feature to make tests pass
# Edit source file

# 5. Run tests again (they should pass)
pytest Tests/unit/test_feature.py -v

# 6. Refactor with confidence
# Tests guard against regressions

# 7. Check coverage
pytest Tests/unit/test_feature.py --cov=module --cov-report=html
```

### Reference Test Patterns (Existing Codebase)

**Backend Service with Mocking**:
- Pattern: `Tests/unit/test_tuning_loader.py`
- Use cases: Services that interact with hardware, filesystem, or external APIs
- Key techniques: `monkeypatch`, `tmp_path`, mocking Picamera2

**Flask API Routes**:
- Pattern: `Tests/unit/test_gallery_routes.py`
- Use cases: REST API endpoints with Flask test client
- Key techniques: CSRF token handling, path traversal tests, fixture photos

**Frontend React Components**:
- Pattern: `webui/frontend/src/components/__tests__/`
- Use cases: UI components with user interactions
- Key techniques: Jest, React Testing Library, user-event, mock API calls

**Integration Tests**:
- Pattern: `Tests/integration/test_autofocus_workflows.py`
- Use cases: Multi-component workflows, real hardware
- Key techniques: Subprocess spawning, real file I/O, cleanup fixtures

### Test Organization

```
Tests/
├── unit/               # Fast, isolated tests (mock dependencies)
│   ├── test_thumbnail_cache.py
│   ├── test_metadata_parser.py
│   └── test_tag_autocomplete.py
├── integration/        # Slower tests with real components
│   ├── test_export_workflow.py
│   └── test_gallery_pagination.py
└── performance/        # Benchmark tests (not counted in coverage)
    └── test_export_performance.py
```

### Coverage Requirements
- **Overall**: ≥85% (enforced in CI)
- **Critical paths**: ≥95% (export, GPS, caching)
- **UI components**: ≥75% (focus on logic, not styling)

### Running Tests

```bash
# Unit tests only (fast, can run without hardware)
pytest Tests/unit/ -v

# Integration tests (requires Pi hardware)
pytest Tests/integration/ -v -s

# Specific test file
pytest Tests/unit/test_feature.py -v

# With coverage report
pytest Tests/ --cov=webui/backend --cov-report=html
open htmlcov/index.html

# Performance benchmarks
pytest Tests/performance/ -v --benchmark-only
```

---

## Development Environment Setup

### Prerequisites
```bash
# Backend dependencies (already in requirements.txt)
pip install -r requirements.txt

# Frontend dependencies
cd webui/frontend
npm install
```

### Running Dev Servers

```bash
# Terminal 1: Backend (Flask API)
cd webui/backend
export MOTHBOX_ENV=development
python app.py
# Runs on http://localhost:5000

# Terminal 2: Frontend (React dev server)
cd webui/frontend
npm run dev
# Runs on http://localhost:5173
```

### Code Quality Checks

```bash
# Linting (auto-fix)
ruff check --fix .
ruff format .

# Security scan (MEDIUM+ severity enforced)
bandit -c pyproject.toml -r . --severity-level medium

# Type checking (optional, not enforced yet)
mypy webui/backend
```

---

## Deployment Process

### After Each Phase

1. **Run Full Test Suite**
   ```bash
   pytest Tests/ -v --cov=webui/backend --cov=mothbox_paths --cov-report=html
   coverage report --fail-under=85
   ```

2. **Security Scan**
   ```bash
   bandit -c pyproject.toml -r . --severity-level medium
   ```

3. **Build Frontend**
   ```bash
   cd webui/frontend
   npm run build
   ```

4. **Git Tag Release**
   ```bash
   git tag -a v5.X.0-phaseX -m "Phase X: Feature Name"
   git push origin v5.X.0-phaseX
   ```

5. **Deploy to Test Instance**
   ```bash
   # Follow install_mothbox.sh process
   ./install_mothbox.sh --type production --with-webui
   ```

6. **User Validation**
   - Test on real Pi hardware
   - Verify all acceptance criteria met
   - Document any issues or UX feedback
   - Adjust in next sprint if needed

---

## Parallel Work Opportunities

While this roadmap assumes solo development, some issues can be worked concurrently:

### Phase 1
- Issues #134 and #135 can start together (backend cache + API)
- Issue #138 can integrate alongside #136-137 (loading states)

### Phase 2
- Issues #98, #99, #104 can all start week 4 (backend focus)
- Issues #101 and #105 can run parallel week 5 (frontend focus)

### Phase 3
- Issues #110 and #113 can start together (backend + frontend)

### Phase 4
- Issues #108, #109, #124 can work together once #107 is done

### Phase 5
- Issues #116-120 (exporters) can all start once #112-114 are done
- Issues #126-127 (UI) can work together once #125 is done

**Strategy**: If you find yourself blocked on one issue (e.g., waiting for feedback), pivot to a parallel issue to maintain momentum.

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Performance on Pi hardware slower than expected | Issue #139 catches this early in Phase 1; adjust quality settings if needed |
| GPS EXIF embedding complex | Issue #104 utilities separate complexity; comprehensive tests validate |
| Map view performance issues | Issue #115 clustering reduces marker count; #121 mobile optimization |
| Search performance with 10,000+ photos | Issue #131 uses SQLite FTS5 (proven fast); benchmark tests validate |
| ZIP generation too slow | Issue #128 explicitly optimizes this; <5s target for 50 photos |

### Schedule Risks

| Risk | Mitigation |
|------|------------|
| Issue takes longer than estimated | Full-time capacity provides buffer; can extend phase by 1-2 weeks |
| Blocked by unfamiliar technology (Leaflet, etc.) | Allow extra research time week 7; documentation linked in issues |
| Test coverage below 85% | Strict TDD prevents this; coverage checked before every deploy |
| User validation reveals major UX issues | Each phase deploys independently; can iterate without blocking next phase |

---

## Success Metrics & KPIs

### Phase 1
- [ ] Gallery load time: <2s with 500 photos
- [ ] Cache hit rate: >80%
- [ ] Test coverage: ≥85%

### Phase 2
- [ ] GPS EXIF: 100% of new photos have coordinates
- [ ] Lightbox performance: 60 FPS zoom/pan
- [ ] Mobile responsive: Works on phones/tablets

### Phase 3
- [ ] Series detection: >95% accuracy
- [ ] Map clustering: Correct within 10m
- [ ] Lighthouse mobile: >85 score

### Phase 4
- [ ] Tagging workflow: <30s per photo
- [ ] Search speed: <500ms for 10,000 photos
- [ ] Migration: Handles 10,000 photos in <60s

### Phase 5
- [ ] Export workflow: <5 clicks end-to-end
- [ ] ZIP generation: 50 photos <5s
- [ ] Format validation: GBIF and iNat accept exports

---

## Resources & References

### Documentation
- **Main README**: `README.md`
- **CLAUDE.md**: Project overview and architecture
- **TESTING_PROCEDURE.md**: Manual hardware testing procedures
- **This Roadmap**: Current plan and progress tracking

### Key Codebase Files
- **Path resolution**: `mothbox_paths.py` (all path handling)
- **Configuration**: `controls.txt`, `camera_settings.csv`
- **Photo capture**: `4.x/TakePhoto.py`, `5.x/TakePhoto.py`
- **Gallery backend**: `webui/backend/routes/gallery.py`
- **Gallery frontend**: `webui/frontend/src/pages/Gallery.jsx`

### External Resources
- **Darwin Core**: https://dwc.tdwg.org/terms/
- **GBIF**: https://www.gbif.org/developer/occurrence
- **iNaturalist**: https://www.inaturalist.org/pages/developers
- **Leaflet.js**: https://leafletjs.com/reference.html
- **React Testing Library**: https://testing-library.com/docs/react-testing-library/intro/

---

## Progress Tracking

Track progress in [GitHub Project #2](https://github.com/users/zane-lazare/projects/2).

### Project Views (configured)
- **By Phase**: Group issues by milestone
- **Timeline**: Gantt-style view with due dates
- **My Work**: Issues assigned to you, sorted by priority
- **Testing**: Filter for issues with testing label

### Updating Progress
1. Move issues across board columns: Todo → In Progress → Done
2. Check off acceptance criteria in issue description
3. Link PRs to issues with "Closes #123" in commit message
4. Update milestone progress (auto-calculated from closed issues)

### Weekly Review (Recommended)
Every Friday:
1. Review week's completed issues
2. Update next week's priorities
3. Check milestone progress %
4. Note any blockers or risks
5. Adjust timeline if needed

---

## Contact & Support

- **GitHub Issues**: Use issue comments for questions
- **Project Board**: Track progress and blockers
- **Testing Help**: Reference `TESTING_PROCEDURE.md`
- **Architecture Questions**: Reference `CLAUDE.md`

---

**Last Updated**: 2025-01-06
**Version**: 1.0
**Status**: Ready for Phase 1 kickoff
