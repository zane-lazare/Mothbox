"""Scheduler management endpoints"""
from flask import Blueprint, jsonify, request
from crontab import CronTab
import sys
from pathlib import Path

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import get_script_path

scheduler_bp = Blueprint('scheduler', __name__)

# Whitelist of allowed Mothbox scripts to prevent command injection
# Maps friendly keys to script filenames
ALLOWED_SCRIPTS = {
    'takephoto': 'TakePhoto.py',
    'scheduler': 'Scheduler.py',
    'backup': 'Backup_Files.py',
    'attract_on': 'Attract_On.py',
    'attract_off': 'Attract_Off.py',
    'flash_on': 'FlashOn.py'
}

@scheduler_bp.route('/jobs', methods=['GET'])
def list_cron_jobs():
    """List all Mothbox cron jobs"""
    try:
        cron = CronTab(user=True)
        jobs = []

        for job in cron:
            if 'mothbox' in job.command.lower() or 'TakePhoto' in job.command:
                jobs.append({
                    'command': job.command,
                    'schedule': str(job.slices),
                    'enabled': job.is_enabled(),
                    'comment': job.comment
                })

        return jsonify({'jobs': jobs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scheduler_bp.route('/job', methods=['POST'])
def add_cron_job():
    """Add a new cron job (with command injection protection)"""
    try:
        data = request.json
        script_key = data.get('script_key')  # Use script_key instead of raw command
        schedule = data.get('schedule')  # e.g., "0 * * * *"
        comment = data.get('comment', '')

        if not script_key or not schedule:
            return jsonify({'error': 'Missing script_key or schedule'}), 400

        # Validate script_key against whitelist to prevent command injection
        if script_key not in ALLOWED_SCRIPTS:
            return jsonify({
                'error': f'Invalid script_key. Allowed: {", ".join(ALLOWED_SCRIPTS.keys())}'
            }), 400

        # Get validated script path (get_script_path already has path traversal protection)
        script_name = ALLOWED_SCRIPTS[script_key]
        try:
            script_path = get_script_path(script_name)
        except ValueError as e:
            return jsonify({'error': f'Script path validation failed: {str(e)}'}), 400

        # Construct command with validated path
        command = f"/usr/bin/python3 {script_path}"

        # Create cron job with validated command
        cron = CronTab(user=True)
        job = cron.new(command=command, comment=comment)
        job.setall(schedule)
        cron.write()

        return jsonify({'success': True, 'command': command})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scheduler_bp.route('/job', methods=['DELETE'])
def delete_cron_job():
    """Delete a cron job (with validation to prevent deleting non-Mothbox jobs)"""
    try:
        data = request.json
        command = data.get('command')

        if not command:
            return jsonify({'error': 'Missing command'}), 400

        # Validate that command looks like a Mothbox job
        # Use same filtering logic as GET /jobs endpoint
        is_mothbox_job = (
            'mothbox' in command.lower() or
            'TakePhoto' in command or
            '/usr/bin/python3' in command  # All Mothbox jobs use this
        )

        if not is_mothbox_job:
            return jsonify({
                'error': 'Command does not appear to be a Mothbox job. Deletion rejected for safety.',
                'command': command
            }), 400

        # Additional validation: Check if command path is within MOTHBOX_HOME
        from mothbox_paths import MOTHBOX_HOME
        if str(MOTHBOX_HOME) not in command:
            return jsonify({
                'error': f'Command path is not within MOTHBOX_HOME ({MOTHBOX_HOME}). Deletion rejected.',
                'command': command
            }), 400

        # Validation passed - safe to delete
        cron = CronTab(user=True)
        removed_count = cron.remove_all(command=command)
        cron.write()

        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'command': command
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scheduler_bp.route('/status', methods=['GET'])
def get_scheduler_status():
    """Get scheduler status from Scheduler.py"""
    try:
        import subprocess

        # Check if cron is running
        result = subprocess.run(['systemctl', 'is-active', 'cron'], capture_output=True, text=True)
        cron_active = result.stdout.strip() == 'active'

        return jsonify({
            'cron_active': cron_active,
            'scheduler_script': str(get_script_path('Scheduler.py'))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
