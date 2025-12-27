"""
Services package for Mothbox web UI backend

Contains business logic services that can be used by route handlers.
Provides lazy-initialization getters for singleton services to avoid circular imports.
"""

from .photo_service import PaginationError, PhotoService
from .thumbnail_cache import ThumbnailCache, ThumbnailError

# Lazy-initialized singleton service instances
_clustering_service = None
_series_service = None
_locations_service = None
_sidecar_service = None
_deployment_service = None
_scheduler_service = None
_sensor_service = None


def get_clustering_service():
    """
    Get the singleton ClusteringService instance.
    Lazily initializes on first call to avoid circular imports.
    """
    global _clustering_service
    if _clustering_service is None:
        from .clustering_service import ClusteringService
        _clustering_service = ClusteringService(cache_ttl=300)
    return _clustering_service


def get_series_service():
    """
    Get the singleton SeriesService instance.
    Lazily initializes on first call to avoid circular imports.
    """
    global _series_service
    if _series_service is None:
        from .series_service import SeriesService
        _series_service = SeriesService(cache_ttl=300)
    return _series_service


def get_locations_service():
    """
    Get the singleton LocationsService instance.
    Lazily initializes on first call to avoid circular imports.
    """
    global _locations_service
    if _locations_service is None:
        from .locations_service import LocationsService
        _locations_service = LocationsService(cache_ttl=300)
    return _locations_service


def get_sidecar_service():
    """
    Get the singleton SidecarService instance.
    Lazily initializes on first call to avoid circular imports.
    """
    global _sidecar_service
    if _sidecar_service is None:
        import contextlib
        import logging

        from mothbox_paths import DATA_DIR

        from .sidecar_service import CACHE_SCHEMA_VERSION, SidecarService

        logger = logging.getLogger(__name__)

        cache_dir = DATA_DIR / "cache" / "sidecar"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Check version file and purge if schema changed
        version_file = cache_dir / ".version"
        if version_file.exists() and version_file.read_text().strip() != CACHE_SCHEMA_VERSION:
            logger.info("Cache schema version changed, purging L2 cache")
            for f in cache_dir.glob("*.json"):
                with contextlib.suppress(Exception):
                    f.unlink()
        version_file.write_text(CACHE_SCHEMA_VERSION)

        _sidecar_service = SidecarService(
            cache_dir=cache_dir,
            cache_version=CACHE_SCHEMA_VERSION,
        )
    return _sidecar_service


def get_deployment_service():
    """
    Get the singleton DeploymentService instance.
    Lazily initializes on first call to avoid circular imports.
    """
    global _deployment_service
    if _deployment_service is None:
        from .deployment_service import DeploymentService
        _deployment_service = DeploymentService(cache_ttl=300)
    return _deployment_service


def get_scheduler_service():
    """
    Get singleton SchedulerService instance with lazy initialization.

    Returns:
        SchedulerService: The singleton service instance

    Example:
        from webui.backend.services import get_scheduler_service

        service = get_scheduler_service()
        schedules = service.list_schedules()
    """
    global _scheduler_service
    if _scheduler_service is None:
        from .scheduler_service import SchedulerService
        _scheduler_service = SchedulerService(cache_ttl=300, max_cache_size=100)
    return _scheduler_service


def get_sensor_service():
    """
    Get singleton SensorService instance with lazy initialization.

    Returns:
        SensorService: The singleton service instance

    Example:
        from webui.backend.services import get_sensor_service

        service = get_sensor_service()
        if service.evaluate_preconditions(preconditions):
            # Proceed with capture
            pass
    """
    global _sensor_service
    if _sensor_service is None:
        from .sensor_service import SensorService
        _sensor_service = SensorService(max_history=100)
    return _sensor_service


__all__ = [
    'PhotoService',
    'PaginationError',
    'ThumbnailCache',
    'ThumbnailError',
    'get_clustering_service',
    'get_series_service',
    'get_locations_service',
    'get_sidecar_service',
    'get_deployment_service',
    'get_scheduler_service',
    'get_sensor_service',
]
