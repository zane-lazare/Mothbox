# Gallery Enhancement Timeline - Gantt Chart

This document provides visual timeline representations for the Gallery Enhancement project.

## Overall Project Timeline (20 weeks)

```mermaid
gantt
    title Mothbox Gallery Enhancement - Full Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1
    Thumbnail caching          :p1-1, 2025-01-06, 3d
    Pagination API            :p1-2, 2025-01-06, 2d
    Infinite scroll           :p1-3, after p1-2, 2d
    Grid/List toggle          :p1-4, after p1-3, 2d
    Loading states            :p1-5, after p1-3, 2d
    Performance tests         :p1-6, after p1-5, 2d
    Documentation            :p1-7, after p1-6, 1d
    Deploy & Validate        :milestone, p1-done, after p1-7, 0d

    section Phase 2
    GPS utilities            :p2-1, after p1-done, 2d
    GPS EXIF embedding       :p2-2, after p2-1, 3d
    Metadata parser          :p2-3, after p2-1, 2d
    Metadata API             :p2-4, after p2-3, 2d
    Adaptive lightbox        :p2-5, after p1-done, 3d
    Virtualized gallery      :p2-6, after p2-5, 3d
    Metadata panel           :p2-7, after p2-4 p2-5, 3d
    E2E tests               :p2-8, after p2-7, 2d
    Deploy & Validate       :milestone, p2-done, after p2-8, 0d

    section Phase 3
    Series detection        :p3-1, after p2-done, 2d
    Leaflet map             :p3-2, after p2-done, 3d
    Stacked card UI         :p3-3, after p3-1, 2d
    Location clustering     :p3-4, after p3-2, 2d
    Hover popups            :p3-5, after p3-2 p3-4, 2d
    Map-lightbox integration :p3-6, after p3-5, 2d
    Mobile testing          :p3-7, after p3-6, 2d
    Deploy & Validate       :milestone, p3-done, after p3-7, 0d

    section Phase 4
    JSON sidecar metadata   :p4-1, after p3-done, 3d
    Metadata CRUD API       :p4-2, after p4-1, 2d
    Migration script        :p4-3, after p4-1, 2d
    Tag autocomplete        :p4-4, after p4-2, 2d
    Quick-tag dropdown      :p4-5, after p4-2 p4-4, 3d
    Metadata panel          :p4-6, after p4-2, 3d
    Full-text search        :p4-7, after p4-2, 3d
    Filter drawer           :p4-8, after p4-7, 3d
    Bulk tagging            :p4-9, after p4-5, 3d
    Deploy & Validate       :milestone, p4-done, after p4-9, 0d

    section Phase 5
    Export metadata service :p5-1, after p4-done, 2d
    Deployment manager      :p5-2, after p5-1, 3d
    Export presets          :p5-3, after p4-done, 2d
    Darwin Core exporter    :p5-4, after p5-1 p5-2, 2d
    iNaturalist exporter    :p5-5, after p5-1 p5-2, 2d
    JSON/CSV exporters      :p5-6, after p5-1, 2d
    Export API routes       :p5-7, after p5-4 p5-5 p5-6, 2d
    ZIP optimization        :p5-8, after p5-5 p5-7, 2d
    Export page UI          :p5-9, after p5-7, 3d
    Context menus           :p5-10, after p5-7 p5-9, 2d
    Bulk export toolbar     :p5-11, after p5-10, 2d
    Documentation           :p5-12, after p5-9, 2d
    Deploy & Validate       :milestone, p5-done, after p5-12, 0d
```

## Phase-by-Phase Breakdown

### Phase 1: Performance Foundation (Weeks 1-3)

