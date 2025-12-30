# Mothbox Logging Guide

This guide explains how to configure and use the Mothbox logging system for diagnostics, troubleshooting, and monitoring.

## Overview

The Mothbox uses Python's standard `logging` module with centralized configuration. Logs are written to both the console (with colored output) and rotating log files.

## Configuration

Logging is configured via `controls.txt`:

```ini
# Log level for application logging (default: INFO)
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level=INFO

# Number of days to retain log files (default: 7)
log_retention_days=7
```

### Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `DEBUG` | Verbose output with all details | Troubleshooting specific issues |
| `INFO` | Normal operation messages | Production monitoring (recommended) |
| `WARNING` | Potential issues that don't stop operation | Reviewing operational health |
| `ERROR` | Errors that affect functionality | Diagnosing failures |
| `CRITICAL` | Critical failures requiring immediate attention | Emergency alerts |

### Changing Log Level

1. Edit `controls.txt` and set `log_level=DEBUG` (or desired level)
2. Restart the Mothbox web UI service
3. The new level takes effect immediately

For temporary debugging without editing files:
```bash
# View current log level
grep log_level /path/to/controls.txt

# Set DEBUG level for troubleshooting
sed -i 's/log_level=.*/log_level=DEBUG/' /path/to/controls.txt
```

## Log File Location

Log files are stored in `DATA_DIR/logs/`:

- **Production**: `/var/lib/mothbox/logs/mothbox.log`
- **Legacy**: `/home/pi/Desktop/Mothbox/logs/mothbox.log`
- **Development**: `<repo>/logs/mothbox.log`

### Log Rotation

- Logs rotate when they reach **5MB**
- Up to **5 backup files** are kept (mothbox.log.1, .2, etc.)
- Oldest logs are automatically deleted

## Viewing Logs

### Real-time Log Viewing

```bash
# Follow logs in real-time
tail -f /var/lib/mothbox/logs/mothbox.log

# With colored output (if coloredlogs installed)
tail -f /var/lib/mothbox/logs/mothbox.log | ccze -A
```

### Filtering Logs

```bash
# Show only errors
grep ERROR /var/lib/mothbox/logs/mothbox.log

# Show only camera-related logs
grep "routes.camera" /var/lib/mothbox/logs/mothbox.log

# Show logs from the last hour
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" /var/lib/mothbox/logs/mothbox.log
```

### Log Format

Each log entry follows this format:
```
YYYY-MM-DD HH:MM:SS - module.name - LEVEL - Message
```

Example:
```
2024-01-15 14:23:45 - routes.camera - INFO - Camera initialized
2024-01-15 14:23:46 - routes.camera - DEBUG - Applied settings: exposure=1000
2024-01-15 14:23:50 - routes.camera - WARNING - Camera busy, waiting for release
2024-01-15 14:24:01 - routes.camera - ERROR - Photo capture failed: timeout
```

## Troubleshooting

### Enable Debug Logging

For detailed troubleshooting:

1. Set `log_level=DEBUG` in controls.txt
2. Restart services
3. Reproduce the issue
4. Review logs for detailed information
5. Set `log_level=INFO` when done (to reduce disk usage)

### Common Issues

#### Logs not appearing
- Check that the logs directory exists and is writable
- Verify `log_level` is set correctly in controls.txt
- Ensure the service has restarted after config changes

#### Disk space issues
- Reduce `log_retention_days` to keep fewer logs
- Set `log_level=WARNING` to reduce log volume
- Manually delete old log files: `rm /var/lib/mothbox/logs/mothbox.log.*`

#### Finding specific errors
```bash
# Find all errors in the last 24 hours
find /var/lib/mothbox/logs -mtime -1 -exec grep -l ERROR {} \;

# Count errors by module
grep ERROR /var/lib/mothbox/logs/mothbox.log | cut -d'-' -f3 | sort | uniq -c
```

## For Developers

### Using the Logger

```python
import logging
logger = logging.getLogger(__name__)

# Log at different levels
logger.debug("Verbose detail for troubleshooting")
logger.info("Normal operation status")
logger.warning("Potential issue detected")
logger.error("Operation failed")

# Log exceptions with traceback
try:
    risky_operation()
except Exception:
    logger.exception("Error during risky operation")
```

### Best Practices

1. **Use appropriate levels**: DEBUG for verbose details, INFO for normal operations
2. **Include context**: Log relevant variables and state
3. **Use lazy formatting**: `logger.info("Value: %s", value)` instead of f-strings for performance
4. **Avoid sensitive data**: Never log passwords, API keys, or personal information
5. **Keep messages concise**: One line per log entry when possible

### Testing with Logs

```bash
# Run tests with logging output visible
pytest -v -s --log-cli-level=DEBUG Tests/unit/test_camera_routes.py
```

## Console Output

During development, logs are displayed in the console with colored output:

- **DEBUG**: Cyan
- **INFO**: Green
- **WARNING**: Yellow (bold)
- **ERROR**: Red (bold)
- **CRITICAL**: Red on white background

This requires the `coloredlogs` package (automatically installed with requirements).

---

**Last Updated**: 2024-01-15
**Related Issues**: #37
