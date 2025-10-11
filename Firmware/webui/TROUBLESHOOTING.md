# Mothbox Web UI Troubleshooting Guide

This guide helps diagnose and fix common issues with the Mothbox Web UI.

## Table of Contents
- [WebSocket Connection Errors](#websocket-connection-errors)
- [GPIO Control Failures (400 Errors)](#gpio-control-failures-400-errors)
- [CSRF Token Issues](#csrf-token-issues)
- [Service Not Starting](#service-not-starting)
- [Permission Errors](#permission-errors)

---

## WebSocket Connection Errors

### Symptom
```
http://192.168.1.197:5000 is not an accepted origin
192.168.1.106 - - [date] "GET /socket.io/?EIO=4&transport=websocket HTTP/1.1" 400 -
```

### Cause
The Web UI service is running in production mode (default) which only allows same-origin WebSocket connections. When accessing from:
- A development server (different port)
- A different device on the network
- A different hostname/IP

...the connection is blocked by CORS policy.

### Solution 1: Configure CORS for Local Network Access

Edit the systemd service file to allow connections from your local network:

```bash
sudo nano /etc/systemd/system/mothbox-webui.service
```

Find the line:
```
Environment="ALLOWED_ORIGINS="
```

Change it to:
```
Environment="ALLOWED_ORIGINS=http://localhost:*,http://127.0.0.1:*,http://192.168.*.*:*,http://10.*.*.*:*"
```

Then restart the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mothbox-webui
```

### Solution 2: Access from Same Origin

Access the Web UI directly from the Mothbox IP address instead of a development server:
```
http://<mothbox-ip>:5000
```

Instead of:
```
http://localhost:5173  (Vite dev server)
```

### Verify Fix

Check the logs to confirm connections are now accepted:
```bash
sudo journalctl -u mothbox-webui -f
```

You should see:
```
✓ Client connected from <ip>
```

Instead of:
```
⚠ WebSocket connection rejected from unauthorized origin
```

---

## GPIO Control Failures (400 Errors)

### Symptom
```
192.168.1.106 - - [date] "POST /api/gpio/control HTTP/1.1" 400 -
```

GPIO control buttons don't work, always return 400 Bad Request.

### Cause
The Web UI requires CSRF tokens for all POST/PUT/DELETE/PATCH requests to prevent cross-site request forgery attacks.

### Solution: Ensure Frontend Fetches CSRF Token

If using the built-in React frontend, this is handled automatically. If you're making manual API calls:

```javascript
// 1. Fetch CSRF token first
const tokenResponse = await fetch('http://<mothbox-ip>:5000/api/csrf-token');
const { csrf_token } = await tokenResponse.json();

// 2. Include token in POST requests
const response = await fetch('http://<mothbox-ip>:5000/api/gpio/control', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token  // Include token here
  },
  body: JSON.stringify({
    relay: 'Relay_Ch1',
    state: true
  })
});
```

### Additional Causes

**Missing `relay` or `state` parameter:**
```javascript
// ✗ Wrong - missing parameters
{ state: true }

// ✓ Correct - both parameters required
{ relay: 'Relay_Ch1', state: true }
```

**Invalid relay name:**
```javascript
// ✗ Wrong - invalid relay
{ relay: 'Relay1', state: true }

// ✓ Correct - valid relay names
{ relay: 'Relay_Ch1', state: true }  // or Relay_Ch2, Relay_Ch3
```

**State not a boolean:**
```javascript
// ✗ Wrong - string instead of boolean
{ relay: 'Relay_Ch1', state: 'true' }

// ✓ Correct - boolean value
{ relay: 'Relay_Ch1', state: true }
```

---

## CSRF Token Issues

### Symptom
```
{"error": "CSRF validation failed", "message": "..."}
```

### Solutions

**1. Cookie Issues:**
CSRF tokens are stored in cookies. Ensure your browser accepts cookies from the Mothbox domain.

**2. Cross-Origin Requests:**
If making requests from a different origin, ensure:
- `ALLOWED_ORIGINS` is configured (see WebSocket section)
- Credentials are included in fetch:
```javascript
fetch(url, {
  credentials: 'include',  // Include cookies
  headers: { 'X-CSRFToken': token }
})
```

**3. Token Expiration:**
CSRF tokens don't expire in the Web UI (configured for single-user devices), but if you clear cookies, fetch a new token.

---

## Service Not Starting

### Check Service Status
```bash
sudo systemctl status mothbox-webui
```

### View Detailed Logs
```bash
sudo journalctl -u mothbox-webui -n 50
```

### Common Issues

**1. Python Dependencies Missing:**
```bash
cd ~/Mothbox/webui/backend
pip3 install --break-system-packages -r requirements.txt
```

**2. Frontend Not Built:**
```bash
cd ~/Mothbox/webui/frontend
npm install
npm run build
```

**3. Port Already in Use:**
Check if another service is using port 5000:
```bash
sudo lsof -i :5000
```

**4. Invalid MOTHBOX_HOME Path:**
Check the service file has the correct path:
```bash
grep "MOTHBOX_HOME" /etc/systemd/system/mothbox-webui.service
```

---

## Permission Errors

### Symptom
```
GPIO permission denied
PermissionError: [Errno 13] Permission denied: '/dev/gpiomem'
```

### Solution 1: Add User to GPIO Group
```bash
sudo usermod -a -G gpio $USER
```

Then either:
- **Option A:** Restart the service (recommended):
```bash
sudo systemctl restart mothbox-webui
```

- **Option B:** Log out and log back in (makes group membership active)

### Solution 2: Verify GPIO Group Exists
```bash
getent group gpio
```

If it doesn't exist:
```bash
sudo groupadd gpio
sudo usermod -a -G gpio $USER
```

### Verify Fix
```bash
groups $USER
```

Should include `gpio` in the list.

Check Web UI logs:
```bash
sudo journalctl -u mothbox-webui -f
```

Should see:
```
✓ GPIO permissions validated successfully
```

Instead of:
```
⚠️ GPIO permission denied
```

---

## Environment Configuration

### Check Current Configuration
```bash
sudo systemctl cat mothbox-webui
```

Look for these environment variables:
```
Environment="MOTHBOX_ENV=production"
Environment="ALLOWED_ORIGINS=..."
```

### Change Environment Mode

**Development (permissive CORS, debug logging):**
```bash
sudo nano /etc/systemd/system/mothbox-webui.service
```

Change:
```
Environment="MOTHBOX_ENV=development"
Environment="ALLOWED_ORIGINS=http://localhost:*,http://127.0.0.1:*,http://192.168.*.*:*"
```

**Production (strict CORS, minimal logging):**
```
Environment="MOTHBOX_ENV=production"
Environment="ALLOWED_ORIGINS="
```

**Apply changes:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart mothbox-webui
```

---

## Diagnostic Commands

### Check Service is Running
```bash
sudo systemctl is-active mothbox-webui
```

### View Live Logs
```bash
sudo journalctl -u mothbox-webui -f
```

### Check Network Binding
```bash
sudo lsof -i :5000
```

Should show Python binding to `0.0.0.0:5000`

### Test API Endpoint
```bash
curl http://localhost:5000/api/system/status
```

Should return JSON with system information.

### Test GPIO Without CSRF (expect failure)
```bash
curl -X POST http://localhost:5000/api/gpio/control \
  -H "Content-Type: application/json" \
  -d '{"relay": "Relay_Ch1", "state": true}'
```

Should return:
```json
{"error": "CSRF validation failed"}
```

---

## Getting Help

If you're still experiencing issues:

1. **Gather diagnostic information:**
   ```bash
   sudo systemctl status mothbox-webui
   sudo journalctl -u mothbox-webui -n 100 > ~/mothbox-webui-logs.txt
   ```

2. **Check GitHub issues:**
   https://github.com/Digital-Naturalism-Laboratories/Mothbox/issues

3. **Create a new issue with:**
   - Description of the problem
   - Steps to reproduce
   - Relevant log output
   - Your configuration (MOTHBOX_ENV, ALLOWED_ORIGINS)
   - Mothbox version/commit hash

---

## Quick Reference

### Restart Service
```bash
sudo systemctl restart mothbox-webui
```

### View Logs
```bash
sudo journalctl -u mothbox-webui -f
```

### Edit Configuration
```bash
sudo nano /etc/systemd/system/mothbox-webui.service
sudo systemctl daemon-reload
sudo systemctl restart mothbox-webui
```

### Check GPIO Permissions
```bash
groups $USER
ls -l /dev/gpiomem
```

### Test API Connection
```bash
curl http://localhost:5000/api/csrf-token
```
