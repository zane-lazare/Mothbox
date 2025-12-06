#!/usr/bin/env python3
"""
Mothbox Web UI Backend
Flask API server for Mothbox control and monitoring
"""

import atexit
import logging
import signal
import sys
from pathlib import Path

# Load configuration based on environment
from config import get_config
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFError, CSRFProtect

config = get_config()

# Reduce Werkzeug request logging verbosity
# Only show warnings and errors, not every request
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Setup path to import mothbox modules
# mothbox_paths.py is in the Firmware root directory, three levels up from this file
# This works for all installation types: production (/opt/mothbox), legacy, custom, and dev
backend_dir = Path(__file__).resolve().parent
webui_dir = backend_dir.parent
firmware_root = webui_dir.parent  # backend -> webui -> Firmware (or /opt/mothbox)
sys.path.insert(0, str(firmware_root))

app = Flask(__name__, static_folder="../frontend/dist")

# Apply configuration
app.config.from_object(config)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Debug: Log CSRF configuration
print("✓ CSRF Protection initialized")
print(f"  WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED')}")
print(f"  WTF_CSRF_HEADERS: {app.config.get('WTF_CSRF_HEADERS')}")
print(f"  SECRET_KEY set: {bool(app.config.get('SECRET_KEY'))}")

# Initialize rate limiter to prevent hardware abuse
# Uses remote address for rate limiting (single user device typically has same IP)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Configure CORS for cross-origin requests
# Use restrictive origins from config (empty list = same-origin only in production)
if config.CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    print(f"✓ CORS enabled for origins: {config.CORS_ORIGINS}")
else:
    # No CORS configured - same-origin only (most secure for production)
    print("✓ CORS: Same-origin only (no cross-origin requests allowed)")

