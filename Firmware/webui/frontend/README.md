# Mothbox Web UI - Frontend

Modern React-based web interface for the Mothbox automated insect photography system. Provides real-time camera control, photo gallery management, GPIO control, and system monitoring.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Getting Started](#getting-started)
4. [Project Structure](#project-structure)
5. [Available Scripts](#available-scripts)
6. [Development Workflow](#development-workflow)
7. [Building for Production](#building-for-production)
8. [Testing](#testing)
9. [Code Style](#code-style)
10. [Key Features](#key-features)
11. [API Integration](#api-integration)
12. [Documentation](#documentation)
13. [Contributing](#contributing)
14. [Troubleshooting](#troubleshooting)

---

## Project Overview

The Mothbox Web UI frontend is a single-page application (SPA) built with React 18 that provides comprehensive control and monitoring of the Mothbox hardware system. It communicates with a Flask backend API to manage camera operations, view captured photos, control GPIO relays, and monitor system status.

**Key Capabilities:**
- Real-time camera preview with adjustable settings (exposure, focus, white balance)
- Infinite-scroll photo gallery with grid/list views
- GPIO relay control for attract lights, flash, and UV lights
- Cron-based scheduler management
- System diagnostics and power monitoring
- Camera preset system for quick setting changes
- Progressive image loading for optimal performance

**Target Devices:**
- Raspberry Pi 4/5 with touchscreen (primary use case)
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Mobile devices (phones, tablets)

---

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.1.1 | Component-based UI library |
| **Vite** | 7.1.7 | Fast build tool with HMR |
| **Tailwind CSS** | 4.1.14 | Utility-first CSS framework |
| **TanStack Query** | 5.90.2 | Server state management and caching |
| **React Router** | 7.9.3 | Client-side routing |
| **Axios** | 1.12.2 | HTTP client with CSRF protection |
| **Socket.IO Client** | 4.8.1 | WebSocket communication for camera streaming |
| **React Hot Toast** | 2.6.0 | Toast notifications |
| **Vitest** | 1.1.0 | Unit testing framework |
| **React Testing Library** | 16.2.0 | Component testing utilities |

**Browser Compatibility:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Node.js Requirement:** Node 18+ (for local development)

---

## Getting Started

### Prerequisites

1. **Node.js 18+**: Check version with `node -v`
2. **npm**: Comes with Node.js, check with `npm -v`
3. **Backend Running**: Flask API server must be running on port 5000

### Installation

```bash
# Navigate to frontend directory
cd /path/to/Mothbox/Firmware/webui/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The development server will start on `http://localhost:5173/` with hot module replacement (HMR) enabled.

### First-Time Setup

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Start Backend API:**
   ```bash
   cd ../backend
   python3 app.py
   ```

3. **Start Frontend Dev Server:**
   ```bash
   npm run dev
   ```

4. **Access Application:**
   Open browser to `http://localhost:5173/`

5. **Verify Connection:**
   - Dashboard should display system status
   - Gallery should load (may be empty if no photos captured yet)
   - Camera page should show live preview

---

## Project Structure

```
webui/frontend/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── PhotoGridItem.jsx       # Grid view photo card
│   │   ├── PhotoListItem.jsx       # List view photo item
│   │   ├── ProgressiveImage.jsx    # Progressive image loading
│   │   ├── PhotoSkeleton.jsx       # Loading placeholder
│   │   ├── EmptyStateMessage.jsx   # Empty state UI
│   │   ├── ViewModeToggle.jsx      # Grid/list toggle
│   │   ├── MothIcon.jsx            # SVG moth icon
│   │   ├── CollapsibleCard.jsx     # Collapsible container
│   │   ├── SavePresetModal.jsx     # Camera preset modal
│   │   ├── GPSSettings.jsx         # GPS configuration
│   │   ├── ErrorBoundary.jsx       # Error boundary wrapper
│   │   └── __tests__/              # Component tests
│   │
│   ├── pages/                # Top-level route components
│   │   ├── Dashboard.jsx           # System overview
│   │   ├── Gallery.jsx             # Photo gallery (infinite scroll)
│   │   ├── Camera.jsx              # Camera control & live preview
│   │   ├── GPIO.jsx                # Relay control interface
│   │   ├── Scheduler.jsx           # Cron job management
│   │   ├── Settings.jsx            # System settings
│   │   └── __tests__/              # Page component tests
│   │
│   ├── hooks/                # Custom React hooks
│   │   ├── useInfiniteScroll.js    # Infinite scroll logic
│   │   ├── useViewMode.js          # View mode persistence
│   │   └── __tests__/              # Hook tests
│   │
│   ├── utils/                # Utility functions
│   │   ├── api.js                  # Axios API client & endpoints
│   │   ├── csrf.js                 # CSRF token management
│   │   ├── queryKeys.js            # TanStack Query cache keys
│   │   └── helpers.js              # Format/validation helpers
│   │
│   ├── constants/            # Configuration constants
│   │   └── config.js               # UI config (gallery, toast, etc.)
│   │
│   ├── assets/               # Static assets
│   │
│   ├── App.jsx               # Root component with routing
│   ├── App.css               # Global styles
│   ├── main.jsx              # Application entry point
│   ├── index.css             # Tailwind CSS imports
│   └── setupTests.js         # Test environment configuration
│
├── public/                   # Static files (served as-is)
│   └── favicon.ico
│
├── dist/                     # Production build output (generated)
│   ├── index.html
│   └── assets/
│       ├── index-[hash].css
│       └── index-[hash].js
│
├── package.json              # Dependencies and scripts
├── vite.config.js            # Vite configuration
├── tailwind.config.js        # Tailwind CSS configuration
├── vitest.config.js          # Test configuration
├── eslint.config.js          # Linting rules
└── README.md                 # This file
```

### Key Directories

- **`src/components/`**: Reusable UI components used across multiple pages
- **`src/pages/`**: Top-level route components (one per navigation item)
- **`src/hooks/`**: Custom React hooks for shared logic
- **`src/utils/`**: Pure functions for API calls, formatting, validation
- **`src/constants/`**: Configuration values (avoid magic numbers)

---

## Available Scripts

### Development

```bash
# Start development server with HMR
npm run dev

# Development server starts on http://localhost:5173/
# Changes auto-reload in browser (~100ms)
```

### Testing

```bash
# Run tests in watch mode
npm test

# Run tests once (CI mode)
npm run test:run

# Run tests with UI interface
npm test:ui

# Generate coverage report
npm run test:coverage
```

### Production Build

```bash
# Build optimized production bundle
npm run build

# Output: dist/ directory
# Minified JS/CSS with content hashes
```

### Preview Production Build

```bash
# Serve production build locally
npm run preview

# Preview server starts on http://localhost:4173/
```

### Code Quality

```bash
# Lint JavaScript/JSX files
npm run lint

# Auto-fix linting issues
npm run lint -- --fix
```

---

## Development Workflow

### Starting Development

1. **Terminal 1 - Backend:**
   ```bash
   cd /path/to/Mothbox/Firmware/webui/backend
   export MOTHBOX_ENV=development
   python3 app.py
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd /path/to/Mothbox/Firmware/webui/frontend
   npm run dev
   ```

3. **Browser:** Navigate to `http://localhost:5173/`

### Hot Module Replacement (HMR)

Vite provides instant feedback during development:
- **JavaScript changes**: Components reload without full page refresh
- **CSS changes**: Styles update without reload
- **State preservation**: React Fast Refresh maintains component state

**Example Workflow:**
1. Edit `src/components/PhotoGridItem.jsx`
2. Save file
3. Browser updates in <100ms
4. Component state preserved during reload

### API Development

**Backend API Endpoint:** `http://localhost:5000/api`

**Environment Variable** (optional):
```bash
# In webui/frontend/.env (create if needed)
VITE_API_URL=http://localhost:5000/api
```

If not set, frontend uses current hostname (works for production deployment).

### Adding New Features

See **Contributing** section and `docs/frontend-components.md` for detailed patterns.

---

## Building for Production

### Build Process

```bash
npm run build
```

**Output:** `dist/` directory with optimized files

**Build Steps:**
1. Tree-shaking removes unused code
2. Minification reduces file sizes
3. Code splitting creates async chunks
4. Asset hashing for cache busting

**Example Output:**
```
dist/
├── index.html                     (0.52 KB, gzipped: 0.31 KB)
├── assets/
│   ├── index-BwL4K8Zx.css        (8.43 KB, gzipped: 2.18 KB)
│   └── index-DZp3V9gL.js       (183.27 KB, gzipped: 59.82 KB)
└── favicon.ico
```

### Deployment

**Backend serves frontend:**
1. Flask serves `dist/` as static files
2. Client navigates to Raspberry Pi IP (e.g., `http://192.168.1.100:5000`)
3. Backend returns `dist/index.html`
4. React app boots and makes API calls to `/api/*`

**Production Checklist:**
- ✅ Build with `npm run build`
- ✅ Test with `npm run preview`
- ✅ Backend configured to serve `dist/`
- ✅ CORS configured correctly
- ✅ CSRF protection enabled
- ✅ Production API endpoints working

---

## Testing

### Test Framework

**Vitest + React Testing Library** provides fast, reliable component testing.

### Running Tests

```bash
# Watch mode (recommended during development)
npm test

# Interactive commands in watch mode:
# - Press 'a' to run all tests
# - Press 'f' to run only failed tests
# - Press 'p' to filter by filename
# - Press 't' to filter by test name
# - Press 'q' to quit

# Run all tests once
npm run test:run

# Coverage report (HTML output)
npm run test:coverage
```

### Test Organization

Tests are colocated with source files:
```
src/components/
├── PhotoGridItem.jsx
└── __tests__/
    └── PhotoGridItem.test.jsx
```

### Writing Tests

**Example Component Test:**
```javascript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PhotoGridItem from '../PhotoGridItem'

describe('PhotoGridItem', () => {
  it('calls onClick when clicked', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    const photo = { path: 'test.jpg', filename: 'test.jpg', date: '2024-03-15' }

    render(<PhotoGridItem photo={photo} onClick={handleClick} />)

    const button = screen.getByRole('button')
    await user.click(button)

    expect(handleClick).toHaveBeenCalledWith(photo)
  })
})
```

### Test Coverage

Current coverage targets (Phase 1):
- Components: 85%+
- Hooks: 90%+
- Utilities: 95%+

View coverage report:
```bash
npm run test:coverage
# Opens htmlcov/index.html in browser
```

---

## Code Style

### ESLint Configuration

**Rules Enforced:**
- React Hooks rules (exhaustive deps, rules of hooks)
- React Refresh rules (HMR compatibility)
- ES6+ best practices

**Auto-fix on save** (VS Code):
```json
// .vscode/settings.json
{
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

### Tailwind CSS Conventions

**Utility-First Approach:**
```javascript
// ✅ Good - Use Tailwind utilities
<button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
  Click Me
</button>

// ❌ Bad - Avoid custom CSS
<style>
  .custom-button { padding: 8px 16px; background: blue; }
</style>
<button className="custom-button">Click Me</button>
```

**Responsive Design Pattern:**
```javascript
// Mobile-first with breakpoints
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
  {/* 2 cols on mobile, 3 on tablet, 4 on desktop */}
</div>
```

### Component Conventions

**File Naming:**
- Components: PascalCase (`PhotoGridItem.jsx`)
- Hooks: camelCase (`useInfiniteScroll.js`)
- Utilities: camelCase (`helpers.js`)

**Component Structure:**
```javascript
// 1. Imports
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

// 2. Component definition with JSDoc
/**
 * ComponentName - Brief description
 *
 * @param {Object} props - Component props
 * @param {string} props.requiredProp - Description
 */
export default function ComponentName({ requiredProp }) {
  // 3. Hooks (in order: state, queries, effects)
  const [state, setState] = useState(null)
  const { data } = useQuery(...)

  // 4. Event handlers
  const handleClick = () => { ... }

  // 5. Render
  return <div>...</div>
}
```

---

## Key Features

### 1. Photo Gallery

**Location:** `/gallery`

**Features:**
- Infinite scroll pagination (24 photos per page)
- Dual view modes: grid (compact) and list (detailed)
- Progressive image loading with fade-in animation
- Lightbox modal for full-resolution viewing
- Skeleton loading placeholders
- Empty state with call-to-action
- Toast notifications for loading/error states

**Performance:**
- Loads only visible photos (reduces bandwidth)
- Caches thumbnail requests
- IntersectionObserver for scroll detection (no polling)
- Optimized re-renders with React.memo

### 2. Camera Control

**Location:** `/camera`

**Features:**
- Real-time camera preview via WebSocket
- Adjustable settings: exposure, gain, focus, white balance
- Autofocus trigger with ROI selection
- Preset system (save/load camera configurations)
- Test capture to verify settings
- HDR mode and focus bracketing controls
- Live histogram and exposure feedback

**Technical:**
- Socket.IO WebSocket connection (~10 FPS preview)
- TanStack Query for settings persistence
- Optimistic updates for instant UI feedback

### 3. GPIO Control

**Location:** `/gpio`

**Features:**
- Toggle relay controls (attract lights, flash, UV lights)
- Real-time relay status display
- Flash trigger with duration control
- Safety interlocks (prevent simultaneous operations)

**Hardware:**
- Controls GPIO pins via backend API
- Supports both 4.x and 5.x firmware pin mappings

### 4. Scheduler

**Location:** `/scheduler`

**Features:**
- View active cron jobs
- Add new scheduled tasks
- Delete existing jobs
- Cron expression validation
- Common presets (sunset photos, nightly captures)

### 5. System Dashboard

**Location:** `/` (default route)

**Features:**
- System status overview (CPU, memory, storage)
- Power monitoring (INA260 sensor data)
- GPS status and synchronization
- Camera availability check
- Network information
- Uptime and boot time

### 6. Settings

**Location:** `/settings`

**Features:**
- Camera settings import/export
- Hardware configuration (GPIO pins, I2C addresses)
- GPS configuration (timeouts, baud rate)
- Web UI preferences
- System diagnostics

---

## API Integration

### HTTP Client

**Axios Instance** (`src/utils/api.js`):
```javascript
export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Include cookies for CSRF
})
```

**CSRF Protection:**
- Request interceptor adds `X-CSRFToken` header to POST/PUT/DELETE/PATCH
- Response interceptor handles CSRF validation failures with retry

### API Endpoints

**Gallery:**
```javascript
getPhotosPaginated({ limit, offset, sort }) // Paginated photo list
getThumbnailUrl(path)                       // Thumbnail URL builder
getPhotoUrl(path)                           // Full-resolution URL builder
```

**Camera:**
```javascript
getCameraSettings()                         // Current camera config
updateCameraSettings(settings)              // Update camera settings
capturePhoto()                              // Trigger photo capture
triggerAutofocus()                          // Run autofocus
```

**GPIO:**
```javascript
getGpioStatus()                             // Current relay states
controlGpio(relay, state)                   // Toggle relay on/off
triggerFlash()                              // Flash with duration
```

**Preferences:**
```javascript
getPreferences()                            // User preferences
setPreference(key, value)                   // Save preference
```

### TanStack Query

**Query Keys** (`src/utils/queryKeys.js`):
```javascript
QUERY_KEYS.PHOTOS_INFINITE     // ['photos', 'infinite']
QUERY_KEYS.CAMERA_SETTINGS     // ['camera-settings']
QUERY_KEYS.GPIO_STATUS         // ['gpio-status']
QUERY_KEYS.PREFERENCES         // ['preferences']
```

**Usage Pattern:**
```javascript
const { data, isLoading, error } = useQuery({
  queryKey: QUERY_KEYS.CAMERA_SETTINGS,
  queryFn: getCameraSettings,
  staleTime: 5 * 60 * 1000, // 5 minutes
})
```

**Mutations:**
```javascript
const mutation = useMutation({
  mutationFn: updateCameraSettings,
  onSuccess: () => {
    queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
  },
})
```

---

## Documentation

### Comprehensive Guides

1. **Frontend Components:** `docs/frontend-components.md`
   - Component architecture and hierarchy
   - Custom hooks documentation
   - Performance optimization techniques
   - Styling patterns and responsive design
   - Testing strategies

2. **Backend API:** `webui/backend/README.md`
   - API endpoint reference
   - Request/response formats
   - Error codes and handling
   - CSRF protection details

3. **Testing:** `Tests/README.md`
   - Unit test patterns
   - Integration test setup
   - Mocking strategies
   - Coverage requirements

### Quick Reference

**Component Props:**
```javascript
// See JSDoc comments in component files
<PhotoGridItem
  photo={{ path, filename, date }}
  onClick={(photo) => setSelected(photo)}
/>
```

**Custom Hooks:**
```javascript
// useInfiniteScroll
const sentinelRef = useInfiniteScroll({
  onLoadMore: fetchNextPage,
  hasMore: hasNextPage,
  isLoading: isFetchingNextPage,
})

// useViewMode
const { viewMode, setViewMode, isLoading } = useViewMode()
```

---

## Contributing

### Adding New Features

1. **Create Feature Branch:**
   ```bash
   git checkout -b feat/new-feature
   ```

2. **Implement Feature:**
   - Create component in `src/components/`
   - Add tests in `__tests__/`
   - Update documentation

3. **Run Tests:**
   ```bash
   npm test
   npm run test:coverage
   ```

4. **Build and Preview:**
   ```bash
   npm run build
   npm run preview
   ```

5. **Commit with Conventional Format:**
   ```bash
   git commit -m "feat(gallery): add photo download feature"
   ```

6. **Create Pull Request**

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic changes)
- `refactor`: Code restructuring
- `test`: Adding/updating tests
- `perf`: Performance improvements
- `chore`: Build/tooling changes

**Examples:**
```
feat(gallery): add infinite scroll pagination
fix(camera): resolve focus bracket timing issue
docs(readme): update installation instructions
test(hooks): add useViewMode error handling tests
```

### Code Review Checklist

- ✅ Component tests added with >85% coverage
- ✅ Accessibility (ARIA labels, keyboard navigation)
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Error handling (network errors, edge cases)
- ✅ Performance (avoid unnecessary re-renders)
- ✅ Documentation updated (JSDoc, README)
- ✅ Linting passes (`npm run lint`)
- ✅ Build succeeds (`npm run build`)

---

## Troubleshooting

### Common Issues

#### 1. Development Server Won't Start

**Error:** `EADDRINUSE: address already in use :::5173`

**Solution:**
```bash
# Find process using port 5173
lsof -ti:5173

# Kill the process
kill -9 <PID>

# Or use different port
npm run dev -- --port 3000
```

#### 2. API Connection Errors

**Error:** `Network Error` or `CORS policy` errors in browser console

**Solution:**
- Verify backend is running: `http://localhost:5000/api/system/status`
- Check `VITE_API_URL` environment variable
- Ensure CORS configured in backend (`app.py`)
- Check browser network tab for request details

#### 3. Hot Reload Not Working

**Symptom:** Changes don't appear in browser

**Solution:**
1. Check browser console for errors
2. Verify file saved successfully
3. Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
4. Restart dev server: `Ctrl+C` then `npm run dev`

#### 4. Tests Failing

**Error:** `Cannot find module` or import errors

**Solution:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vitest cache
rm -rf node_modules/.vitest

# Run tests again
npm test
```

#### 5. Build Errors

**Error:** `Module not found` or `Unexpected token`

**Solution:**
- Check for syntax errors in JSX files
- Verify all imports have correct paths
- Ensure all dependencies installed: `npm install`
- Check Node.js version: `node -v` (requires 18+)

#### 6. Gallery Photos Not Loading

**Symptom:** Empty gallery or broken image icons

**Solution:**
- Verify photos exist on Raspberry Pi filesystem
- Check backend logs for API errors
- Inspect network tab: Are thumbnail requests returning 200?
- Verify backend photo directory permissions
- Check `getThumbnailUrl()` constructs correct path

#### 7. WebSocket Connection Failed (Camera Preview)

**Error:** `WebSocket connection to 'ws://...' failed`

**Solution:**
- Verify Flask-SocketIO running in backend
- Check firewall allows WebSocket connections
- Ensure Socket.IO versions match (client: 4.8.1, server: compatible)
- Try camera page refresh to re-establish connection

### Debug Mode

**Enable Verbose Logging:**
```javascript
// Add to src/main.jsx temporarily
console.log('API Base URL:', import.meta.env.VITE_API_URL)

// In components
console.log('Photos loaded:', data?.pages)
console.log('Query state:', { isLoading, isError, error })
```

**React Query DevTools** (temporary):
```bash
npm install @tanstack/react-query-devtools
```

```javascript
// Add to App.jsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

<QueryClientProvider client={queryClient}>
  <AppRoutes />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

### Performance Issues

**Symptom:** Gallery lags when scrolling

**Solution:**
1. Check browser performance tab for bottlenecks
2. Verify thumbnail size is appropriate (256px default)
3. Enable React DevTools Profiler to find slow renders
4. Consider reducing `GALLERY_CONFIG.PAGE_SIZE` in `src/constants/config.js`

**Symptom:** Camera preview stuttering

**Solution:**
- Check network bandwidth (preview ~768KB/s at 10 FPS)
- Reduce preview resolution in backend settings
- Verify no other heavy network operations running

### Getting Help

1. **Check Documentation:**
   - `docs/frontend-components.md` - Component details
   - `webui/backend/README.md` - API reference
   - `Tests/README.md` - Testing guide

2. **Search Issues:**
   - GitHub repository issues
   - Check closed issues for similar problems

3. **Debug Information to Include:**
   - Node.js version (`node -v`)
   - npm version (`npm -v`)
   - Browser and version
   - Console error messages
   - Network tab screenshots
   - Steps to reproduce

---

## License

This project is part of the Mothbox automated insect photography system. See repository root for license information.

---

## Acknowledgments

**Built With:**
- [React](https://react.dev/) - UI library
- [Vite](https://vitejs.dev/) - Build tool
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework
- [TanStack Query](https://tanstack.com/query/latest) - Data fetching
- [Vitest](https://vitest.dev/) - Testing framework

**Developed for:**
- Raspberry Pi 4/5 with Arducam OwlSight 64MP camera
- Automated moth and insect photography
- Field research and biodiversity monitoring

---

**Last Updated:** November 10, 2025
**Frontend Version:** Phase 1 - Gallery Enhancement Complete
**Node Requirement:** 18+
**Browser Support:** Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
