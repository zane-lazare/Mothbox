"""Scheduler management endpoints"""

import logging

from crontab import CronTab
from flask import Blueprint, jsonify, request

# Setup path to import mothbox_paths
from mothbox_paths import get_script_path

# Import cron security utilities (Issue #207)
from webui.backend.lib.cron_security import (
    ALLOWED_SCRIPTS,
    is_mothbox_command,
    validate_script_key,
)
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/jobs", methods=["GET"])
def list_cron_jobs():
    """List all Mothbox cron jobs"""
    try:
        cron = CronTab(user=True)
        jobs = []

        for job in cron:
            if "mothbox" in job.command.lower() or "TakePhoto" in job.command:
                jobs.append(
                    {
                        "command": job.command,
                        "schedule": str(job.slices),
                        "enabled": job.is_enabled(),
                        "comment": job.comment,
                    }
                )

        return jsonify({"jobs": jobs})
    except Exception as e:
        logger.error(f"Error listing cron jobs: {e}")
        return error_response(SERVER_ERROR, "Failed to list cron jobs", 500)


@scheduler_bp.route("/job", methods=["POST"])
def add_cron_job():
    """Add a new cron job (with command injection protection)"""
    try:
        data = request.json
        script_key = data.get("script_key")  # Use script_key instead of raw command
        schedule = data.get("schedule")  # e.g., "0 * * * *"
        comment = data.get("comment", "")

        if not script_key or not schedule:
            return error_response(VALIDATION_ERROR, "Missing script_key or schedule")

        # Validate script_key against whitelist to prevent command injection
        valid, error = validate_script_key(script_key)
        if not valid:
            return error_response(VALIDATION_ERROR, error)

        # Get validated script path (get_script_path already has path traversal protection)
        script_name = ALLOWED_SCRIPTS[script_key]
        try:
            script_path = get_script_path(script_name)
        except ValueError as e:
            logger.error(f"Script path validation failed: {e}")
            return error_response(VALIDATION_ERROR, "Script path validation failed")

        # Construct command with validated path
        command = f"/usr/bin/python3 {script_path}"

        # Create cron job with validated command
        cron = CronTab(user=True)
        job = cron.new(command=command, comment=comment)
        job.setall(schedule)
        cron.write()

        return jsonify({"success": True, "command": command})
    except Exception as e:
        logger.error(f"Error adding cron job: {e}")
        return error_response(SERVER_ERROR, "Failed to add cron job", 500)


@scheduler_bp.route("/job", methods=["DELETE"])
def delete_cron_job():
    """Delete a cron job (with validation to prevent deleting non-Mothbox jobs)"""
    try:
        data = request.json
        command = data.get("command")

        if not command:
            return error_response(VALIDATION_ERROR, "Missing command")

        # Validate that command looks like a Mothbox job
        # Use security utility from cron_security module (Issue #207)
        if not is_mothbox_command(command):
            return error_response(
                VALIDATION_ERROR,
                "Command does not appear to be a Mothbox job. Deletion rejected for safety.",
                command=command,
            )

        # Additional validation: Check if command path is within MOTHBOX_HOME
        from mothbox_paths import MOTHBOX_HOME

        if str(MOTHBOX_HOME) not in command:
            return error_response(
                VALIDATION_ERROR,
                f"Command path is not within MOTHBOX_HOME ({MOTHBOX_HOME}). Deletion rejected.",
                command=command,
            )

        # Validation passed - safe to delete
        cron = CronTab(user=True)
        removed_count = cron.remove_all(command=command)
        cron.write()

        return jsonify({"success": True, "removed_count": removed_count, "command": command})
    except Exception as e:
        logger.error(f"Error deleting cron job: {e}")
        return error_response(SERVER_ERROR, "Failed to delete cron job", 500)


@scheduler_bp.route("/status", methods=["GET"])
def get_scheduler_status():
    """Get scheduler status from Scheduler.py"""
    try:
        import subprocess

        # Check if cron is running
        result = subprocess.run(["systemctl", "is-active", "cron"], capture_output=True, text=True)
        cron_active = result.stdout.strip() == "active"

        return jsonify(
            {"cron_active": cron_active, "scheduler_script": str(get_script_path("Scheduler.py"))}
        )
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return error_response(SERVER_ERROR, "Failed to get scheduler status", 500)