# Configure SocketIO with proper CORS and transport settings
# WebSocket connections are exempt from CSRF by Flask-WTF
# Use same CORS origins as REST API for consistency
# Production (no CORS_ORIGINS): empty list = reject all cross-origin connections
# Development (CORS_ORIGINS set): allow configured origins
socketio = SocketIO(
    app,
    cors_allowed_origins=config.CORS_ORIGINS if config.CORS_ORIGINS else [],
    async_mode="threading",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# Initialize live view streamer
from liveview_stream import LiveViewStreamer

camera_streamer = LiveViewStreamer(socketio)

# Register cleanup handlers to ensure camera resources are released
# Uses both atexit and signal handlers for defense in depth
atexit.register(camera_streamer.cleanup)
print("✓ Registered atexit cleanup handler for camera")


def _signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT gracefully"""
    signame = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    print(f"\n{signame} received - cleaning up camera resources...")
    camera_streamer.cleanup()
    print("Cleanup complete, exiting")
    sys.exit(0)


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)
print("✓ Registered signal handlers for graceful shutdown")

# Initialize thumbnail cache
from services.thumbnail_cache import ThumbnailCache

from mothbox_paths import PHOTOS_DIR, THUMBNAIL_CACHE_DIR

try:
    # TODO: Read configuration from controls.txt (max_size_mb, sizes)
    # For now, use defaults: max_size_mb=500, sizes=[64, 128, 256]
    thumbnail_cache = ThumbnailCache(
        cache_dir=THUMBNAIL_CACHE_DIR,
        max_size_mb=500,
        sizes=[64, 128, 256]
    )
    app.config['THUMBNAIL_CACHE'] = thumbnail_cache

    # Register cleanup handler to flush statistics on shutdown
    atexit.register(thumbnail_cache.close)
    print(f"✓ Thumbnail cache initialized: {THUMBNAIL_CACHE_DIR}")
    print("✓ Registered thumbnail cache cleanup handler")
except Exception as e:
    print(f"⚠️  Failed to initialize thumbnail cache: {e}")
    app.config['THUMBNAIL_CACHE'] = None
    thumbnail_cache = None

# Initialize cache warmer (Issue #134 - Phase 3)
from services.cache_warmer import CacheWarmer

if thumbnail_cache:
    try:
        cache_warmer = CacheWarmer(
            thumbnail_cache=thumbnail_cache,
            photos_dir=PHOTOS_DIR
        )
        app.config['CACHE_WARMER'] = cache_warmer

        # Warm recent photos on startup (non-blocking)
        cache_warmer.warm_recent(count=50, background=True)

        # Start background monitoring for auto-warming
        cache_warmer.start_background_warming()

        # Register cleanup handler for cache warmer
        atexit.register(cache_warmer.stop_background_warming)
        print("✓ Cache warmer initialized and startup warming triggered")
        print("✓ Registered cache warmer cleanup handler")

    except Exception as e:
        print(f"⚠️  Failed to initialize cache warmer: {e}")
        app.config['CACHE_WARMER'] = None
else:
    app.config['CACHE_WARMER'] = None
    print("⚠️  Cache warmer not initialized (thumbnail cache unavailable)")

# Initialize services using lazy getters (avoids circular imports)
# Services are lazily initialized on first access via get_*_service() functions
from services import (
    get_clustering_service,
    get_locations_service,
    get_series_service,
    get_sidecar_service,
)
from services.search_service import SearchService

try:
    # Pre-initialize services and store in app.config for routes that need direct access
    app.config['SERIES_SERVICE'] = get_series_service()
    print("✓ Series service initialized")
except Exception as e:
    print(f"⚠️  Failed to initialize series service: {e}")
    app.config['SERIES_SERVICE'] = None

try:
    app.config['CLUSTERING_SERVICE'] = get_clustering_service()
    print("✓ Clustering service initialized")
except Exception as e:
    print(f"⚠️  Failed to initialize clustering service: {e}")
    app.config['CLUSTERING_SERVICE'] = None

try:
    app.config['LOCATIONS_SERVICE'] = get_locations_service()
    print("✓ Locations service initialized")
except Exception as e:
    print(f"⚠️  Failed to initialize locations service: {e}")
    app.config['LOCATIONS_SERVICE'] = None

try:
    app.config['SIDECAR_SERVICE'] = get_sidecar_service()
    print("✓ Sidecar service initialized")
except Exception as e:
    print(f"⚠️  Failed to initialize sidecar service: {e}")
    app.config['SIDECAR_SERVICE'] = None

# Initialize search service (Issue #131)
try:
    app.config['SEARCH_SERVICE'] = SearchService()
    print("✓ Search service initialized")
except Exception as e:
    print(f"⚠️  Failed to initialize search service: {e}")
    app.config['SEARCH_SERVICE'] = None

# Initialize tag autocomplete engine (Issue #124)
from webui.backend.lib.tag_autocomplete import TagAutocompleteEngine

try:
    sidecar_service = app.config.get('SIDECAR_SERVICE')
    if sidecar_service:
        app.config['TAG_AUTOCOMPLETE_ENGINE'] = TagAutocompleteEngine(
            sidecar_service=sidecar_service,
            cache_ttl=300  # 5 minutes
        )
        print("✓ Tag autocomplete engine initialized")
    else:
        app.config['TAG_AUTOCOMPLETE_ENGINE'] = None
        print("⚠️  Tag autocomplete engine not initialized (sidecar service unavailable)")
except Exception as e:
    print(f"⚠️  Failed to initialize tag autocomplete engine: {e}")
    app.config['TAG_AUTOCOMPLETE_ENGINE'] = None

# Import route blueprints
from routes.camera import camera_bp
from routes.config import config_bp
from routes.gallery import gallery_bp
from routes.gpio import gpio_bp
from routes.gps import gps_bp
from routes.metadata import metadata_bp
from routes.preferences import preferences_bp
from routes.presets import presets_bp
from routes.scheduler import scheduler_bp
from routes.search import search_bp
from routes.sidecar import sidecar_bp
from routes.system import system_bp

# Make camera_streamer accessible to routes via app config
app.config["CAMERA_STREAMER"] = camera_streamer

# Register blueprints
app.register_blueprint(system_bp, url_prefix="/api/system")
app.register_blueprint(camera_bp, url_prefix="/api/camera")
app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
app.register_blueprint(config_bp, url_prefix="/api/config")
app.register_blueprint(gpio_bp, url_prefix="/api/gpio")
app.register_blueprint(scheduler_bp, url_prefix="/api/scheduler")
app.register_blueprint(presets_bp, url_prefix="/api/presets")
app.register_blueprint(preferences_bp, url_prefix="/api/preferences")
app.register_blueprint(gps_bp, url_prefix="/api/gps")
app.register_blueprint(metadata_bp, url_prefix="/api/metadata")
app.register_blueprint(sidecar_bp, url_prefix="/api/sidecar")
app.register_blueprint(search_bp)  # Note: search_bp already includes /api/photos/search prefix

# Register WebSocket handlers
from websocket_handlers import register_handlers

register_handlers(socketio, camera_streamer)
print("✓ Registered WebSocket event handlers")

# Apply rate limiting to hardware endpoints to prevent abuse
# Camera: 10 requests per minute for capture operations (prevents rapid captures)
# GPIO: 30 requests per minute for control operations (one per 2 seconds)
# GPIO: 10 requests per minute for flash operations (prevents rapid relay cycling)
# GPS: 5 requests per minute for sync operations (GPS takes time to acquire fix)
# Use app.view_functions with blueprint-prefixed endpoint names
limiter.limit("10 per minute")(app.view_functions["camera.capture_photo"])
limiter.limit("30 per minute")(app.view_functions["gpio.control_gpio"])
limiter.limit("10 per minute")(app.view_functions["gpio.trigger_flash"])
limiter.limit("5 per minute")(app.view_functions["gps.sync_gps"])

# Exempt read-only endpoints that use caching from rate limiting
limiter.exempt(app.view_functions["gps.get_gps_status"])
limiter.exempt(app.view_functions["gallery.get_thumbnail"])
limiter.exempt(app.view_functions["gallery.get_photo"])
limiter.exempt(app.view_functions["sidecar.get_photo_metadata"])

print("✓ Rate limiting applied to camera, GPIO, and GPS endpoints")

# Sidecar API rate limiting (Issue #107 follow-up)
# Bulk: 10 per minute (prevents abuse of batch operations)
# PATCH/DELETE: 30 per minute (one per 2 seconds, reasonable for UI use)
limiter.limit("10 per minute")(app.view_functions["sidecar.bulk_update_metadata"])
limiter.limit("30 per minute")(app.view_functions["sidecar.update_photo_metadata"])
limiter.limit("30 per minute")(app.view_functions["sidecar.delete_photo_metadata"])

# Tag autocomplete rate limiting (Issue #124)
# 60 per minute (1 per second) - autocomplete endpoints are chatty with typing
limiter.limit("60 per minute")(app.view_functions["metadata.get_tag_autocomplete"])

print("✓ Rate limiting applied to sidecar and metadata endpoints")


# CSRF token endpoint
@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """Return CSRF token for the session"""
    from flask_wtf.csrf import generate_csrf

    return jsonify({"csrf_token": generate_csrf()})


# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF validation errors"""
    print(f"⚠️  CSRF validation failed: {e.description}")
    print(f"   Request path: {request.path}")
    print(f"   Request method: {request.method}")
    print(f"   Request headers: {dict(request.headers)}")
    print(f"   Request cookies: {list(request.cookies.keys())}")
    return jsonify({"error": "CSRF validation failed", "message": str(e.description)}), 400


# Serve React app
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and Path(app.static_folder, path).exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # Print startup banner with environment information
    print("\n" + "=" * 60)
    print("Mothbox Web UI Starting")
    print(f"Environment: {config.ENV_NAME}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Host: {config.HOST}:{config.PORT}")
    print("=" * 60)

    if config.ENV_NAME == "production":
        print("\n⚠️  WARNING: Running with Werkzeug development server")
        print("   For production deployment, use gunicorn with eventlet worker")
        print("   See issue #19: https://github.com/zane-lazare/Mothbox/issues/19")
        print("=" * 60 + "\n")

    # Block production mode until gunicorn is implemented (issue #19)
    # Production installations should run in development mode for now
    if config.ENV_NAME == "production" and not config.DEBUG:
        raise RuntimeError(
            "\n" + "=" * 60 + "\n"
            "ERROR: Production mode requires gunicorn deployment\n"
            "=" * 60 + "\n"
            "The Werkzeug development server is not safe for production use.\n"
            "\n"
            "For now, run in development mode:\n"
            "  export MOTHBOX_ENV=development\n"
            "\n"
            "Or wait for gunicorn implementation:\n"
            "  https://github.com/zane-lazare/Mothbox/issues/19\n"
            "=" * 60
        )

    # Run development server
    # Require BOTH debug mode AND development environment for werkzeug
    # This prevents accidental unsafe werkzeug in production even if DEBUG is misconfigured
    # Cleanup handled by atexit handlers registered during initialization
    socketio.run(
        app,
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        allow_unsafe_werkzeug=(config.DEBUG and config.ENV_NAME == "development"),
    )
