# API Key Authentication

This guide explains how to configure and use API key authentication for programmatic access to the Mothbox sidecar and deployment metadata APIs.

## Overview

The Mothbox API supports two authentication methods:

1. **CSRF tokens** (default for web UI) - Automatically handled by the browser
2. **API keys** - For programmatic/scripted access via `X-API-Key` header

Both methods are accepted on state-changing endpoints (POST, PATCH, DELETE). GET endpoints are read-only and don't require authentication.

## Configuration

### Recommended: Environment Variable (Most Secure)

Set the `MOTHBOX_API_KEY` environment variable:

```bash
# For a single session
export MOTHBOX_API_KEY="your-secret-key-here"

# For persistent use, add to ~/.bashrc or ~/.profile
echo 'export MOTHBOX_API_KEY="your-secret-key-here"' >> ~/.bashrc

# For systemd service, add to the unit file
Environment="MOTHBOX_API_KEY=your-secret-key-here"
```

### Alternative: controls.txt (Device-Local)

Add to your device's `controls.txt` file:

```
api_key=your-secret-key-here
```

**Warning**: Do not commit `controls.txt` to git if it contains an API key. The template files in the repository do not contain API keys.

### Priority Order

1. `MOTHBOX_API_KEY` environment variable (checked first)
2. `api_key` entry in controls.txt (fallback)

## Using the API Key

Include the API key in the `X-API-Key` header:

```bash
# Update photo metadata
curl -X PATCH "http://mothbox.local:5000/api/sidecar/photos/photo.jpg" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{"tags": ["moth", "night"], "species": "Actias luna"}'

# Delete photo metadata
curl -X DELETE "http://mothbox.local:5000/api/sidecar/photos/photo.jpg" \
  -H "X-API-Key: your-secret-key-here"

# Bulk update
curl -X POST "http://mothbox.local:5000/api/sidecar/bulk" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{"filenames": ["photo1.jpg", "photo2.jpg"], "updates": {"tags": ["batch"]}}'
```

## Python Example

```python
import requests

API_KEY = "your-secret-key-here"
BASE_URL = "http://mothbox.local:5000/api/sidecar"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Update photo metadata
response = requests.patch(
    f"{BASE_URL}/photos/photo.jpg",
    headers=headers,
    json={"tags": ["moth"], "species": "Actias luna"}
)
print(response.json())
```

## Protected Endpoints

The following endpoints require authentication (CSRF or API key):

### Sidecar Metadata API (`/api/sidecar`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/photos/<filename>` | Update photo metadata |
| DELETE | `/photos/<filename>` | Delete photo sidecar |
| POST | `/bulk` | Bulk update metadata |

### Deployment Metadata API (`/api/deployment`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/metadata/<directory>` | Update deployment metadata |
| DELETE | `/metadata/<directory>` | Delete deployment sidecar |
| POST | `/batch` | Batch update deployments |
| POST | `/generate` | Generate sidecars for subdirectories |
| POST | `/cache/invalidate` | Invalidate deployment cache |

## Security Considerations

1. **Use environment variables for production** - They're never stored in version control
2. **Generate strong keys** - Use at least 32 random characters
3. **Keep keys secret** - Never log or display API keys
4. **Rotate keys periodically** - Change keys if they may have been compromised
5. **Use HTTPS in production** - API keys are transmitted in headers

### Generating a Secure Key

```bash
# Linux/macOS
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using openssl
openssl rand -base64 32
```

## Backwards Compatibility

If no API key is configured:
- All requests are allowed (backwards compatible behavior)
- This is the default state for existing installations

To enable API key authentication, simply configure a key using one of the methods above.

## Error Responses

| Status | Description |
|--------|-------------|
| 200 | Success |
| 401 | Authentication required (no valid CSRF or API key) |
| 403 | Forbidden (path traversal or invalid input) |
| 500 | Internal server error |

Error messages are intentionally generic to prevent information disclosure about the authentication mechanism.

## Troubleshooting

### "Authentication required" error

1. Verify the API key is set correctly:
   ```bash
   echo $MOTHBOX_API_KEY  # Check environment variable
   ```

2. Verify the header is being sent:
   ```bash
   curl -v -H "X-API-Key: your-key" ...  # -v for verbose output
   ```

3. Check the key matches exactly (no extra spaces or newlines)

### Key not being recognized

1. Environment variable takes precedence - check if it's set
2. Restart the Flask server after changing controls.txt
3. Verify controls.txt format: `api_key=value` (no spaces around `=`)

## Related Documentation

- [Sidecar Metadata API](dev/api/sidecar.md)
- [Deployment Metadata API](dev/api/deployment.md)
- [Security Best Practices](../SECURITY.md)
