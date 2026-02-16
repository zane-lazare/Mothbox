#!/usr/bin/python

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import logging
import os
import select
import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from gps import *  # noqa: F403 - gpsd library requires these exports
from timezonefinder import TimezoneFinder

from mothbox_paths import CONTROLS_FILE, get_control_values, get_hardware_config
from webui.backend.lib.file_lock import FileLock, LockTimeoutError

# Configure logging for standalone script execution
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load hardware configuration
hw_config = get_hardware_config()

if not hw_config["gps_enabled"]:
    logger.info("GPS disabled in configuration")
    sys.exit(0)

gpsd = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)  # noqa: F405
UTCtime = None
latitude = None
longitude = None
start_time = time.time()
tf = TimezoneFinder()
timeout = hw_config["gps_timeout"]

start_time = time.time()
tf = TimezoneFinder()

"""
#This might be mysticism, the GPS might just need a good view of the sky
#It seems that (at least for a USB gps) if the GPS has been disconnected and reconnected, gpsmon has to run before it can get timings and stuff
import signal
import subprocess

# Start gpsmon in the background (detached)
proc = subprocess.Popen(['gpsmon'])

# Wait for exactly 3 seconds
time.sleep(3)

# Send SIGTERM to terminate gpsmon and wait a moment to ensure it exits properly
proc.terminate()
time.sleep(0.1)  # Allow time for process cleanup

# If the process didn't exit after terminate(), send SIGKILL as a failsafe (not recommended)
try:
    proc.wait(timeout=0.5)
except subprocess.TimeoutExpired:
    proc.kill()

print("gpsmon terminated")
"""

# Use get_control_values from mothbox_paths (proper error handling built-in)
control_values = get_control_values(str(CONTROLS_FILE))


def update_gps_values(
    filepath,
    lat=None,
    lon=None,
    gpstime=None,
    utc_offset=None,
    fix_mode=None,
    nsat=None,
    usat=None,
    hdop=None,
    pdop=None,
):
    """
    Atomically update GPS values in controls.txt with file locking.

    This prevents race conditions with WebUI by using FileLock with timeout.
    All GPS values are updated in a single locked write operation.

    Args:
        filepath: Path to controls.txt
        lat: Latitude value (or None to skip)
        lon: Longitude value (or None to skip)
        gpstime: Unix timestamp (or None to skip)
        utc_offset: UTC offset in hours (or None to skip)
        fix_mode: GPS fix mode - 0=no fix, 2=2D, 3=3D (or None to skip)
        nsat: Number of satellites visible (or None to skip)
        usat: Number of satellites used in fix (or None to skip)
        hdop: Horizontal dilution of precision (or None to skip)
        pdop: Position dilution of precision (or None to skip)
    """
    # Prepare updates mapping (only include values that were provided)
    updates = {}
    if lat is not None:
        updates["lat"] = str(lat)
        # Also update last known position if lat/lon are valid (not "n/a")
        if lat != "n/a" and lon is not None and lon != "n/a":
            updates["last_known_lat"] = str(lat)
            updates["last_known_lon"] = str(lon)
            if gpstime is not None:
                updates["last_position_time"] = str(gpstime)
    if lon is not None:
        updates["lon"] = str(lon)
    if gpstime is not None:
        updates["gpstime"] = str(gpstime)
    if utc_offset is not None:
        updates["UTCoff"] = str(utc_offset)
    if fix_mode is not None:
        updates["gps_fix_mode"] = str(fix_mode)
    if nsat is not None:
        updates["gps_satellites_visible"] = str(nsat)
    if usat is not None:
        updates["gps_satellites_used"] = str(usat)
    if hdop is not None:
        updates["gps_hdop"] = f"{hdop:.3f}"  # 3 decimal precision for GPS quality
    if pdop is not None:
        updates["gps_pdop"] = f"{pdop:.3f}"  # 3 decimal precision for GPS quality

    # Retries handle write failures (e.g., I/O error after lock acquired), not
    # just lock contention — FileLock's internal backoff handles the latter.
    # File write failures are non-critical — stale coordinates persist until
    # next cron run (graceful degradation).
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with FileLock(filepath, exclusive=True, timeout=10.0) as f:
                # Read current contents
                lines = f.readlines()

                # Update lines
                updated_lines = []
                updated_keys = set()

                for line in lines:
                    stripped = line.strip()
                    if stripped and "=" in stripped and not stripped.startswith("#"):
                        key = stripped.split("=", 1)[0]
                        if key in updates:
                            updated_lines.append(f"{key}={updates[key]}\n")
                            updated_keys.add(key)
                            logger.debug(
                                "Updated %s=%s", key, updates[key]
                            )  # lgtm[py/clear-text-logging-sensitive-data]
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)

                # Add any new keys that weren't in the file
                for key, value in updates.items():
                    if key not in updated_keys:
                        updated_lines.append(f"{key}={value}\n")
                        # GPS coordinates are equipment deployment locations (camera trap position),
                        # not personal/user data. This logging is intentional for debugging.
                        logger.debug(
                            "Added %s=%s", key, value
                        )  # lgtm[py/clear-text-logging-sensitive-data]

                # Write back to file
                f.seek(0)
                f.truncate()
                f.writelines(updated_lines)
                f.flush()
                return  # success
        except LockTimeoutError:
            if attempt < max_retries:
                logger.info(
                    "Lock attempt %d/%d failed on %s — retrying",
                    attempt,
                    max_retries,
                    filepath,
                )
                time.sleep(0.5)
            else:
                logger.warning(
                    "Could not acquire lock on %s after %d attempts — skipping GPS update",
                    filepath,
                    max_retries,
                )


