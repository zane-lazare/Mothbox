# Mothbox Documentation Index

**Project**: Mothbox Automated Camera Trap System
**Version**: Phase 1 Gallery Enhancement (v5.1.0)
**Last Updated**: 2025-11-10

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Gallery Enhancement Documentation (Phase 1)](#gallery-enhancement-documentation-phase-1)
3. [Architecture & Design](#architecture--design)
4. [API Reference](#api-reference)
5. [Developer Guides](#developer-guides)
6. [Testing & Quality Assurance](#testing--quality-assurance)
7. [Project Management](#project-management)
8. [Configuration & Setup](#configuration--setup)
9. [Reading Paths](#reading-paths)
10. [External Resources](#external-resources)

---

## Quick Start

**New to Mothbox?** Start here:

1. [CLAUDE.md](../CLAUDE.md) - Project overview, architecture, and development guidelines (5 min)
2. [webui/README.md](../webui/README.md) - Web UI overview and security notice (3 min)
3. [Gallery Architecture](gallery-architecture.md) - Gallery system design (Phase 1) (15 min)

**Ready to develop?**

- Frontend developers: [Frontend Components Guide](frontend-components.md)
- Backend developers: [Gallery Developer Guide](gallery-developer-guide.md)
- Testing: [Gallery Testing Documentation](gallery-testing.md)

---

## Gallery Enhancement Documentation (Phase 1)

Phase 1 implements the performance foundation for the photo gallery system, including thumbnail caching, pagination, infinite scroll, and comprehensive loading states.

### Core Gallery Documentation

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Gallery Architecture](gallery-architecture.md) | High-level system architecture, data flow diagrams, caching strategy, and performance characteristics for the gallery system | 15 min |
| [Gallery Developer Guide](gallery-developer-guide.md) | Practical patterns and workflows for developers extending or maintaining the gallery system with real implementation examples | 30 min |
| [Frontend Components](frontend-components.md) | Comprehensive documentation of all React components, hooks, and state management patterns used in the gallery UI | 40 min |
| [Thumbnail Cache Guide](thumbnail-cache.md) | In-depth guide to the multi-resolution thumbnail caching system with LRU eviction and performance tuning | 20 min |
| [Gallery Testing](gallery-testing.md) | Testing procedures, performance validation, and coverage requirements for gallery features | 30 min |

**Prerequisites**: Basic familiarity with React, Flask, and Raspberry Pi hardware recommended.

---

## Architecture & Design

### System Architecture

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [CLAUDE.md](../CLAUDE.md) | Master reference for project architecture, path resolution system, camera workflows, hardware configuration, and development patterns | 25 min |
| [Gallery Architecture](gallery-architecture.md) | Gallery-specific architecture including component diagrams, data flow, caching strategy, and scalability analysis | 15 min |

### Design Decisions

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Issue #137 Bug Analysis](issue-137-backend-persistence-bug.md) | Post-mortem analysis of gallery view mode persistence bug with root cause analysis and lessons learned | 5 min |

---

## API Reference

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Gallery API](api/gallery.md) | Complete REST API documentation for gallery endpoints including pagination, thumbnail serving, cache management, and error handling | 20 min |

**API Base URL**: `/api/gallery`
**Authentication**: None (see security notice in webui/README.md)
**Format**: JSON responses (except binary image data)

---

## Developer Guides

### Backend Development

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Gallery Developer Guide](gallery-developer-guide.md) | Backend patterns, service architecture, adding new features, and common pitfalls with solutions | 30 min |
| [Thumbnail Cache Guide](thumbnail-cache.md) | Cache implementation details, configuration options, monitoring, and troubleshooting | 20 min |
| [CLAUDE.md](../CLAUDE.md) | Path resolution, GPIO configuration, camera resource management, and CSRF protection patterns | 25 min |

### Frontend Development

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Frontend Components](frontend-components.md) | Component hierarchy, custom hooks, TanStack Query integration, and performance optimization techniques | 40 min |
| [webui/frontend/README.md](../webui/frontend/README.md) | Technology stack, project structure, development workflow, and build instructions | 15 min |

### Development Workflow

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [TDD Workflow Reference](TDD_WORKFLOW.md) | Test-driven development patterns with references to existing test files for backend (pytest) and frontend (Jest) | 10 min |
| [CLAUDE.md](../CLAUDE.md) | Common development commands for testing, linting, security scanning, and running the dev server | 5 min |

---

## Testing & Quality Assurance

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Gallery Testing](gallery-testing.md) | Comprehensive testing procedures for Phase 1 gallery features including performance validation and coverage requirements | 30 min |
| [Tests/README.md](../Tests/README.md) | Testing infrastructure overview, markers, fixtures, and coverage configuration | 15 min |
| [TDD Workflow Reference](TDD_WORKFLOW.md) | Quick reference to proven test patterns already in the codebase for accelerating TDD workflow | 10 min |

**Key Testing Requirements**:
- Minimum 85% code coverage enforced in CI/CD
- Performance targets: <2 seconds gallery load (500 photos, cold cache)
- Security scanning: Bandit with MEDIUM+ severity enforcement

**Running Tests**:
```bash
# All tests (requires Raspberry Pi hardware)
pytest Tests/ -v -s

# Unit tests only (can run without hardware)
pytest Tests/unit/ -v

# Gallery-specific tests
pytest Tests/unit/test_gallery*.py -v
pytest Tests/integration/test_gallery_performance.py -v -s

# With coverage report
pytest Tests/ --cov=webui/backend --cov-report=html
```

---

## Project Management

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [Gallery Roadmap](../GALLERY_ROADMAP.md) | Five-phase development roadmap with timeline, metrics, and success criteria for complete gallery enhancement | 20 min |
| [Gallery Gantt Chart](GALLERY_GANTT.md) | Visual timeline representations (Mermaid diagrams) for all project phases and dependencies | 5 min |
| [Project Views Setup](PROJECT_VIEWS_SETUP.md) | Guide for configuring GitHub Project #2 custom views to track gallery enhancement progress | 5 min |

**Project Context**:
- **Timeline**: 5 phases over 20 weeks (17-20 calendar weeks with full-time capacity)
- **Methodology**: TDD strict with 85%+ coverage requirement
- **Deployment**: Phase-by-phase with user validation checkpoints
- **GitHub Project**: [Photo Gallery Enhancement #2](https://github.com/users/zane-lazare/projects/2)

**Phase 1 Status**: ✅ Complete (deployed and validated)
**Current Phase**: Phase 2 (Photo Viewer & Metadata)

---

## Configuration & Setup

| Document | Description | Reading Time |
|----------|-------------|--------------|
| [CLAUDE.md](../CLAUDE.md) | Installation types, path resolution system, hardware configuration, and configuration file formats | 15 min |
| [webui/README.md](../webui/README.md) | Security notice, installation instructions, and deployment considerations | 10 min |
| [Thumbnail Cache Guide](thumbnail-cache.md) | Cache configuration options and performance tuning parameters | 10 min |

**Key Configuration Files**:
- `controls.txt` - Hardware configuration (GPIO pins, I2C addresses, feature flags)
- `camera_settings.csv` - Camera parameters (resolution, exposure, focus, HDR)
- `schedule_settings.csv` - Cron scheduling configuration
- `liveview_settings.txt` - Camera streaming parameters

**Path Resolution**: All code uses `mothbox_paths.py` for path resolution. Never hardcode paths.

---

## Reading Paths

Different roles have different documentation needs. Follow these recommended sequences:

### New Developer (Start Here)

Complete this sequence to understand the full project:

1. **[CLAUDE.md](../CLAUDE.md)** (25 min) - Project architecture and development patterns
2. **[Gallery Architecture](gallery-architecture.md)** (15 min) - Gallery system design
3. **[TDD Workflow Reference](TDD_WORKFLOW.md)** (10 min) - Testing patterns
4. **[Gallery Developer Guide](gallery-developer-guide.md)** (30 min) - Practical development patterns

**Total**: ~80 minutes

### Frontend Developer

Focus on React components and UI patterns:

1. **[webui/frontend/README.md](../webui/frontend/README.md)** (15 min) - Project setup
2. **[Frontend Components](frontend-components.md)** (40 min) - Component documentation
3. **[Gallery API](api/gallery.md)** (20 min) - Backend integration
4. **[Gallery Architecture](gallery-architecture.md)** (15 min) - Data flow understanding

**Total**: ~90 minutes

### Backend Developer

Focus on Flask API and service architecture:

1. **[CLAUDE.md](../CLAUDE.md)** (25 min) - Path resolution and hardware patterns
2. **[Gallery Architecture](gallery-architecture.md)** (15 min) - System design
3. **[Gallery Developer Guide](gallery-developer-guide.md)** (30 min) - Backend patterns
4. **[Thumbnail Cache Guide](thumbnail-cache.md)** (20 min) - Caching implementation
5. **[Gallery API](api/gallery.md)** (20 min) - API reference

**Total**: ~110 minutes

### QA / Testing Specialist

Focus on testing infrastructure and validation:

1. **[Gallery Testing](gallery-testing.md)** (30 min) - Test procedures
2. **[TDD Workflow Reference](TDD_WORKFLOW.md)** (10 min) - Test patterns
3. **[Tests/README.md](../Tests/README.md)** (15 min) - Test infrastructure
4. **[Gallery Architecture](gallery-architecture.md)** (15 min) - Performance targets

**Total**: ~70 minutes

### DevOps / Deployment

Focus on configuration and deployment:

1. **[CLAUDE.md](../CLAUDE.md)** (25 min) - Installation types and configuration
2. **[webui/README.md](../webui/README.md)** (10 min) - Security and deployment
3. **[Thumbnail Cache Guide](thumbnail-cache.md)** (10 min) - Cache configuration
4. **[Gallery Architecture](gallery-architecture.md)** (15 min) - Scalability considerations

**Total**: ~60 minutes

---

## Documentation Metadata

Complete list of all documentation with metadata:

| Document | Location | Lines | Last Updated | Status |
|----------|----------|-------|--------------|--------|
| **Project Overview** |
| CLAUDE.md | `/CLAUDE.md` | ~800 | 2025-11-10 | Current |
| Gallery Roadmap | `planning/GALLERY_ROADMAP.md` | ~1200 | 2025-01-06 | Phase 1 Complete |
| **Gallery Phase 1** |
| Gallery Architecture | `architecture/gallery-architecture.md` | 960 | 2025-11-10 | Production |
| Gallery API | `api/gallery.md` | 1218 | 2025-11-10 | Production |
| Thumbnail Cache Guide | `architecture/thumbnail-cache.md` | 1270 | 2025-11-10 | Production |
| Gallery Developer Guide | `guides/gallery-developer-guide.md` | 2229 | 2025-01-10 | Production |
| Frontend Components | `architecture/frontend-components.md` | 2790 | 2025-11-10 | Production |
| Gallery Testing | `testing/gallery-testing.md` | 2107 | 2025-11-10 | Production |
| **Development** |
| TDD Workflow | `guides/TDD_WORKFLOW.md` | 629 | 2025-11-06 | Current |
| Tests README | `/Tests/README.md` | ~500 | 2025-11-06 | Current |
| **Web UI** |
| Web UI README | `/webui/README.md` | ~400 | 2025-11-06 | Current |
| Frontend README | `/webui/frontend/README.md` | ~600 | 2025-11-06 | Current |
| **Project Management** |
| Gallery Gantt Chart | `planning/GALLERY_GANTT.md` | 298 | 2025-11-06 | Current |

---

## External Resources

### Technology Stack Documentation

**Backend**:
- [Flask 3.0 Documentation](https://flask.palletsprojects.com/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- [Pillow (PIL) Documentation](https://pillow.readthedocs.io/)
- [simplejpeg](https://pypi.org/project/simplejpeg/) - Fast JPEG encoding

**Frontend**:
- [React 18 Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [TanStack Query (React Query)](https://tanstack.com/query/latest)
- [Tailwind CSS](https://tailwindcss.com/)
- [React Router](https://reactrouter.com/)

**Testing**:
- [pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)

**Hardware**:
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [Picamera2 Library](https://github.com/raspberrypi/picamera2)
- [Arducam OwlSight 64MP](https://www.arducam.com/)

### Related Projects

- [Mothbox Hardware Repository](https://github.com/zane-lazare/Mothbox) - Hardware designs and assembly
- [GitHub Project #2](https://github.com/users/zane-lazare/projects/2) - Gallery Enhancement tracking

---

## Documentation Standards

### Contributing to Documentation

When creating or updating documentation:

1. **Include metadata header**:
   ```markdown
   **Last Updated**: YYYY-MM-DD
   **Version**: Phase X (vX.X.X)
   **Status**: Draft | Current | Production | Archived
   ```

2. **Add table of contents** for documents >300 lines

3. **Use clear headings**: Follow hierarchy (H1 → H2 → H3)

4. **Include code examples**: Use proper syntax highlighting

5. **Link related docs**: Cross-reference relevant documentation

6. **Keep it updated**: Update "Last Updated" date when making changes

7. **Test code examples**: Ensure all code snippets are tested and working

### Documentation Style

- **Tone**: Professional, technical, clear, and concise
- **Voice**: Active voice preferred
- **Language**: Technical but accessible
- **Code blocks**: Always include language identifier for syntax highlighting
- **Commands**: Include brief descriptions of what each command does
- **Examples**: Provide real-world usage examples

### File Naming Conventions

- Lowercase with hyphens: `gallery-architecture.md`
- Descriptive names: `thumbnail-cache.md` not `cache.md`
- API docs in `api/` subdirectory
- ALL CAPS for project-level docs: `CLAUDE.md`, `TDD_WORKFLOW.md`

---

## Troubleshooting

### Common Documentation Issues

**"I can't find documentation on X"**:
- Check this index for all available documentation
- Search within specific documents using your editor's find function
- Check `CLAUDE.md` for general architecture patterns

**"Documentation is outdated"**:
- Check "Last Updated" date in document header
- Refer to `GALLERY_ROADMAP.md` for current phase status
- Submit an issue if documentation needs updating

**"I need help with testing"**:
- Start with [Gallery Testing](testing/gallery-testing.md)
- Review [TDD Workflow Reference](guides/TDD_WORKFLOW.md)
- Check [Tests/README.md](../../../Tests/README.md) for infrastructure details

**"I need help with camera/GPIO"**:
- See [CLAUDE.md](../../../CLAUDE.md) sections on:
  - Camera System (photo capture vs. live preview)
  - GPIO Pin Access (using `get_gpio_pins()`)
  - Hardware Configuration (using `get_hardware_config()`)

**"I need help with gallery performance"**:
- Review [Gallery Architecture](architecture/gallery-architecture.md) - Performance Characteristics section
- Check [Thumbnail Cache Guide](architecture/thumbnail-cache.md) - Performance Tuning section
- See [Gallery Testing](testing/gallery-testing.md) - Performance validation procedures

---

## Document Updates

This index file should be updated when:

- New documentation is added to `webui/docs/dev/` subdirectories
- Documentation files are renamed or moved
- Major documentation updates occur (version changes, restructuring)
- New project phases begin

**Maintainer**: Update this file as part of each phase completion or major documentation effort.

**Last Index Update**: 2025-11-10

---

## License

Mothbox is open-source hardware and software. See repository root for license information.

---

**Questions or suggestions for documentation improvements?** Please open an issue in the GitHub repository.
