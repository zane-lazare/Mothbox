# E2E Testing Guide (Playwright)

End-to-end tests using Playwright run against a real Mothbox Pi server using Firefox browser.

## Quick Start

```bash
cd webui/frontend

# Run all E2E tests
npm run test:e2e

# Run tests with browser visible (headed mode)
npm run test:e2e:headed

# Debug tests interactively
npm run test:e2e:debug

# Use Playwright UI mode for test development
npm run test:e2e:ui

# View test report after running
npm run test:e2e:report

# Run specific test file
npx playwright test smoke.spec.js

# Run tests matching pattern
npx playwright test --grep "Gallery"
```

## Configuration

**File**: `webui/frontend/playwright.config.js`

| Setting | Value | Reason |
|---------|-------|--------|
| Target | `http://mothbox.lazare.nz:5000` | Remote Pi server |
| Browser | Firefox only | User requirement |
| Timeout | 60 seconds | Accounts for network latency |
| Workers | 1 | Sequential execution against single Pi |
| Artifacts | Screenshots, videos, traces | Captured on failure |

## Test Structure

```
webui/frontend/e2e/
├── fixtures/
│   └── test-helpers.js       # Shared utilities (rate limit handling, date formatting)
├── pages/
│   ├── gallery.page.js       # Gallery page object (photo grid, selection mode)
│   ├── lightbox.page.js      # Lightbox page object (navigation, zoom, metadata)
│   ├── filter-drawer.page.js # Filter drawer page object (date, tags, species)
│   └── export.page.js        # Export workflow page object (format, progress)
└── tests/
    ├── smoke.spec.js           # Basic connectivity and API health (5 tests)
    ├── gallery-browsing.spec.js # Gallery loading, scroll, view modes (8 tests)
    ├── lightbox-navigation.spec.js # Photo viewing, navigation (10 tests)
    ├── filter-search.spec.js   # Filter drawer, search (12 tests)
    ├── bulk-operations.spec.js # Selection mode, bulk actions (9 tests)
    └── export-workflow.spec.js # Export job creation, download (6 tests)
```

## Page Object Pattern

Tests use page objects to encapsulate UI interactions:

```javascript
import { GalleryPage } from '../pages/gallery.page.js'

const gallery = new GalleryPage(page)
await gallery.goto()
await gallery.toggleSelectMode()
await gallery.selectPhotos([0, 1, 2])
await gallery.clickBulkExport()
```

## Rate Limiting

The Pi server has a 50 requests/hour limit. Tests automatically skip when rate limited:

```javascript
import { isRateLimited } from '../fixtures/test-helpers.js'

test.beforeEach(async ({ page }) => {
  if (await isRateLimited(page)) {
    test.skip(true, 'Rate limited by server (50/hour)')
  }
})
```

## Adding New Tests

1. Create page object in `e2e/pages/` if needed
2. Use aria-labels and role attributes for selectors (not class names)
3. Add rate limit handling in `beforeEach`
4. Handle "no photos" edge case with `test.skip()`
5. Run `npm run test:e2e:ui` to develop tests interactively

## Important Notes

- Tests run against **real data** on the Pi (not mocked)
- **Bulk delete is SKIPPED** to protect real photos
- Bulk tag tests use unique timestamped tags for cleanup
- Export tests are reversible (files auto-cleanup)

## Related Documentation

- [Gallery Testing](./gallery-testing.md) - Unit and integration tests for gallery
- [Camera Hardware Testing](./camera-hardware-testing.md) - Hardware-specific tests