logger.info("startingGPS")
got_gps_fix = False
UTCtime = None
latitude = None
longitude = None

# GPS quality metrics
fix_mode = 0  # 0=no fix, 2=2D, 3=3D
satellites_visible = 0
satellites_used = 0
hdop = 99.99  # Horizontal dilution of precision (lower is better)
pdop = 99.99  # Position dilution of precision (lower is better)

try:
    while time.time() - start_time < timeout:
        # Check if there's data from gpsd (timeout = 1 second)
        if select.select([gpsd.sock], [], [], 1)[0]:
            report = gpsd.next()

            # TPV report: Time-Position-Velocity
            if report["class"] == "TPV":
                got_gps_fix = True
                latitude = getattr(report, "lat", None)
                longitude = getattr(report, "lon", None)
                UTCtime = getattr(report, "time", "")
                fix_mode = getattr(report, "mode", 0)
                # GPS coordinates are equipment deployment locations (camera trap position),
                # not personal/user data. This logging is intentional for debugging.
                logger.debug(
                    f"TPV: {latitude}\t{longitude}\t{UTCtime}\t"
                    f"alt={getattr(report, 'alt', 'nan')}\t"
                    f"mode={fix_mode}\t"
                    f"epv={getattr(report, 'epv', 'nan')}\t"
                    f"ept={getattr(report, 'ept', 'nan')}"
                )

            # SKY report: Satellite visibility and dilution of precision
            elif report["class"] == "SKY":
                satellites_visible = len(getattr(report, "satellites", []))
                satellites_used = getattr(report, "uSat", 0)
                hdop = getattr(report, "hdop", 99.99)
                pdop = getattr(report, "pdop", 99.99)
                logger.debug(
                    f"SKY: nSat={satellites_visible}, uSat={satellites_used}, "
                    f"HDOP={hdop:.2f}, PDOP={pdop:.2f}"
                )
        else:
            logger.debug("Waiting for GPS data...")
        time.sleep(1)
    logger.info("Finished Looking for GPS. GPS device found = " + str(got_gps_fix))
    if UTCtime:
        try:
            dt = datetime.strptime(UTCtime, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            dt = datetime.strptime(UTCtime, "%Y-%m-%dT%H:%M:%SZ")
        dt = dt.replace(tzinfo=UTC)  # Mark as UTC before converting to epoch
        epoch_time = int(dt.timestamp())
        logger.info("Epoch time: %s", epoch_time)

        # Set system UTC time
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        os.system(f'sudo date -u -s "{formatted_time}"')  # nosec B605 - GPS time from hardware, validated by strptime
        logger.info("sync HW clock with system clock")
        os.system("sudo hwclock -w")  # nosec B605 - Hardcoded system command
        logger.info("System UTC time set.")

        # Use offline timezone lookup
        if latitude is not None and longitude is not None:
            timezone = tf.timezone_at(lat=latitude, lng=longitude)
            if timezone:
                logger.info("Setting system timezone to: %s", timezone)
                os.system(f"sudo timedatectl set-timezone {timezone}")  # nosec B605 - Timezone from timezonefinder library lookup

                # Now calculate the UTC offset
                from zoneinfo import ZoneInfo

                local_time = datetime.now(ZoneInfo(timezone))
                utc_offset_hours = int(local_time.utcoffset().total_seconds() // 3600)
                logger.info("UTC Offset (hours): %s", utc_offset_hours)

                # Atomically update all GPS values in one locked operation
                update_gps_values(
                    str(CONTROLS_FILE),
                    lat=latitude,
                    lon=longitude,
                    gpstime=epoch_time,
                    utc_offset=utc_offset_hours,
                    fix_mode=fix_mode,
                    nsat=satellites_visible,
                    usat=satellites_used,
                    hdop=hdop,
                    pdop=pdop,
                )
            else:
                logger.warning("Could not determine timezone from coordinates.")
                # GPS coordinates are equipment deployment locations (camera trap position),
                # not personal/user data. This logging is intentional for debugging.
                logger.info(
                    "Writing coordinates anyway: lat=%s, lon=%s", latitude, longitude
                )  # lgtm[py/clear-text-logging-sensitive-data]
                # Still write coordinates even if timezone lookup fails
                # Use default UTC offset of 0 since we couldn't determine it
                update_gps_values(
                    str(CONTROLS_FILE),
                    lat=latitude,
                    lon=longitude,
                    gpstime=epoch_time,
                    utc_offset=0,  # Default to UTC if timezone unknown
                    fix_mode=fix_mode,
                    nsat=satellites_visible,
                    usat=satellites_used,
                    hdop=hdop,
                    pdop=pdop,
                )
        else:
            # GPS has time fix but no position fix
            logger.info("No position fix - time only")
            update_gps_values(
                str(CONTROLS_FILE),
                lat="n/a",
                lon="n/a",
                gpstime=epoch_time,
                fix_mode=fix_mode,
                nsat=satellites_visible,
                usat=satellites_used,
                hdop=hdop,
                pdop=pdop,
            )

    else:
        logger.info("No UTC time received before timeout")
        update_gps_values(
            str(CONTROLS_FILE),
            lat="n/a",
            lon="n/a",
            fix_mode=fix_mode,
            nsat=satellites_visible,
            usat=satellites_used,
            hdop=hdop,
            pdop=pdop,
        )


except (KeyboardInterrupt, SystemExit):
    logger.info("Done.\nExiting.")
