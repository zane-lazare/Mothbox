#!/usr/bin/env python3
"""
Mothbox Web UI Backend
Flask API server for Mothbox control and monitoring
"""

# isort: off
# Path setup must happen before webui.* imports
import sys
from pathlib import Path

# Setup path to import mothbox modules
# mothbox_paths.py is in the Firmware root directory, three levels up from this file
# This works for all installation types: production (/opt/mothbox), legacy, custom, and dev
backend_dir = Path(__file__).resolve().parent
webui_dir = backend_dir.parent
firmware_root = webui_dir.parent  # backend -> webui -> Firmware (or /opt/mothbox)
sys.path.insert(0, str(firmware_root))

# Load configuration based on environment (requires sys.path setup above)
from webui.backend.config import get_config
# isort: on

import atexit
import logging
import os
import signal

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFError, CSRFProtect

# Initialize logging early (before other imports that may use logging)
from webui.backend.logging_config import setup_mothbox_logging

logger = setup_mothbox_logging("mothbox.app")

config = get_config()

# Reduce Werkzeug request logging verbosity
# Only show warnings and errors, not every request
logging.getLogger("werkzeug").setLevel(logging.WARNING)

app = Flask(__name__, static_folder="../frontend/dist")

# Apply configuration
app.config.from_object(config)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Log CSRF configuration
logger.info("CSRF Protection initialized")
logger.debug(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED')}")
logger.debug(f"WTF_CSRF_HEADERS: {app.config.get('WTF_CSRF_HEADERS')}")
logger.debug(f"SECRET_KEY set: {bool(app.config.get('SECRET_KEY'))}")

# Initialize rate limiter to prevent hardware abuse
# Uses remote address for rate limiting (single user device typically has same IP)
# Use more generous limits in development/test environments for E2E testing
_env = os.environ.get("MOTHBOX_ENV", "production").lower()
if _env in ("development", "test"):
    _default_limits = ["10000 per day", "1000 per hour"]
    logger.info(f"Rate limiting: {_env} mode (1000/hour)")
else:
    _default_limits = ["200 per day", "50 per hour"]
    logger.info("Rate limiting: production mode (50/hour)")

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=_default_limits,
    storage_uri="memory://",
)

# Configure CORS for cross-origin requests
# Use restrictive origins from config (empty list = same-origin only in production)
if config.CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    logger.info(f"CORS enabled for origins: {config.CORS_ORIGINS}")
else:
    # No CORS configured - same-origin only (most secure for production)
    logger.info("CORS: Same-origin only (no cross-origin requests allowed)")

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
logger.info("Registered atexit cleanup handler for camera")


