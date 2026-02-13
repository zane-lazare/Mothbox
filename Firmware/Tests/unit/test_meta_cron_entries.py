"""Unit tests for meta-cron entries (Issue #398)."""

from webui.backend.lib.cron_bridge import _get_meta_cron_entries


class TestGetMetaCronEntries:
    """Tests for _get_meta_cron_entries() helper."""

    def test_returns_two_entries(self):
        """Should return @reboot and weekly refresh entries."""
        entries = _get_meta_cron_entries()
        assert len(entries) == 2

    def test_reboot_entry(self):
        """First entry is @reboot for boot reconciliation."""
        entries = _get_meta_cron_entries()
        reboot = [e for e in entries if e.expression == "@reboot"]
        assert len(reboot) == 1
        assert "reconcile_on_boot" in reboot[0].command
        assert "Mothbox" in reboot[0].comment

    def test_weekly_refresh_entry(self):
        """Second entry is weekly cron refresh (Sunday 2am)."""
        entries = _get_meta_cron_entries()
        weekly = [e for e in entries if e.expression == "0 2 * * 0"]
        assert len(weekly) == 1
        assert "refresh_schedule" in weekly[0].command
        assert "Mothbox" in weekly[0].comment

    def test_entries_identifiable_as_mothbox(self):
        """Meta entries are identifiable by is_mothbox_command() for cleanup."""
        from webui.backend.lib.cron_security import is_mothbox_command

        entries = _get_meta_cron_entries()
        for entry in entries:
            assert is_mothbox_command(entry.command), (
                f"Meta entry not identifiable as Mothbox: {entry.command}"
            )