```mermaid
gantt
    title Phase 1: Performance Foundation
    dateFormat  YYYY-MM-DD

    section Week 1
    Issue #134 Thumbnail caching     :p1-1, 2025-01-06, 3d
    Issue #135 Pagination API        :p1-2, 2025-01-06, 2d

    section Week 2
    Issue #136 Infinite scroll       :p1-3, after p1-2, 2d
    Issue #137 Grid/List toggle      :p1-4, after p1-3, 2d
    Issue #138 Loading states        :p1-5, 2025-01-13, 2d

    section Week 3
    Issue #139 Performance tests     :p1-6, after p1-4 p1-5, 2d
    Issue #140 Documentation         :p1-7, after p1-6, 1d
    Deploy & User Validation        :milestone, after p1-7, 0d
```

**Parallel Work Opportunities**:
- #134 and #135 can both start Week 1 (backend focus)
- #138 can integrate with #136-137 (loading states layer)

---

### Phase 2: Enhanced Photo Viewer & Metadata (Weeks 4-6)

```mermaid
gantt
    title Phase 2: Enhanced Photo Viewer & Metadata
    dateFormat  YYYY-MM-DD

    section Week 4
    Issue #104 GPS utilities         :p2-1, 2025-01-27, 2d
    Issue #98 GPS EXIF embedding     :p2-2, after p2-1, 3d
    Issue #99 Metadata parser        :p2-3, 2025-01-27, 2d

    section Week 5
    Issue #100 Metadata API          :p2-4, after p2-3, 2d
    Issue #101 Adaptive lightbox     :p2-5, 2025-02-03, 3d
    Issue #105 Virtualized gallery   :p2-6, after p2-5, 3d

    section Week 6
    Issue #103 Metadata panel        :p2-7, after p2-4 p2-5, 3d
    Issue #106 E2E tests             :p2-8, after p2-7, 2d
    Deploy & User Validation        :milestone, after p2-8, 0d
```

**Critical Path**: #104 → #98 → #99 → #100 → #103
**Parallel**: #101 and #105 can work independently

---

### Phase 3: Series Grouping & Map View (Weeks 7-9)

```mermaid
gantt
    title Phase 3: Series Grouping & Map View
    dateFormat  YYYY-MM-DD

    section Week 7
    Issue #110 Series detection      :p3-1, 2025-02-17, 2d
    Issue #113 Leaflet map           :p3-2, 2025-02-17, 3d
    Issue #111 Stacked card UI       :p3-3, after p3-1, 2d

    section Week 8
    Issue #115 Location clustering   :p3-4, after p3-2, 2d
    Issue #117 Hover popups          :p3-5, after p3-2 p3-4, 2d
    Issue #119 Map-lightbox integ    :p3-6, after p3-5, 2d

    section Week 9
    Issue #121 Mobile testing        :p3-7, after p3-6, 2d
    Deploy & User Validation        :milestone, after p3-7, 0d
```

**Parallel Work Opportunities**:
- #110 and #113 can both start Week 7 (different tech stacks)

---

### Phase 4: Tagging, Search & Filtering (Weeks 10-13)

```mermaid
gantt
    title Phase 4: Tagging, Search & Filtering
    dateFormat  YYYY-MM-DD

    section Week 10
    Issue #102 JSON sidecar          :p4-1, 2025-03-10, 3d
    Issue #107 Metadata CRUD API     :p4-2, after p4-1, 2d
    Issue #133 Migration script      :p4-3, after p4-1, 2d

    section Week 11
    Issue #124 Tag autocomplete      :p4-4, after p4-2, 2d
    Issue #108 Quick-tag dropdown    :p4-5, after p4-2 p4-4, 3d
    Issue #109 Metadata panel        :p4-6, after p4-2, 3d

    section Week 12
    Issue #131 Full-text search      :p4-7, after p4-2, 3d
    Issue #132 Filter drawer         :p4-8, after p4-7, 3d
    Issue #130 Bulk tagging          :p4-9, after p4-5, 3d

    section Week 13
    Integration Testing             :p4-10, after p4-8 p4-9, 2d
    Deploy & User Validation        :milestone, after p4-10, 0d
```

**Critical Path**: #102 → #107 → everything else depends on this
**Parallel**: After #107, multiple UI components can be built concurrently

---

