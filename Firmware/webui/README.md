# Mothbox Web UI

A modern web interface for controlling and monitoring your Mothbox camera trap system.

📚 **Having issues?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems and solutions.

## ⚠️ IMPORTANT SECURITY NOTICE ⚠️

**The Web UI currently has NO AUTHENTICATION and binds to all network interfaces (0.0.0.0) by default.**

This means anyone with network access to your Mothbox can:
- View and download all captured photos
- Control GPIO relays (attract lights, flash, UV lights)
- Modify system configuration and camera settings
- Trigger camera captures
- Manage scheduled tasks

**Only use this Web UI on trusted, private networks** (e.g., home network, isolated field network). Do NOT expose it to the public internet without additional security measures.

**Planned security improvements** (tracked in [issue #19](https://github.com/zane-lazare/Mothbox/issues/19)):
- User authentication system
- Configurable network binding (e.g., localhost-only mode)
- Production-grade WSGI server (gunicorn/uwsgi)
- Rate limiting and request throttling

**Current security features:**
- ✅ CSRF protection on all state-changing endpoints
- ✅ Input validation to prevent injection attacks
- ✅ Path traversal protection for file access
- ✅ CORS configuration for WebSocket/API origin validation

## Features

- **Dashboard**: Real-time system status, CPU temperature, disk space, and photo count
- **Photo Gallery**: Browse and view captured photos with thumbnails and lightbox
- **Camera Control**: Manual photo capture with live WebSocket preview (~10 FPS)
- **GPIO Controls**: Direct control of attract lights, flash, and UV lights
- **Scheduler**: Visual cron job management for automated captures
- **Settings**: Edit camera settings and hardware configuration

## Tech Stack

### Backend
- Flask 3.0
- Flask-SocketIO for WebSocket support
- Integration with existing Mothbox Python scripts

### Frontend
- React 18
- Vite for fast development and builds
- Tailwind CSS for styling
- React Router for navigation
- TanStack Query for data fetching
- Socket.io-client for real-time updates

## Installation

### Backend Setup

1. Navigate to the backend directory:
```bash
cd Firmware/webui/backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Flask server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd Firmware/webui/frontend
```

2. Install npm dependencies:
```bash
npm install
```

3. Create a `.env` file (optional):
```bash
VITE_API_URL=http://localhost:5000/api
```

4. Run the development server:
```bash
npm run dev
```

The UI will be available at `http://localhost:5173`

5. Build for production:
```bash
npm run build
```

The built files will be in `dist/` and can be served by Flask.

## Environment Configuration

The Web UI supports two environment modes controlled by the `MOTHBOX_ENV` environment variable:

### Development Mode
```bash
export MOTHBOX_ENV=development
python app.py
```

Features:
- Debug mode enabled
- Verbose logging
- Werkzeug development server (acceptable for local development)
- Fast iteration for testing

### Production Mode (Default)
```bash
export MOTHBOX_ENV=production  # or omit, production is default
python app.py
```

Features:
- Debug mode disabled
- Minimal logging
- Security warnings displayed
- Currently uses Werkzeug with warning (gunicorn coming in issue #19)

⚠️ **Security Notice**: The Web UI has no authentication and binds to all network interfaces (0.0.0.0). Only use on trusted local networks. Production-grade security (gunicorn, authentication, network binding options) is tracked in [issue #19](https://github.com/zane-lazare/Mothbox/issues/19).

## Production Deployment

### Current Method (Systemd Service)

The installer sets up a systemd service that runs in production mode:

```bash
sudo systemctl status mothbox-webui
sudo systemctl restart mothbox-webui
sudo journalctl -u mothbox-webui -f
```

The service automatically:
- Runs in production mode (`MOTHBOX_ENV=production`)
- Starts on boot
- Restarts on failure
- Logs to systemd journal

### Manual Production Build

1. Build the React frontend:
```bash
cd Firmware/webui/frontend
npm run build
```

2. Run the Flask backend (serves both API and built React app):
```bash
cd Firmware/webui/backend
export MOTHBOX_ENV=production
python app.py
```

Access the full application at `http://localhost:5000`

### Future Production Deployment

Full production deployment with gunicorn, authentication, and configurable network binding is being implemented in [issue #19](https://github.com/zane-lazare/Mothbox/issues/19).

## API Endpoints

### Authentication & CSRF

**IMPORTANT:** All POST/PUT/DELETE/PATCH endpoints require a CSRF token to prevent cross-site request forgery attacks.

#### Getting a CSRF Token
```javascript
// Fetch CSRF token first
const response = await fetch('/api/csrf-token');
const { csrf_token } = await response.json();

// Include token in subsequent POST requests
await fetch('/api/gpio/control', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token
  },
  body: JSON.stringify({ relay: 'Relay_Ch1', state: true })
});
```

**Error responses without CSRF token:**
- `400 Bad Request` - CSRF token missing or invalid
- Response body: `{"error": "CSRF validation failed"}`

### System
- `GET /api/system/status` - Get system status (CPU temp, disk space, etc.)
- `GET /api/system/power` - Get power metrics from INA260

### Camera
- `POST /api/camera/capture` - Trigger photo capture (automatically uses HDR if configured) **[Requires CSRF]**
- `GET /api/camera/settings` - Get camera settings
- `POST /api/camera/settings` - Update camera settings **[Requires CSRF]**
- `POST /api/camera/autofocus` - Trigger autofocus cycle **[Requires CSRF]**
- `POST /api/camera/calibrate` - Auto-calibrate camera settings **[Requires CSRF]**

#### HDR (High Dynamic Range) Mode

HDR mode captures multiple exposures with automatic exposure bracketing for enhanced dynamic range. When enabled, captures use `TakePhoto_HDR.py` instead of `TakePhoto.py`.

**Configuration:**
- Set `HDR` in camera_settings.csv to number of exposures: `1` (off), `3`, `5`, or `7`
- Set `HDR_width` to bracket step size in microseconds (default: 7000µs = 7ms)
- View current HDR status in the Camera page (shows purple badge when active)

**Example:**
```csv
SETTING,VALUE,DETAILS
HDR,5,Number of bracketed exposures
HDR_width,7000,Bracket step size in microseconds
```

**Capture Response:**
```json
{
  "success": true,
  "hdr_mode": true,
  "hdr_count": 5,
  "hdr_width": 7000,
  "script_used": "TakePhoto_HDR.py",
  "message": "HDR capture complete: 5 exposures with 7000µs bracket width",
  "latest_photo": "2025-01-15/IMG_001.jpg"
}
```

**Web UI Indicators:**
- Camera page shows HDR status indicator with current configuration
- Capture success toast displays HDR details (e.g., "HDR capture complete: 5 exposures with 7000µs bracket width")

### Gallery
- `GET /api/gallery/photos` - List all photos
- `GET /api/gallery/photo/<path>` - Get full-size photo
- `GET /api/gallery/thumbnail/<path>` - Get photo thumbnail

### Config
- `GET /api/config/controls` - Get controls.txt configuration
- `POST /api/config/controls` - Update controls.txt **[Requires CSRF]**
- `GET /api/config/schedule` - Get schedule settings
- `POST /api/config/schedule` - Update schedule settings **[Requires CSRF]**

### GPIO
- `GET /api/gpio/status` - Get GPIO pin states
- `POST /api/gpio/control` - Control GPIO relay (on/off) **[Requires CSRF]**
- `POST /api/gpio/flash` - Trigger flash momentarily **[Requires CSRF]**

### Scheduler
- `GET /api/scheduler/jobs` - List cron jobs
- `POST /api/scheduler/job` - Add cron job **[Requires CSRF]**
- `DELETE /api/scheduler/job` - Delete cron job **[Requires CSRF]**
- `GET /api/scheduler/status` - Get scheduler status

## Development

### Backend Development
The backend integrates with Mothbox's existing Python infrastructure using the `mothbox_paths` module for path configuration.

### Frontend Development
- Uses Vite's hot module replacement for fast development
- Tailwind CSS for responsive, modern UI
- React Query for efficient data fetching and caching

## Roadmap

- [ ] WebSocket live camera preview
- [ ] User authentication
- [ ] Photo filtering and search
- [ ] Batch photo operations
- [ ] Export/backup functionality
- [ ] Mobile-responsive optimizations
- [ ] Dark mode support

## Contributing

This web UI is part of the Mothbox project. See the main project README for contribution guidelines.

## License

Same as the main Mothbox project.
