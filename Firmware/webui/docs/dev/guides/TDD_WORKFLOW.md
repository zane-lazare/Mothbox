# TDD Workflow Reference Guide

**Project**: Mothbox Gallery Enhancement
**Testing Philosophy**: Test-driven development with 85%+ coverage requirement
**Framework**: pytest (backend), Jest + React Testing Library (frontend)

---

## Overview

This guide provides reference patterns from the existing Mothbox codebase to accelerate TDD workflow. Instead of detailed tutorials, it points you to proven test patterns already in the project.

---

## Quick Reference: Existing Test Patterns

### Backend Testing Patterns

| Pattern | Reference File | Use Case |
|---------|---------------|----------|
| **Service with hardware mocking** | `Tests/unit/test_tuning_loader.py` | Services that interact with camera, GPIO, sensors |
| **Flask API routes** | `Tests/unit/test_gallery_routes.py` | REST API endpoints with CSRF, file serving |
| **Path resolution** | `Tests/unit/test_mothbox_paths_hardware.py` | Testing path utilities and config loading |
| **Integration workflow** | `Tests/integration/test_autofocus_workflows.py` | Multi-component workflows with real I/O |
| **Configuration parsing** | `Tests/unit/test_config.py` | Testing config file readers and validators |

### Frontend Testing Patterns

| Pattern | Reference Location | Use Case |
|---------|-------------------|----------|
| **React component** | `webui/frontend/src/components/__tests__/` | UI component rendering and interactions |
| **Custom hooks** | Look for `use*.test.js` files | React hooks with state management |
| **API integration** | Mock axios/fetch calls in component tests | Components that fetch data |
| **User interactions** | Use `@testing-library/user-event` | Button clicks, form inputs, navigation |

---

## TDD Workflow: Standard Cycle

```bash
# 1. Create test file FIRST (before implementation)
touch Tests/unit/test_new_feature.py

# 2. Write failing test
# See patterns below

# 3. Run test (should fail with clear error)
pytest Tests/unit/test_new_feature.py -v

# 4. Implement minimal code to pass test
# Edit source file

# 5. Run test again (should pass)
pytest Tests/unit/test_new_feature.py -v

# 6. Refactor with confidence (tests protect you)
# Improve code quality without breaking functionality

# 7. Add more test cases, repeat cycle
# Edge cases, error handling, performance

# 8. Check coverage before committing
pytest Tests/unit/test_new_feature.py --cov=module --cov-report=term
```

---

## Pattern 1: Backend Service with Mocking

**Reference**: `Tests/unit/test_tuning_loader.py`

### Key Techniques from Reference

```python
# 1. Mock hardware dependencies
@pytest.fixture
def mock_camera(monkeypatch):
    """Mock Picamera2 to avoid requiring real hardware"""
    mock = Mock()
    monkeypatch.setattr('tuning_loader.Picamera2', mock)
    return mock

# 2. Use tmp_path for filesystem operations
def test_tuning_file_loading(tmp_path):
    """Test file I/O without affecting real filesystem"""
    test_file = tmp_path / "test_tuning.json"
    test_file.write_text('{"key": "value"}')
    result = load_tuning_file(test_file)
    assert result['key'] == 'value'

# 3. Test error handling explicitly
def test_handles_missing_file_gracefully():
    """Verify behavior when dependencies unavailable"""
    result = load_tuning_file(Path("/nonexistent/file.json"))
    assert result is None  # Or appropriate default

# 4. Parametrize for multiple scenarios
@pytest.mark.parametrize("camera_model,expected", [
    ("ov64a40", "ov64a40_tuning.json"),
    ("imx708", "imx708_tuning.json"),
    ("unknown", "default_tuning.json"),
])
def test_model_detection(camera_model, expected):
    # Test matrix of inputs/outputs
    pass
```

### Apply to Gallery Enhancement