def _signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT gracefully"""
    signame = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.info(f"{signame} received - cleaning up camera resources...")
    camera_streamer.cleanup()
    logger.info("Cleanup complete, exiting")
    sys.exit(0)


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)
logger.info("Registered signal handlers for graceful shutdown")

# Initialize thumbnail cache
from services.thumbnail_cache import ThumbnailCache

from mothbox_paths import PHOTOS_DIR, THUMBNAIL_CACHE_DIR

try:
    # TODO: Read configuration from controls.txt (max_size_mb, sizes)
    # For now, use defaults: max_size_mb=500, sizes=[64, 128, 256]
    thumbnail_cache = ThumbnailCache(
        cache_dir=THUMBNAIL_CACHE_DIR, max_size_mb=500, sizes=[64, 128, 256]
    )
    app.config["THUMBNAIL_CACHE"] = thumbnail_cache

    # Register cleanup handler to flush statistics on shutdown
    atexit.register(thumbnail_cache.close)
    logger.info(f"Thumbnail cache initialized: {THUMBNAIL_CACHE_DIR}")
    logger.info("Registered thumbnail cache cleanup handler")
except Exception as e:
    logger.warning(f"Failed to initialize thumbnail cache: {e}")
    app.config["THUMBNAIL_CACHE"] = None
    thumbnail_cache = None

# Initialize cache warmer
from services.cache_warmer import CacheWarmer

if thumbnail_cache:
    try:
        cache_warmer = CacheWarmer(thumbnail_cache=thumbnail_cache, photos_dir=PHOTOS_DIR)
        app.config["CACHE_WARMER"] = cache_warmer

        # Warm recent photos on startup (non-blocking)
        cache_warmer.warm_recent(count=50, background=True)

        # Start background monitoring for auto-warming
        cache_warmer.start_background_warming()

        # Register cleanup handler for cache warmer
        atexit.register(cache_warmer.stop_background_warming)
        logger.info("Cache warmer initialized and startup warming triggered")
        logger.info("Registered cache warmer cleanup handler")

    except Exception as e:
        logger.warning(f"Failed to initialize cache warmer: {e}")
        app.config["CACHE_WARMER"] = None
else:
    app.config["CACHE_WARMER"] = None
    logger.warning("Cache warmer not initialized (thumbnail cache unavailable)")

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
    app.config["SERIES_SERVICE"] = get_series_service()
    logger.info("Series service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize series service: {e}")
    app.config["SERIES_SERVICE"] = None

try:
    app.config["CLUSTERING_SERVICE"] = get_clustering_service()
    logger.info("Clustering service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize clustering service: {e}")
    app.config["CLUSTERING_SERVICE"] = None

try:
    app.config["LOCATIONS_SERVICE"] = get_locations_service()
    logger.info("Locations service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize locations service: {e}")
    app.config["LOCATIONS_SERVICE"] = None

try:
    app.config["SIDECAR_SERVICE"] = get_sidecar_service()
    logger.info("Sidecar service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize sidecar service: {e}")
    app.config["SIDECAR_SERVICE"] = None

# Initialize search service
try:
    sidecar_svc = app.config.get("SIDECAR_SERVICE")
    app.config["SEARCH_SERVICE"] = SearchService(sidecar_service=sidecar_svc)
    logger.info("Search service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize search service: {e}")
    app.config["SEARCH_SERVICE"] = None

# Initialize tag autocomplete engine
from webui.backend.lib.tag_autocomplete import TagAutocompleteEngine

try:
    sidecar_service = app.config.get("SIDECAR_SERVICE")
    if sidecar_service:
        app.config["TAG_AUTOCOMPLETE_ENGINE"] = TagAutocompleteEngine(
            sidecar_service=sidecar_service,
            cache_ttl=300,  # 5 minutes
        )
        logger.info("Tag autocomplete engine initialized")
    else:
        app.config["TAG_AUTOCOMPLETE_ENGINE"] = None
        logger.warning("Tag autocomplete engine not initialized (sidecar service unavailable)")
except Exception as e:
    logger.warning(f"Failed to initialize tag autocomplete engine: {e}")
    app.config["TAG_AUTOCOMPLETE_ENGINE"] = None

# Initialize export metadata service
from webui.backend.services.export_metadata_service import ExportMetadataService

try:
    cache_ttl = app.config.get("EXPORT_CACHE_TTL", 300)
    if not isinstance(cache_ttl, int) or cache_ttl < 0:
        logger.warning("Invalid EXPORT_CACHE_TTL, using default: 300")
        cache_ttl = 300
    app.config["EXPORT_METADATA_SERVICE"] = ExportMetadataService(cache_ttl=cache_ttl)
    logger.info("Export metadata service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize export metadata service: {e}")
    app.config["EXPORT_METADATA_SERVICE"] = None

# Initialize export job service (async job queue for exports)
from webui.backend.constants import (
    EXPORT_JOB_MAX_HISTORY,
    EXPORT_JOB_TIMEOUT_SECONDS,
    EXPORT_JOB_TTL_SECONDS,
)
from webui.backend.services.export_job_service import ExportJobService

try:
    export_metadata_svc = app.config.get("EXPORT_METADATA_SERVICE")
    if export_metadata_svc:
        # Database stored in DATA_DIR for persistence across restarts
        from mothbox_paths import DATA_DIR, PHOTOS_DIR

        db_path = DATA_DIR / "export_jobs.db"
        temp_dir = DATA_DIR / "export_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        export_job_service = ExportJobService(
            db_path=db_path,
            export_service=export_metadata_svc,
            photos_dir=PHOTOS_DIR,
            temp_dir=temp_dir,
            job_timeout_seconds=EXPORT_JOB_TIMEOUT_SECONDS,
            job_ttl_seconds=EXPORT_JOB_TTL_SECONDS,
            max_history=EXPORT_JOB_MAX_HISTORY,
        )
        export_job_service.start()  # Start worker thread
        app.config["EXPORT_JOB_SERVICE"] = export_job_service
        atexit.register(export_job_service.stop)  # Cleanup on shutdown
        logger.info("Export job service initialized")
        logger.debug(f"Database: {db_path}")
        logger.debug(f"Temp dir: {temp_dir}")
    else:
        app.config["EXPORT_JOB_SERVICE"] = None
        logger.warning("Export job service not initialized (export metadata service unavailable)")
except Exception as e:
    logger.warning(f"Failed to initialize export job service: {e}")
    app.config["EXPORT_JOB_SERVICE"] = None

# Initialize deployment service
from webui.backend.services.deployment_service import DeploymentService

try:
    cache_ttl = app.config.get("DEPLOYMENT_CACHE_TTL", 300)
    if not isinstance(cache_ttl, int) or cache_ttl < 0:
        logger.warning("Invalid DEPLOYMENT_CACHE_TTL, using default: 300")
        cache_ttl = 300
    app.config["DEPLOYMENT_SERVICE"] = DeploymentService(cache_ttl=cache_ttl)
    logger.info("Deployment service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize deployment service: {e}")
    app.config["DEPLOYMENT_SERVICE"] = None

# Clean up orphaned lock files from previous sessions (#408)
# These functions already exist and are tested — we just need to invoke them at startup.
try:
    from webui.backend.lib.schedule_storage import cleanup_temp_files as cleanup_schedule_locks

    removed = cleanup_schedule_locks()
    if removed > 0:
        logger.info(f"Cleaned up {removed} orphaned schedule lock file(s)")
except Exception as e:
    logger.warning(f"Schedule lock cleanup failed (non-fatal): {e}")

try:
    from webui.backend.lib.deployment_sidecar import cleanup_temp_files as cleanup_deployment_locks

    removed = cleanup_deployment_locks(PHOTOS_DIR)
    if removed > 0:
        logger.info(f"Cleaned up {removed} orphaned deployment lock file(s)")
except Exception as e:
    logger.warning(f"Deployment lock cleanup failed (non-fatal): {e}")

# Initialize export preset manager
from mothbox_paths import EXPORT_BUILTIN_PRESET_DIR, EXPORT_USER_PRESET_DIR
from webui.backend.export_preset_manager import ExportPresetManager

try:
    # Use built-in presets from package if production paths don't exist

    # Check if the production path exists, otherwise use package path
    if EXPORT_BUILTIN_PRESET_DIR.exists():
        builtin_dir = EXPORT_BUILTIN_PRESET_DIR
    else:
        # Fall back to presets shipped with the package
        builtin_dir = Path(__file__).parent / "presets_builtin" / "export"

    # Ensure user directory exists
    EXPORT_USER_PRESET_DIR.mkdir(parents=True, exist_ok=True)

    export_preset_manager = ExportPresetManager(
        builtin_dir=builtin_dir, user_dir=EXPORT_USER_PRESET_DIR
    )
    app.config["EXPORT_PRESET_MANAGER"] = export_preset_manager
    counts = export_preset_manager.get_preset_count()
    logger.info(
        f"Export preset manager initialized ({counts['built_in']} built-in, {counts['user']} user)"
    )
except Exception as e:
    logger.warning(f"Failed to initialize export preset manager: {e}")
    app.config["EXPORT_PRESET_MANAGER"] = None

# Import route blueprints
from routes.camera import camera_bp
from routes.config import config_bp
from routes.deployment import deployment_bp
from routes.export import export_bp
from routes.export_presets import export_presets_bp
from routes.gallery import gallery_bp
from routes.gpio import gpio_bp
from routes.gps import gps_bp
from routes.gps_exif import gps_exif_bp
from routes.metadata import metadata_bp
from routes.preferences import preferences_bp
from routes.presets import presets_bp
from routes.scheduler import scheduler_bp
from routes.scheduler_ui import scheduler_ui_bp
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
app.register_blueprint(scheduler_ui_bp, url_prefix="/api/scheduler/ui")
app.register_blueprint(presets_bp, url_prefix="/api/presets")
app.register_blueprint(preferences_bp, url_prefix="/api/preferences")
app.register_blueprint(gps_bp, url_prefix="/api/gps")
app.register_blueprint(gps_exif_bp, url_prefix="/api/gps-exif")
app.register_blueprint(metadata_bp, url_prefix="/api/metadata")
app.register_blueprint(sidecar_bp, url_prefix="/api/sidecar")
app.register_blueprint(deployment_bp, url_prefix="/api/deployment")
app.register_blueprint(export_bp, url_prefix="/api/export")
app.register_blueprint(export_presets_bp, url_prefix="/api/export/presets")
app.register_blueprint(search_bp)  # Note: search_bp already includes /api/photos/search prefix

# Register WebSocket handlers
from websocket_handlers import register_handlers

register_handlers(socketio, camera_streamer)
logger.info("Registered WebSocket event handlers")

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

logger.info("Rate limiting applied to camera, GPIO, and GPS endpoints")

# Sidecar API rate limiting
# Bulk: 10 per minute (prevents abuse of batch operations)
# PATCH/DELETE: 30 per minute (one per 2 seconds, reasonable for UI use)
limiter.limit("10 per minute")(app.view_functions["sidecar.bulk_update_metadata"])
limiter.limit("30 per minute")(app.view_functions["sidecar.update_photo_metadata"])
limiter.limit("30 per minute")(app.view_functions["sidecar.delete_photo_metadata"])

# Tag autocomplete rate limiting
# 60 per minute (1 per second) - autocomplete endpoints are chatty with typing
limiter.limit("60 per minute")(app.view_functions["metadata.get_tag_autocomplete"])

logger.info("Rate limiting applied to sidecar and metadata endpoints")


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
    logger.warning(f"CSRF validation failed: {e.description}")
    logger.debug(f"Request path: {request.path}")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request cookies: {list(request.cookies.keys())}")
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
    logger.info("\n" + "=" * 60)
    logger.info("Mothbox Web UI Starting")
    logger.info(f"Environment: {config.ENV_NAME}")
    logger.info(f"Debug Mode: {config.DEBUG}")
    logger.info(f"Host: {config.HOST}:{config.PORT}")
    logger.info("=" * 60)

    if config.ENV_NAME == "production":
        logger.warning("\n" + "=" * 60)
        logger.warning("WARNING: Running with Werkzeug development server")
        logger.warning("For production deployment, use gunicorn with eventlet worker")
        logger.warning("See issue #19: https://github.com/zane-lazare/Mothbox/issues/19")
        logger.warning("=" * 60 + "\n")

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
