#!/usr/bin/python

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import CONTROLS_FILE, get_hardware_config, get_control_values

from gps import *
import time
from datetime import datetime
import os
import select
import fcntl
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

# Load hardware configuration
hw_config = get_hardware_config()

if not hw_config['gps_enabled']:
    print("GPS disabled in configuration")
    quit()

gpsd = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)
UTCtime = None
latitude = None
longitude = None
start_time = time.time()
tf = TimezoneFinder()
timeout = hw_config['gps_timeout']

start_time = time.time()
tf = TimezoneFinder()

'''
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
'''

# Use get_control_values from mothbox_paths (proper error handling built-in)
control_values = get_control_values(str(CONTROLS_FILE))


def update_gps_values(filepath, lat=None, lon=None, gpstime=None, utc_offset=None):
    """
    Atomically update GPS values in controls.txt with file locking.

    This prevents race conditions with WebUI by using fcntl exclusive locks.
    All GPS values are updated in a single locked write operation.

    Args:
        filepath: Path to controls.txt
        lat: Latitude value (or None to skip)
        lon: Longitude value (or None to skip)
        gpstime: Unix timestamp (or None to skip)
        utc_offset: UTC offset in hours (or None to skip)
    """
    # Prepare updates mapping (only include values that were provided)
    updates = {}
    if lat is not None:
        updates['lat'] = str(lat)
    if lon is not None:
        updates['lon'] = str(lon)
    if gpstime is not None:
        updates['gpstime'] = str(gpstime)
    if utc_offset is not None:
        updates['UTCoff'] = str(utc_offset)

    # Open file for read/write and acquire exclusive lock
    with open(filepath, 'r+') as f:
        try:
            # Acquire exclusive lock (blocks until lock is available)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            # Read current contents
            lines = f.readlines()

            # Update lines
            updated_lines = []
            updated_keys = set()

            for line in lines:
                stripped = line.strip()
                if stripped and '=' in stripped and not stripped.startswith('#'):
                    key = stripped.split('=', 1)[0]
                    if key in updates:
                        updated_lines.append(f"{key}={updates[key]}\n")
                        updated_keys.add(key)
                        print(f"Updated {key}={updates[key]}")
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)

            # Add any new keys that weren't in the file
            for key, value in updates.items():
                if key not in updated_keys:
                    updated_lines.append(f"{key}={value}\n")
                    print(f"Added {key}={value}")

            # Write back to file
            f.seek(0)
            f.truncate()
            f.writelines(updated_lines)
            f.flush()

        finally:
            # Release lock (automatically released when file closes, but explicit is better)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

print("startingGPS")
got_gps_fix = False

try:
    while time.time() - start_time < timeout:
        # Check if there's data from gpsd (timeout = 1 second)
        if select.select([gpsd.sock], [], [], 1)[0]:
            report = gpsd.next()
            if report['class'] == 'TPV':
                got_gps_fix = True
                latitude = getattr(report, 'lat', None)
                longitude = getattr(report, 'lon', None)
                UTCtime = getattr(report, 'time', '')
                print(latitude, "\t",
                      longitude, "\t",
                      UTCtime, "\t",
                      getattr(report, 'alt', 'nan'), "\t\t",
                      getattr(report, 'epv', 'nan'), "\t",
                      getattr(report, 'ept', 'nan'), "\t",
                      getattr(report, 'speed', 'nan'), "\t",
                      getattr(report, 'climb', 'nan'), "\t")
        else:
            print("Waiting for GPS data...")
        time.sleep(1)
    print("Finished Looking for GPS. GPS device found = "+str(got_gps_fix))
    if UTCtime:
        try:
            dt = datetime.strptime(UTCtime, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            dt = datetime.strptime(UTCtime, "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = int(dt.timestamp())
        print("Epoch time:", epoch_time)

        # Set system UTC time
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        os.system(f"sudo date -u -s \"{formatted_time}\"")
        print("sync HW clock with system clock")
        os.system("sudo hwclock -w")
        print("System UTC time set.")

        # Use offline timezone lookup
        if latitude is not None and longitude is not None:
            timezone = tf.timezone_at(lat=latitude, lng=longitude)
            if timezone:
                print("Setting system timezone to:", timezone)
                os.system(f"sudo timedatectl set-timezone {timezone}")

                # Now calculate the UTC offset
                from zoneinfo import ZoneInfo
                local_time = datetime.now(ZoneInfo(timezone))
                utc_offset_hours = int(local_time.utcoffset().total_seconds() // 3600)
                print("UTC Offset (hours):", utc_offset_hours)

                # Atomically update all GPS values in one locked operation
                update_gps_values(str(CONTROLS_FILE),
                                lat=latitude,
                                lon=longitude,
                                gpstime=epoch_time,
                                utc_offset=utc_offset_hours)
            else:
                print("Could not determine timezone from coordinates.")
                update_gps_values(str(CONTROLS_FILE), lat="n/a", lon="n/a", gpstime=epoch_time)

    else:
        print("No UTC time received before timeout")
        update_gps_values(str(CONTROLS_FILE), lat="n/a", lon="n/a")



except (KeyboardInterrupt, SystemExit):
    print("Done.\nExiting.")