**Example**: Testing thumbnail cache service (Issue #134)

```python
# Tests/unit/test_thumbnail_cache.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from webui.backend.services.thumbnail_cache import ThumbnailCache

@pytest.fixture
def cache_dir(tmp_path):
    """Temporary cache directory for testing"""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache

@pytest.fixture
def sample_photo(tmp_path):
    """Create a test photo file"""
    photo = tmp_path / "test.jpg"
    # Create minimal valid JPEG (use PIL)
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='red')
    img.save(photo)
    return photo

def test_cache_miss_generates_thumbnail(cache_dir, sample_photo):
    """First request should generate and cache thumbnail"""
    cache = ThumbnailCache(cache_dir)

    # Cache should be empty
    assert not list(cache_dir.glob("*"))

    # Request thumbnail (cache miss)
    thumbnail = cache.get_thumbnail(sample_photo, size=300)

    # Verify thumbnail generated
    assert thumbnail.exists()
    assert thumbnail.parent == cache_dir

def test_cache_hit_returns_cached_file(cache_dir, sample_photo):
    """Second request should use cached thumbnail"""
    cache = ThumbnailCache(cache_dir)

    # First request (generates)
    thumb1 = cache.get_thumbnail(sample_photo, size=300)
    mtime1 = thumb1.stat().st_mtime

    # Second request (from cache)
    thumb2 = cache.get_thumbnail(sample_photo, size=300)
    mtime2 = thumb2.stat().st_mtime

    # Should be same file (not regenerated)
    assert thumb1 == thumb2
    assert mtime1 == mtime2

def test_cache_invalidation_on_source_change(cache_dir, sample_photo):
    """Cache should regenerate when source photo modified"""
    cache = ThumbnailCache(cache_dir)

    # Generate initial thumbnail
    thumb1 = cache.get_thumbnail(sample_photo, size=300)

    # Modify source photo (touch to update mtime)
    sample_photo.touch()

    # Request again (should regenerate due to mtime change)
    thumb2 = cache.get_thumbnail(sample_photo, size=300)

    # Verify regeneration occurred (check implementation)
    # This depends on your cache invalidation logic

# Follow patterns from test_tuning_loader.py for more scenarios
```

---

## Pattern 2: Flask API Routes

**Reference**: `Tests/unit/test_gallery_routes.py`

### Key Techniques from Reference

```python
# 1. Flask test client fixture
@pytest.fixture
def client():
    """Flask test client for API testing"""
    from webui.backend.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 2. Test successful responses
def test_get_photos_returns_list(client):
    """GET /api/gallery/photos should return photo list"""
    response = client.get('/api/gallery/photos')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

# 3. Test error cases explicitly
def test_get_nonexistent_photo_returns_404(client):
    """GET /api/gallery/photo/<invalid> should return 404"""
    response = client.get('/api/gallery/photo/nonexistent.jpg')
    assert response.status_code == 404

# 4. Test path traversal protection
def test_path_traversal_blocked(client):
    """API should reject ../ path attacks"""
    response = client.get('/api/gallery/photo/../../../etc/passwd')
    assert response.status_code == 400
    # Or 404, depending on implementation

# 5. Test CSRF protection on POST/PUT/DELETE
def test_post_without_csrf_token_fails(client):
    """State-changing requests require CSRF token"""
    response = client.post('/api/gallery/delete/photo.jpg')
    assert response.status_code == 400
    # Error message should mention CSRF
```

### Apply to Gallery Enhancement

**Example**: Testing pagination API (Issue #135)

```python
# Tests/unit/test_gallery_pagination.py
import pytest
from webui.backend.app import create_app

@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()

def test_pagination_first_page(client):
    """GET /api/gallery/photos?page=1&per_page=50"""
    response = client.get('/api/gallery/photos?page=1&per_page=50')

    assert response.status_code == 200
    data = response.get_json()

    # Verify pagination metadata
    assert 'photos' in data
    assert 'pagination' in data
    assert data['pagination']['page'] == 1
    assert data['pagination']['per_page'] == 50
    assert len(data['photos']) <= 50

def test_pagination_invalid_page(client):
    """Invalid page number should return 400"""
    response = client.get('/api/gallery/photos?page=-1')
    assert response.status_code == 400

def test_pagination_page_exceeds_total(client):
    """Page beyond total should return empty list"""
    response = client.get('/api/gallery/photos?page=9999')
    assert response.status_code == 200
    data = response.get_json()
    assert data['photos'] == []
    assert data['pagination']['has_next'] == False

# Follow test_gallery_routes.py for more patterns
```

---

## Pattern 3: React Component Testing

**Reference**: `webui/frontend/src/components/__tests__/`

### Key Techniques

```javascript
// 1. Basic component render test
import { render, screen } from '@testing-library/react'
import { PhotoCard } from '../PhotoCard'

test('renders photo card with thumbnail', () => {
  const photo = { id: '1', filename: 'test.jpg', thumbnail: '/thumb.jpg' }
  render(<PhotoCard photo={photo} />)

  const img = screen.getByRole('img')
  expect(img).toHaveAttribute('src', '/thumb.jpg')
})

// 2. User interaction test
import userEvent from '@testing-library/user-event'

test('clicking photo opens lightbox', async () => {
  const user = userEvent.setup()
  const onPhotoClick = jest.fn()

  render(<PhotoCard photo={photo} onClick={onPhotoClick} />)

  await user.click(screen.getByRole('img'))
  expect(onPhotoClick).toHaveBeenCalledWith(photo)
})

// 3. Mock API calls
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  rest.get('/api/gallery/photos', (req, res, ctx) => {
    return res(ctx.json([{ id: '1', filename: 'test.jpg' }]))
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('gallery loads photos from API', async () => {
  render(<Gallery />)

  expect(await screen.findByText('test.jpg')).toBeInTheDocument()
})
```

### Apply to Gallery Enhancement

**Example**: Testing infinite scroll (Issue #136)

```javascript
// webui/frontend/src/components/__tests__/InfiniteScrollGallery.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { InfiniteScrollGallery } from '../InfiniteScrollGallery'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

test('loads initial batch of photos', async () => {
  render(<InfiniteScrollGallery />, { wrapper: createWrapper() })

  // Wait for photos to load
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(50)
  })
})

test('loads more photos on scroll to bottom', async () => {
  render(<InfiniteScrollGallery />, { wrapper: createWrapper() })

  // Initial batch
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(50)
  })

  // Simulate scroll to bottom
  const sentinel = screen.getByTestId('scroll-sentinel')
  const mockIntersectionObserver = jest.fn()
  mockIntersectionObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null
  })
  window.IntersectionObserver = mockIntersectionObserver

  // Trigger intersection
  const [callback] = mockIntersectionObserver.mock.calls[0]
  callback([{ isIntersecting: true }])

  // Wait for next batch
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(100)
  })
})
```

---

## Running Tests

### Unit Tests (Fast)

```bash
# All unit tests
pytest Tests/unit/ -v

# Specific test file
pytest Tests/unit/test_thumbnail_cache.py -v

# Specific test function
pytest Tests/unit/test_thumbnail_cache.py::test_cache_hit -v

# With coverage
pytest Tests/unit/ --cov=webui/backend --cov-report=html
open htmlcov/index.html
```

### Integration Tests (Slower, Requires Hardware)

```bash
# All integration tests
pytest Tests/integration/ -v -s

# Skip hardware tests (for CI)
pytest Tests/integration/ -v -m "not hardware"

# Run specific integration test
pytest Tests/integration/test_export_workflow.py -v -s
```

### Frontend Tests

```bash
cd webui/frontend

# All tests
npm test

# Watch mode (re-run on file changes)
npm test -- --watch

# Coverage report
npm test -- --coverage
```

---

## Coverage Requirements

### Per pyproject.toml

```toml
[tool.coverage.run]
branch = true
source = ["webui/backend", "mothbox_paths"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:"
]
fail_under = 85
```

### Checking Coverage

```bash
# Generate coverage report
pytest Tests/ --cov=webui/backend --cov=mothbox_paths --cov-report=html

# View in browser
open htmlcov/index.html

# Terminal report
pytest Tests/ --cov=webui/backend --cov-report=term

# Fail if below 85%
coverage report --fail-under=85
```

---

## Common Test Patterns

### Testing Error Handling

```python
def test_handles_missing_file():
    """Verify graceful handling of missing dependencies"""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.txt"))

def test_handles_corrupt_json():
    """Verify graceful handling of malformed data"""
    result = parse_json("{ invalid json }")
    assert result is None  # Or appropriate default
    # Check logs for error message
```

### Testing Async Operations

```python
import asyncio

@pytest.mark.asyncio
async def test_async_photo_processing():
    """Test async image processing"""
    result = await process_photo_async("test.jpg")
    assert result.status == "success"
```

### Testing with Fixtures

```python
@pytest.fixture
def sample_photos(tmp_path):
    """Generate test photos for gallery tests"""
    photos = []
    for i in range(10):
        photo = tmp_path / f"photo_{i}.jpg"
        # Create minimal JPEG
        from PIL import Image
        Image.new('RGB', (100, 100)).save(photo)
        photos.append(photo)
    return photos

def test_pagination_with_sample_photos(sample_photos):
    """Use fixture to test with known dataset"""
    page = get_photo_page(sample_photos, page=1, per_page=5)
    assert len(page) == 5
```

---

## Debugging Tests

### Run with Verbose Output

```bash
# Show print statements
pytest Tests/unit/test_feature.py -v -s

# Show local variables on failure
pytest Tests/unit/test_feature.py -v -l

# Stop on first failure
pytest Tests/unit/test_feature.py -v -x

# Run last failed tests only
pytest --lf
```

### Use pytest Debugger

```python
def test_complex_logic():
    result = complex_function()

    # Drop into debugger if assertion fails
    import pdb; pdb.set_trace()

    assert result == expected
```

### Print Debug Info

```python
def test_with_debug_output(capsys):
    """Capture and verify print statements"""
    function_that_prints()

    captured = capsys.readouterr()
    assert "expected message" in captured.out
```

---

## Test Organization Checklist

For each issue, ensure:

- [ ] Test file created BEFORE implementation
- [ ] Tests cover happy path (expected usage)
- [ ] Tests cover error cases (invalid input, missing data)
- [ ] Tests cover edge cases (empty lists, None values, boundaries)
- [ ] Tests use appropriate fixtures (reusable test data)
- [ ] Tests are independent (can run in any order)
- [ ] Tests are fast (<1 second each for unit tests)
- [ ] Coverage ≥85% for new code
- [ ] Tests follow existing patterns in codebase

---

## Reference Files Quick Index

### Backend Tests
- Service mocking: `Tests/unit/test_tuning_loader.py`
- API routes: `Tests/unit/test_gallery_routes.py`
- Path utilities: `Tests/unit/test_mothbox_paths_hardware.py`
- Config parsing: `Tests/unit/test_config.py`
- Integration: `Tests/integration/test_autofocus_workflows.py`

### Frontend Tests
- Components: `webui/frontend/src/components/__tests__/`
- React hooks: Look for `use*.test.js` patterns
- API mocking: Use MSW (Mock Service Worker) pattern

### Test Configuration
- pytest config: `pyproject.toml` (coverage, markers, paths)
- Frontend config: `webui/frontend/vite.config.js`
- Fixtures: `Tests/conftest.py` (shared fixtures)

---

## Getting Help

1. **Check existing tests**: Most patterns already exist in codebase
2. **Read pytest docs**: https://docs.pytest.org/
3. **Read RTL docs**: https://testing-library.com/docs/react-testing-library/intro/
4. **GitHub Issues**: Ask questions in issue comments
5. **TESTING_PROCEDURE.md**: Manual hardware testing procedures

---

**Last Updated**: 2025-01-06
**Version**: 1.0
