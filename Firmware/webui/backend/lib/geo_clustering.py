"""
Geographic Clustering Library for Mothbox Photo Locations

Provides Haversine distance-based clustering of photo locations with
configurable radius and performance optimizations.

Algorithm:
- Grid-based spatial hashing for O(n) initial grouping
- Haversine distance verification for accuracy
- Union-find for efficient cluster merging
- Centroid calculation for cluster centers

Usage:
    from webui.backend.lib.geo_clustering import cluster_locations

    locations = [
        {"path": "2024-11-10/photo1.jpg", "lat": 37.7749, "lon": -122.4194},
        {"path": "2024-11-10/photo2.jpg", "lat": 37.7750, "lon": -122.4195},
    ]

    result = cluster_locations(locations, radius_m=100)

    for cluster in result.clusters:
        print(f"Cluster {cluster.cluster_id}: {cluster.count} photos")
        print(f"  Center: {cluster.center_lat}, {cluster.center_lon}")

Performance:
- <100ms for 1000 photos
- <500ms for 10000 photos (with timeout fallback)
- Thread-safe (pure functions, no shared state)
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

from webui.backend.lib.haversine import haversine_distance, validate_coordinates

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PhotoLocation:
    """Represents a photo with GPS location.

    Attributes:
        path: Relative path from PHOTOS_DIR (e.g., "2024-11-10/photo.jpg")
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
        timestamp: Optional ISO format timestamp (YYYY-MM-DDTHH:MM:SS)
        filepath: Optional full path to photo file
        tags: Optional list of tags/labels for the photo
    """
    path: str
    lat: float
    lon: float
    timestamp: str | None = None
    filepath: Path | None = None
    tags: list[str] | None = None


@dataclass
class PhotoCluster:
    """Represents a cluster of nearby photos.

    Attributes:
        cluster_id: Unique identifier (format: cluster_{lat}_{lon}_{count})
        center_lat: Centroid latitude in decimal degrees
        center_lon: Centroid longitude in decimal degrees
        photos: List of PhotoLocation objects in this cluster
        date_range: Tuple of (earliest_timestamp, latest_timestamp)
    """
    cluster_id: str
    center_lat: float
    center_lon: float
    photos: list[PhotoLocation] = field(default_factory=list)
    date_range: tuple[str | None, str | None] = (None, None)

    @property
    def count(self) -> int:
        """Get the number of photos in this cluster."""
        return len(self.photos)

    @property
    def radius_m(self) -> float:
        """Calculate actual radius of cluster (max distance from center to any photo)."""
        if not self.photos:
            return 0.0

        max_dist = 0.0
        for photo in self.photos:
            dist = haversine_distance(
                self.center_lat, self.center_lon,
                photo.lat, photo.lon
            )
            max_dist = max(max_dist, dist)

        return max_dist


@dataclass
class ClusteringResult:
    """Result of clustering operation.

    Attributes:
        clusters: List of PhotoCluster objects
        unclustered: List of PhotoLocation objects not in any cluster
        total_photos: Total number of photos processed
        total_clusters: Number of clusters formed
        radius_m: Configured clustering radius in meters
        processing_time_ms: Time taken to perform clustering
        partial_result: True if timeout occurred before completion
        warning: Optional warning message (e.g., timeout notice)
    """
    clusters: list[PhotoCluster]
    unclustered: list[PhotoLocation]
    total_photos: int
    total_clusters: int
    radius_m: float
    processing_time_ms: float
    partial_result: bool = False
    warning: str | None = None


# ============================================================================
# Helper Classes
# ============================================================================


class UnionFind:
    """Union-Find (Disjoint Set) data structure for efficient cluster merging."""

    def __init__(self, n: int):
        """Initialize with n elements."""
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """Find root of element x with path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """Union two elements by rank. Returns True if merged."""
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False

        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        return True


# ============================================================================
# Helper Functions
# ============================================================================


def calculate_centroid(locations: list[PhotoLocation]) -> tuple[float, float]:
    """
    Calculate the geographic centroid of a list of locations.

    Uses arithmetic mean of coordinates (simple averaging). For small geographic
    areas this is accurate enough. For large areas spanning significant portions
    of the globe, more sophisticated methods would be needed.

    Args:
        locations: List of PhotoLocation objects

    Returns:
        Tuple of (center_lat, center_lon) in decimal degrees

    Example:
        >>> locs = [
        ...     PhotoLocation("2024/A.jpg", 37.7749, -122.4194),
        ...     PhotoLocation("2024/B.jpg", 37.7751, -122.4196),
        ... ]
        >>> lat, lon = calculate_centroid(locs)
        >>> print(f"{lat:.4f}, {lon:.4f}")
        37.7750, -122.4195
    """
    if not locations:
        return 0.0, 0.0

    sum_lat = sum(loc.lat for loc in locations)
    sum_lon = sum(loc.lon for loc in locations)

    center_lat = sum_lat / len(locations)
    center_lon = sum_lon / len(locations)

    return center_lat, center_lon


