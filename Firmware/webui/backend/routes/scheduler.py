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
    """Add a new cron job"""
    try:
        data = request.json
        command = data.get('command')
        schedule = data.get('schedule')  # e.g., "0 * * * *"
        comment = data.get('comment', '')

        if not command or not schedule:
            return jsonify({'error': 'Missing command or schedule'}), 400

        cron = CronTab(user=True)
        job = cron.new(command=command, comment=comment)
        job.setall(schedule)
        cron.write()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scheduler_bp.route('/job', methods=['DELETE'])
def delete_cron_job():
    """Delete a cron job"""
    try:
        data = request.json
        command = data.get('command')

        if not command:
            return jsonify({'error': 'Missing command'}), 400

        cron = CronTab(user=True)
        cron.remove_all(command=command)
        cron.write()

        return jsonify({'success': True})
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
