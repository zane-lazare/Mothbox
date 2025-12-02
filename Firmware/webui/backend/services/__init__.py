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
        from mothbox_paths import DATA_DIR

        from .sidecar_service import SidecarService

        cache_dir = DATA_DIR / "cache" / "sidecar"
        _sidecar_service = SidecarService(cache_dir=cache_dir)
    return _sidecar_service


__all__ = [
    'PhotoService',
    'PaginationError',
    'ThumbnailCache',
    'ThumbnailError',
    'get_clustering_service',
    'get_series_service',
    'get_locations_service',
    'get_sidecar_service',
]
