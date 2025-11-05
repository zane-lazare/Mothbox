# Security Testing

This document describes the security testing tools and procedures for the Mothbox firmware.

## Bandit - Python Security Scanner

Bandit is a static security analysis tool that scans Python code for common security vulnerabilities.

### What Bandit Checks For

- **Command Injection** (HIGH): Use of shell commands with user input
- **Hardcoded Secrets** (HIGH): API keys, passwords in source code
- **SQL Injection** (HIGH): Unsafe database query construction
- **Insecure Temp Files** (MEDIUM): Predictable temporary file paths
- **File Permissions** (MEDIUM): Overly permissive file/directory permissions
- **Bind to All Interfaces** (MEDIUM): Network services exposed to all interfaces
- And many more security issues...

### Running Bandit Locally

#### Prerequisites

Install Bandit with TOML support:

```bash
pip install bandit[toml]
```

Or using pipx (recommended):

```bash
pipx install 'bandit[toml]'
```

#### Basic Scan

From the `Firmware/` directory, run:

```bash
# Scan with MEDIUM+ severity (matches CI/CD policy)
bandit -c pyproject.toml -r . --severity-level medium

# Scan with all findings (including LOW)
bandit -c pyproject.toml -r .

# Generate JSON report
bandit -c pyproject.toml -r . --format json --output bandit-report.json
```

#### Understanding Results

Bandit reports issues with:

- **Severity**: HIGH, MEDIUM, LOW, or INFO
- **Confidence**: HIGH, MEDIUM, or LOW
- **CWE ID**: Common Weakness Enumeration reference
- **Location**: File path and line number

Example output:

```
>> Issue: [B605:start_process_with_a_shell] Starting a process with a shell
   Severity: High   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   Location: ./4.x/GPS.py:149
```

### CI/CD Enforcement Policy

The GitHub Actions workflow enforces this policy:

- ✅ **MEDIUM and HIGH severity**: CI **FAILS** - must be fixed before merge
- ⚠️ **LOW severity**: Warning only - address during refactoring
- ℹ️ **INFO**: Informational - no action required

This is **stricter** than Issue #79's original suggestion (HIGH-only).

### Security Exceptions

When Bandit flags legitimate code patterns, use `# nosec` comments with clear justifications:

#### Good Examples

```python
# GPS time setting - data validated by strptime
os.system(f"sudo date -u -s \"{formatted_time}\"")  # nosec B605 - GPS time from hardware, validated by strptime

# Web server for local network access
HOST = '0.0.0.0'  # nosec B104 - Mothbox is a local network device, needs LAN access with CSRF/CORS protection

# Standard directory permissions
os.chmod(folder_path, 0o755)  # nosec B103 - Standard directory permissions for photo storage
```

#### Bad Examples

```python
# DON'T DO THIS - No explanation
password = "admin123"  # nosec

# DON'T DO THIS - Vague justification
eval(user_input)  # nosec - needed for functionality
```

### Configuration

Bandit configuration is in `pyproject.toml`:

```toml
[tool.bandit]
exclude_dirs = [
    "Tests/",              # Test code allowed to use subprocess, etc.
    "*/OldScripts/*",      # Deprecated scripts
    "webui/frontend/",     # JavaScript (scanned separately)
    # ... more exclusions
]
```

### Excluded Directories

These directories are excluded from Bandit scanning:

- **Tests/**: Test code legitimately uses subprocess, mocking, etc.
- **OldScripts/**: Deprecated scripts not in production use
- **RaspberryPi_JetsonNano_Epaper/**: Third-party vendor library (490 files)
- **webui/frontend/**: JavaScript code (scanned with ESLint separately)
- **venv/, node_modules/, __pycache__/**: Build artifacts

### Common Findings

#### False Positives

These are typically safe in the Mothbox context:

- **B404/B603**: subprocess imports and usage - Required for camera control, GPIO, system administration
- **B103**: chmod 0o755 - Standard directory permissions for photo storage
- **B104**: Bind 0.0.0.0 - Mothbox is a local network device, secured with CSRF/CORS
- **B108**: /tmp usage - Temporary files for system configuration

#### Genuine Security Issues

Always investigate these carefully:

- **B201-B202**: Flask debug mode in production
- **B105-B106**: Hardcoded passwords or API keys
- **B501-B504**: Weak cryptography (MD5, DES, etc.)
- **B601-B602**: Parameterized SQL queries
- **B608**: SQL injection via string formatting

### Integration with GitHub Actions

Security scanning runs automatically on:

- Push to `main`, `dev`, or `feature/**` branches
- Pull requests to `main` or `dev`
- Manual workflow dispatch

View results:

1. **GitHub Actions**: Check the "Security Scan (Bandit)" job
2. **Artifacts**: Download `bandit-security-report` JSON for detailed analysis
3. **PR Comments**: Failed checks will block merging

### Security Scanning Roadmap

See Issue #79 for the complete security scanning roadmap:

- ✅ **Phase 1**: Bandit Python security scanner (this document)
- ⏳ **Phase 2**: npm audit for frontend dependency scanning
- ⏳ **Phase 3**: Enhanced linting (Black, ESLint)

### Resources

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [CWE Database](https://cwe.mitre.org/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Issue #79: Security Scanning and Linting](https://github.com/Digital-Naturalism-Laboratories/Mothbox/issues/79)

### Questions?

For questions about security scanning, see:

- Issue #79 for implementation discussion
- `.github/workflows/test.yml` for CI/CD configuration
- `Firmware/pyproject.toml` for Bandit configuration