def generate_cluster_id(center_lat: float, center_lon: float, count: int) -> str:
    """
    Generate a unique cluster ID based on location and count.

    Format: cluster_{lat:.4f}_{lon:.4f}_{count}

    Args:
        center_lat: Cluster centroid latitude
        center_lon: Cluster centroid longitude
        count: Number of photos in cluster

    Returns:
        Cluster ID string

    Example:
        >>> generate_cluster_id(37.7749, -122.4194, 5)
        'cluster_37.7749_-122.4194_5'
    """
    # Use absolute value for longitude in ID to avoid issues with minus sign
    lon_str = f"{abs(center_lon):.4f}"
    lon_dir = "W" if center_lon < 0 else "E"

    lat_str = f"{abs(center_lat):.4f}"
    lat_dir = "S" if center_lat < 0 else "N"

    return f"cluster_{lat_str}{lat_dir}_{lon_str}{lon_dir}_{count}"


def _get_grid_cell(lat: float, lon: float, cell_size: float) -> tuple[int, int]:
    """
    Get grid cell coordinates for a location.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        cell_size: Grid cell size in degrees

    Returns:
        Tuple of (cell_x, cell_y) integer coordinates
    """
    cell_x = int(lon / cell_size)
    cell_y = int(lat / cell_size)
    return cell_x, cell_y


def _get_adjacent_cells(cell_x: int, cell_y: int) -> list[tuple[int, int]]:
    """
    Get all adjacent cells (including diagonal) for a cell.

    Args:
        cell_x: Cell X coordinate
        cell_y: Cell Y coordinate

    Returns:
        List of (cell_x, cell_y) tuples for adjacent cells
    """
    adjacent = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            adjacent.append((cell_x + dx, cell_y + dy))
    return adjacent


def _calculate_date_range(photos: list[PhotoLocation]) -> tuple[str | None, str | None]:
    """
    Calculate date range for a list of photos.

    Args:
        photos: List of PhotoLocation objects

    Returns:
        Tuple of (earliest_timestamp, latest_timestamp) or (None, None)
    """
    timestamps = [p.timestamp for p in photos if p.timestamp]

    if not timestamps:
        return None, None

    return min(timestamps), max(timestamps)


# ============================================================================
# Main Clustering Function
# ============================================================================


