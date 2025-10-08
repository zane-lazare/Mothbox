# Mothbox Web UI

A modern web interface for controlling and monitoring your Mothbox camera trap system.

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

## Production Deployment

1. Build the React frontend:
```bash
cd Firmware/webui/frontend
npm run build
```

2. Run the Flask backend (serves both API and built React app):
```bash
cd Firmware/webui/backend
python app.py
```

Access the full application at `http://localhost:5000`

## API Endpoints

### System
- `GET /api/system/status` - Get system status (CPU temp, disk space, etc.)
- `GET /api/system/power` - Get power metrics from INA260

### Camera
- `POST /api/camera/capture` - Trigger photo capture
- `GET /api/camera/settings` - Get camera settings
- `POST /api/camera/settings` - Update camera settings

### Gallery
- `GET /api/gallery/photos` - List all photos
- `GET /api/gallery/photo/<path>` - Get full-size photo
- `GET /api/gallery/thumbnail/<path>` - Get photo thumbnail

### Config
- `GET /api/config/controls` - Get controls.txt configuration
- `POST /api/config/controls` - Update controls.txt
- `GET /api/config/schedule` - Get schedule settings
- `POST /api/config/schedule` - Update schedule settings

### GPIO
- `GET /api/gpio/status` - Get GPIO pin states
- `POST /api/gpio/control` - Control GPIO relay (on/off)
- `POST /api/gpio/flash` - Trigger flash momentarily

### Scheduler
- `GET /api/scheduler/jobs` - List cron jobs
- `POST /api/scheduler/job` - Add cron job
- `DELETE /api/scheduler/job` - Delete cron job
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
