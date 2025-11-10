# GitHub Project #2 Views - Setup Guide

This guide walks you through creating custom views for your Gallery Enhancement project board.

**Project URL**: https://github.com/users/zane-lazare/projects/2

---

## Why Custom Views?

Default project view shows all 43 issues in one list - overwhelming! Custom views help you:
- Focus on current phase
- See timeline visually
- Filter by testing tasks
- Track your active work

---

## Setup Steps (5 minutes)

### Step 1: Open Your Project

1. Go to: https://github.com/users/zane-lazare/projects/2
2. You should see all 43 issues in the default view

---

### Step 2: Create "By Phase" View

**Purpose**: Group issues by milestone to see phase-by-phase organization

1. Click **"+ New view"** (top right, next to view tabs)
2. Click **"New board view"**
3. Name it: `By Phase`
4. Click the **"⋮"** menu (three dots) in the toolbar
5. Select **"Group by"** → **"Milestone"**

**Result**: You'll see 5 columns (one per phase) with issues grouped accordingly.

**Optional Enhancement**:
- Click "⋮" → "Sort by" → "Labels" (to group by type within each phase)

---

### Step 3: Create "Timeline" View

**Purpose**: Gantt-style timeline showing when each issue is scheduled

1. Click **"+ New view"**
2. Click **"New roadmap view"**
3. Name it: `Timeline`
4. The roadmap will automatically show issues with milestone due dates

**Configuration**:
- Zoom: Click the zoom controls to show "Months" view
- Coloring: Issues automatically colored by milestone

**Result**: Visual Gantt chart showing all 43 issues across 5 months (Jan-May 2025).

---

### Step 4: Create "My Work" View

**Purpose**: Focus on issues you're currently working on

1. Click **"+ New view"**
2. Click **"New board view"**
3. Name it: `My Work`
4. Click **Filter** icon (funnel) in toolbar
5. Add filter: Type `assignee:@me` and press Enter
6. Add another filter: `status:"Todo,In Progress"` and press Enter
7. Click **"⋮"** → **"Group by"** → **"Status"**

**Result**: Board with just your assigned issues, grouped by status (Todo → In Progress → Done).

---

### Step 5: Create "Testing" View

**Purpose**: Track all testing-related issues

1. Click **"+ New view"**
2. Click **"New table view"**
3. Name it: `Testing`
4. Click **Filter** icon
5. Add filter: `label:testing`
6. In table view, click **"+"** to add columns:
   - Milestone
   - Labels
   - Status

**Result**: Table showing all testing issues with key metadata.

---

### Step 6: Create "Phase 1 Focus" View

**Purpose**: Laser focus on just the 7 Phase 1 issues

1. Click **"+ New view"**
2. Click **"New board view"**
3. Name it: `Phase 1 Focus`
4. Click **Filter** icon
5. Add filter: `milestone:"Phase 1: Performance Foundation"`
6. Click **"⋮"** → **"Group by"** → **"Status"**

**Result**: Kanban board with ONLY Phase 1 issues (Todo → In Progress → Done).

---

## Optional: Add Custom Fields

Custom fields enhance tracking but are not required to start.

### Priority Field

**Use**: Sort issues by importance within each phase

1. Click **"⋮"** (project menu, top right)
2. Select **"Settings"**
3. Scroll to **"Custom fields"** section
4. Click **"+ New field"**
5. Configuration:
   - Name: `Priority`
   - Type: **Single select**
   - Options:
     - `🔴 Critical` (red)
     - `🟠 High` (orange)
     - `🟡 Medium` (yellow)
     - `🟢 Low` (green)
6. Click **"Save"**

**Then**: Assign priority to each issue by clicking the issue and selecting priority.

### Effort Field

**Use**: Track estimated days for each issue

1. Settings → Custom fields → **"+ New field"**
2. Configuration:
   - Name: `Effort (days)`
   - Type: **Number**
3. Click **"Save"**