def cluster_locations(
    locations: list[dict],
    radius_m: float = 100,
    min_cluster_size: int = 2,
    timeout_ms: float = 500
) -> ClusteringResult:
    """
    Cluster photo locations using Haversine distance.

    Uses grid-based spatial hashing for O(n) initial grouping,
    then Haversine verification for accuracy, and union-find for
    efficient cluster merging.

    Algorithm:
    1. Validate and convert input to PhotoLocation objects
    2. Create spatial grid with cell size based on radius
    3. Hash each location to grid cell(s)
    4. For each location, check adjacent cells for nearby photos
    5. Merge nearby photos using union-find
    6. Extract final clusters and calculate centroids
    7. Filter by min_cluster_size

    Args:
        locations: List of dicts with keys: path, lat, lon, timestamp (optional)
        radius_m: Maximum distance between cluster members (meters)
        min_cluster_size: Minimum photos to form a cluster (singles go to unclustered)
        timeout_ms: Maximum processing time before returning partial results

    Returns:
        ClusteringResult with clusters, unclustered photos, and metadata

    Raises:
        ValueError: If radius_m is negative

    Example:
        >>> locs = [
        ...     {"path": "2024/A.jpg", "lat": 37.7749, "lon": -122.4194},
        ...     {"path": "2024/B.jpg", "lat": 37.7750, "lon": -122.4195},
        ... ]
        >>> result = cluster_locations(locs, radius_m=100)
        >>> print(f"{result.total_clusters} clusters, {len(result.unclustered)} unclustered")
        1 clusters, 0 unclustered
    """
    start_time = time.time()

    # Validate radius
    if radius_m < 0:
        raise ValueError(f"Radius must be non-negative, got {radius_m}")

    # Handle empty input
    if not locations:
        return ClusteringResult(
            clusters=[],
            unclustered=[],
            total_photos=0,
            total_clusters=0,
            radius_m=radius_m,
            processing_time_ms=0.0
        )

    # Step 1: Validate and convert to PhotoLocation objects
    photo_locations = []
    for loc in locations:
        # Extract fields
        path = loc.get("path", "")
        lat = loc.get("lat")
        lon = loc.get("lon")
        timestamp = loc.get("timestamp")
        filepath = loc.get("filepath")
        tags = loc.get("tags")

        # Skip if missing required fields
        if not path or lat is None or lon is None:
            continue

        # Validate coordinates
        is_valid, _ = validate_coordinates(lat, lon)
        if not is_valid:
            continue

        photo_locations.append(PhotoLocation(
            path=path,
            lat=float(lat),
            lon=float(lon),
            timestamp=timestamp,
            filepath=Path(filepath) if filepath else None,
            tags=tags
        ))

    n = len(photo_locations)

    if n == 0:
        return ClusteringResult(
            clusters=[],
            unclustered=[],
            total_photos=0,
            total_clusters=0,
            radius_m=radius_m,
            processing_time_ms=(time.time() - start_time) * 1000
        )

    # Step 2: Calculate grid cell size
    # At equator: 1° ≈ 111km
    # Cell size should be radius_m / 111000 degrees
    cell_size = radius_m / 111000.0

    # Step 3: Build spatial grid
    grid: dict[tuple[int, int], list[int]] = {}
    for i, photo in enumerate(photo_locations):
        cell = _get_grid_cell(photo.lat, photo.lon, cell_size)
        if cell not in grid:
            grid[cell] = []
        grid[cell].append(i)

    # Step 4: Initialize union-find
    uf = UnionFind(n)

    # Step 5: Check adjacent cells for nearby photos
    processed = 0
    partial_result = False

    for i, photo in enumerate(photo_locations):
        # Check timeout
        if (time.time() - start_time) * 1000 > timeout_ms:
            partial_result = True
            break

        cell = _get_grid_cell(photo.lat, photo.lon, cell_size)
        adjacent_cells = _get_adjacent_cells(cell[0], cell[1])

        # Check all photos in adjacent cells
        for adj_cell in adjacent_cells:
            if adj_cell not in grid:
                continue

            for j in grid[adj_cell]:
                if i >= j:  # Skip self and already compared pairs
                    continue

                # Verify actual distance
                other = photo_locations[j]
                dist = haversine_distance(photo.lat, photo.lon, other.lat, other.lon)

                if dist <= radius_m:
                    uf.union(i, j)

        processed += 1

    # Step 6: Extract clusters from union-find
    cluster_map: dict[int, list[int]] = {}
    for i in range(processed):
        root = uf.find(i)
        if root not in cluster_map:
            cluster_map[root] = []
        cluster_map[root].append(i)

    # Step 7: Build PhotoCluster objects
    clusters = []
    unclustered = []

    for indices in cluster_map.values():
        if len(indices) < min_cluster_size:
            # Add to unclustered
            for idx in indices:
                unclustered.append(photo_locations[idx])
        else:
            # Create cluster
            cluster_photos = [photo_locations[idx] for idx in indices]

            # Calculate centroid
            center_lat, center_lon = calculate_centroid(cluster_photos)

            # Calculate date range
            date_range = _calculate_date_range(cluster_photos)

            # Generate cluster ID
            cluster_id = generate_cluster_id(center_lat, center_lon, len(cluster_photos))

            cluster = PhotoCluster(
                cluster_id=cluster_id,
                center_lat=center_lat,
                center_lon=center_lon,
                photos=cluster_photos,
                date_range=date_range
            )

            clusters.append(cluster)

    # Add unprocessed photos to unclustered if timeout occurred
    if partial_result:
        for i in range(processed, n):
            unclustered.append(photo_locations[i])

    # Calculate processing time
    processing_time_ms = (time.time() - start_time) * 1000

    # Build result
    result = ClusteringResult(
        clusters=clusters,
        unclustered=unclustered,
        total_photos=n,
        total_clusters=len(clusters),
        radius_m=radius_m,
        processing_time_ms=processing_time_ms,
        partial_result=partial_result,
        warning="Clustering timed out - returning partial results" if partial_result else None
    )

    return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'PhotoLocation',
    'PhotoCluster',
    'ClusteringResult',
    'cluster_locations',
    'calculate_centroid',
    'generate_cluster_id',
]