### Phase 5: Export System (Weeks 14-18)

```mermaid
gantt
    title Phase 5: Export System
    dateFormat  YYYY-MM-DD

    section Week 14
    Issue #112 Export metadata       :p5-1, 2025-04-07, 2d
    Issue #114 Deployment manager    :p5-2, after p5-1, 3d
    Issue #123 Export presets        :p5-3, 2025-04-07, 2d

    section Week 15
    Issue #116 Darwin Core           :p5-4, after p5-1 p5-2, 2d
    Issue #118 iNaturalist           :p5-5, after p5-1 p5-2, 2d
    Issue #120 JSON/CSV exporters    :p5-6, after p5-1, 2d

    section Week 16
    Issue #122 Export API routes     :p5-7, after p5-4 p5-5 p5-6, 2d
    Issue #128 ZIP optimization      :p5-8, after p5-5 p5-7, 2d
    Issue #125 Export page UI        :p5-9, after p5-7, 3d

    section Week 17
    Issue #126 Context menus         :p5-10, after p5-7 p5-9, 2d
    Issue #127 Bulk export toolbar   :p5-11, after p5-10, 2d
    Issue #129 Documentation         :p5-12, after p5-9, 2d

    section Week 18
    Integration Testing             :p5-13, after p5-11 p5-12, 2d
    Deploy & User Validation        :milestone, after p5-13, 0d
```

**Parallel Work Opportunities**:
- #116, #118, #120 (exporters) can all work after #112-114 complete
- #126, #127, #129 can all work in Week 17

---

## Milestone Due Dates

```mermaid
gantt
    title Project Milestones
    dateFormat  YYYY-MM-DD

    Phase 1 Due :milestone, 2025-02-15, 0d
    Phase 2 Due :milestone, 2025-03-01, 0d
    Phase 3 Due :milestone, 2025-03-15, 0d
    Phase 4 Due :milestone, 2025-04-05, 0d
    Phase 5 Due :milestone, 2025-04-30, 0d
```

---

## Critical Path Analysis

The **critical path** (longest dependency chain) through the project:

```
Phase 1: #134 → #135 → #136 → #137 → #139 → #140
Phase 2: #104 → #98/#99 → #100 → #103 → #106
Phase 3: #113 → #115 → #117 → #119 → #121
Phase 4: #102 → #107 → #131 → #132
Phase 5: #112 → #114 → #116 → #122 → #125 → #126 → #127
```

**Total Critical Path Duration**: ~88 days (17.6 weeks)

With full-time capacity (30-40 hours/week) and allowing for:
- User validation after each phase (1-2 days)
- Buffer for unexpected issues (10%)
- Documentation and polish time

**Realistic Timeline**: 18-20 weeks (4.5-5 months)

---

## Resource Allocation (Solo Developer)

### Typical Week Breakdown

```
Monday-Wednesday:     Feature development (20-24 hours)
Thursday:             Testing & bug fixes (8 hours)
Friday:               Code review, documentation, planning (8 hours)
```

### Effort Distribution by Phase

| Phase | Backend | Frontend | Testing | Docs | Total |
|-------|---------|----------|---------|------|-------|
| Phase 1 | 7 days | 4 days | 2 days | 1 day | 14 days |
| Phase 2 | 9 days | 8 days | 2 days | 1 day | 20 days |
| Phase 3 | 6 days | 7 days | 2 days | 0 days | 15 days |
| Phase 4 | 8 days | 11 days | 2 days | 1 day | 22 days |
| Phase 5 | 13 days | 7 days | 2 days | 2 days | 24 days |
| **Total** | **43 days** | **37 days** | **10 days** | **5 days** | **95 days** |

---

## Viewing This Chart

To render these Mermaid diagrams:
1. View this file on GitHub (renders automatically)
2. Use VS Code with Mermaid extension
3. Copy to https://mermaid.live for standalone viewing
4. Use GitHub Project timeline view for interactive planning

---

**Last Updated**: 2025-01-06
**Version**: 1.0