**Then**: Add effort estimates from the roadmap (e.g., Issue #134 = 3 days).

### Test Coverage % Field

**Use**: Track coverage progress as issues are developed

1. Settings → Custom fields → **"+ New field"**
2. Configuration:
   - Name: `Test Coverage %`
   - Type: **Number**
3. Click **"Save"**

**Then**: Update as you run `pytest --cov` for each issue.

---

## View Navigation Tips

### Switching Views
- Click view tabs at top (By Phase | Timeline | My Work | Testing | Phase 1 Focus)
- Each view saves its filters/grouping automatically

### Updating Issues
- Drag issues between Status columns (Todo → In Progress → Done)
- Changes sync across all views instantly

### Filtering Further
- Use the Filter icon in any view to add temporary filters
- Example: In "By Phase" view, add `label:backend` to see only backend issues

### Keyboard Shortcuts
- `C` - Create new issue
- `/` - Focus search/filter
- `Ctrl+K` (or `Cmd+K` on Mac) - Command palette

---

## Recommended Daily Workflow

### Morning Routine
1. Open **"My Work"** view
2. Check what's in "In Progress"
3. Move completed tasks to "Done"
4. Pull next task from "Todo" to "In Progress"

### Weekly Review (Friday)
1. Open **"Timeline"** view
2. Check if current week's tasks are complete
3. Open **"By Phase"** view
4. Check milestone progress % (shown at top of each column)
5. Plan next week's priorities

### Phase Transition (every 3 weeks)
1. Open **"Phase X Focus"** view
2. Verify all issues marked "Done"
3. Run deployment checklist from roadmap
4. User validation testing
5. Switch to next phase's focus view

---

## Troubleshooting

### "I don't see any issues in my view"
- Check filters - click Filter icon and remove any filters
- Verify issues are added to project (should be 43 total)
- Refresh page (Ctrl+R / Cmd+R)

### "Can't create Roadmap view"
- Roadmap requires at least one issue with a milestone due date
- All 43 issues should have milestones (check at https://github.com/zane-lazare/Mothbox/milestones)

### "Views aren't saving"
- Make sure you click the view tab after creating it
- Project auto-saves changes - no manual save needed
- If issues persist, clear browser cache

---

## Example: Using Views for Phase 1

**Day 1** (Starting Phase 1):
1. Open **"Phase 1 Focus"** view
2. Assign yourself to Issue #134 (Thumbnail caching)
3. Drag #134 to "In Progress" column
4. Start TDD workflow (see docs/TDD_WORKFLOW.md)

**Day 3** (Completed #134):
1. Open **"Phase 1 Focus"** view
2. Drag #134 to "Done" column
3. Drag #135 (Pagination API) to "In Progress"
4. Continue development

**Week 3** (Phase 1 Complete):
1. Open **"Phase 1 Focus"** view
2. Verify all 7 issues in "Done" column
3. Check milestone shows 100% complete
4. Open **"Timeline"** view
5. Verify Phase 1 milestone marked complete
6. Deploy and validate (see roadmap)

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ GitHub Project #2 - Views Cheat Sheet                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ By Phase        → Group by milestone, see all phases    │
│ Timeline        → Gantt chart, see schedule             │
│ My Work         → Your assigned tasks only              │
│ Testing         → All testing-related issues            │
│ Phase 1 Focus   → Current sprint (7 issues)             │
│                                                          │
│ Shortcuts:                                              │
│   C            → Create new issue                       │
│   /            → Filter                                 │
│   Ctrl/Cmd+K   → Command palette                        │
│                                                          │
│ Daily:         → Use "My Work" view                     │
│ Weekly:        → Use "Timeline" + "By Phase" views      │
│ Sprint Focus:  → Use "Phase X Focus" views              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. ✅ Set up these 5 views (takes ~5 minutes)
2. ✅ (Optional) Add custom fields (Priority, Effort)
3. ✅ Start with **"Phase 1 Focus"** view
4. ✅ Assign yourself to Issue #134
5. 🚀 Begin development!

---

**Questions?** Open an issue or check the main roadmap: `GALLERY_ROADMAP.md`

**Last Updated**: 2025-01-06
