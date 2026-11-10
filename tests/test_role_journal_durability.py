"""Tests for RoleSyncJournal Durability, Concurrency, and Process Recovery."""

import json
import os
import threading
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.role_sync_service import (
    RoleSyncJournal,
    RoleSyncJournalEntry,
    SyncState,
)


class TestRoleJournalDurability:
    """Audit test suite verifying RoleSyncJournal durability, concurrency, and corruption recovery."""

    @pytest.fixture
    def journal_path(self, tmp_path):
        """Temporary file path for role sync journal."""
        return tmp_path / "metadata" / "role_sync_audit.jsonl"

    def test_missing_file_initialization_and_creation(self, journal_path):
        """Verify journal initializes gracefully when file does not exist, and creates it on first write."""
        assert not journal_path.exists()
        journal = RoleSyncJournal(log_path=str(journal_path))
        assert len(journal.get_unreconciled_entries()) == 0

        # First write creates directory and file
        entry = journal.record_intent(uuid.uuid4(), "user", "admin")
        assert journal_path.exists()
        assert entry.sync_id in journal._entries

        with open(journal_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["sync_id"] == entry.sync_id
            assert data["state"] == SyncState.PENDING.value

    def test_concurrent_multi_threaded_writes(self, journal_path):
        """Verify thread-safety and no data loss under concurrent multi-threaded writes."""
        journal = RoleSyncJournal(log_path=str(journal_path))
        num_threads = 20
        num_ops_per_thread = 10
        errors = []

        def worker_task(thread_idx: int):
            try:
                for i in range(num_ops_per_thread):
                    uid = uuid.uuid4()
                    entry = journal.record_intent(uid, "user", "admin")
                    # Advance state
                    journal.update_state(entry.sync_id, SyncState.IDP_UPDATED)
                    journal.update_state(entry.sync_id, SyncState.COMMITTED)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        expected_total_entries = num_threads * num_ops_per_thread
        assert len(journal._entries) == expected_total_entries

        # Verify disk log contains all state updates
        with open(journal_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            # Each entry had 3 writes: PENDING, IDP_UPDATED, COMMITTED
            assert len(lines) == expected_total_entries * 3

    def test_process_restart_recovery(self, journal_path):
        """Verify that a newly instantiated journal recovers previous state accurately from disk."""
        # Process A: Write entries
        journal_a = RoleSyncJournal(log_path=str(journal_path))
        uid_1 = uuid.uuid4()
        uid_2 = uuid.uuid4()

        e1 = journal_a.record_intent(uid_1, "user", "admin")
        journal_a.update_state(e1.sync_id, SyncState.COMMITTED)

        e2 = journal_a.record_intent(uid_2, "admin", "user")
        journal_a.update_state(e2.sync_id, SyncState.DESYNCHRONIZED, error="Postgres failed and compensation failed")

        # Process B: Restart simulation (new instance reading existing file)
        journal_b = RoleSyncJournal(log_path=str(journal_path))
        recovered_e1 = journal_b.get_entry(e1.sync_id)
        recovered_e2 = journal_b.get_entry(e2.sync_id)

        assert recovered_e1 is not None
        assert recovered_e1.state == SyncState.COMMITTED.value
        assert recovered_e1.old_role == "user"
        assert recovered_e1.new_role == "admin"

        assert recovered_e2 is not None
        assert recovered_e2.state == SyncState.DESYNCHRONIZED.value
        assert recovered_e2.error == "Postgres failed and compensation failed"

        # Verify unreconciled query identifies the desynchronized entry
        unreconciled = journal_b.get_unreconciled_entries()
        assert len(unreconciled) == 1
        assert unreconciled[0].sync_id == e2.sync_id

    def test_resilience_to_corrupted_and_truncated_lines(self, journal_path):
        """Verify journal skips malformed or truncated JSON lines without failing valid records."""
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        valid_uid = str(uuid.uuid4())
        valid_sync_id = str(uuid.uuid4())
        valid_entry = {
            "sync_id": valid_sync_id,
            "user_id": valid_uid,
            "old_role": "user",
            "new_role": "admin",
            "state": "COMMITTED",
            "created_at": 1000.0,
            "updated_at": 1001.0,
            "error": None,
            "retry_count": 0,
        }

        # Write file with garbage lines, empty lines, and truncated JSON
        with open(journal_path, "w", encoding="utf-8") as f:
            f.write("GARBAGE NOT JSON LINE\n")
            f.write("\n")
            f.write(json.dumps(valid_entry) + "\n")
            f.write('{"truncated_json": true, "sync_id": "bad\n')
            f.write('{"invalid_type": 123}\n')  # Missing required fields

        journal = RoleSyncJournal(log_path=str(journal_path))
        # Should cleanly recover the single valid entry
        assert len(journal._entries) == 1
        assert valid_sync_id in journal._entries
        assert journal._entries[valid_sync_id].state == "COMMITTED"

    def test_resilience_when_disk_storage_fails(self, journal_path):
        """Verify that when disk writes fail (e.g. read-only filesystem), journal logs error and preserves in-memory state."""
        journal = RoleSyncJournal(log_path=str(journal_path))
        uid = uuid.uuid4()

        with patch("builtins.open", side_effect=OSError("Read-only file system or disk full")):
            # Must not raise an unhandled exception
            entry = journal.record_intent(uid, "user", "admin")
            assert entry is not None
            assert entry.sync_id in journal._entries
            assert journal.get_entry(entry.sync_id).state == SyncState.PENDING.value

            updated = journal.update_state(entry.sync_id, SyncState.COMMITTED)
            assert updated.state == SyncState.COMMITTED.value
            assert journal.get_entry(entry.sync_id).state == SyncState.COMMITTED.value

    def test_unreconciled_entries_lifecycle_filtering(self, journal_path):
        """Verify get_unreconciled_entries accurately distinguishes completed from pending/failed states."""
        journal = RoleSyncJournal(log_path=str(journal_path))

        e_pending = journal.record_intent(uuid.uuid4(), "user", "admin")
        e_committed = journal.record_intent(uuid.uuid4(), "user", "admin")
        journal.update_state(e_committed.sync_id, SyncState.COMMITTED)

        e_compensated = journal.record_intent(uuid.uuid4(), "user", "admin")
        journal.update_state(e_compensated.sync_id, SyncState.COMPENSATED)

        e_desync = journal.record_intent(uuid.uuid4(), "user", "admin")
        journal.update_state(e_desync.sync_id, SyncState.DESYNCHRONIZED)

        e_failed = journal.record_intent(uuid.uuid4(), "user", "admin")
        journal.update_state(e_failed.sync_id, SyncState.FAILED)

        unreconciled = journal.get_unreconciled_entries()
        unreconciled_ids = {e.sync_id for e in unreconciled}

        assert e_pending.sync_id in unreconciled_ids
        assert e_desync.sync_id in unreconciled_ids
        assert e_failed.sync_id in unreconciled_ids

        # Completed or compensated states must NOT be considered unreconciled
        assert e_committed.sync_id not in unreconciled_ids
        assert e_compensated.sync_id not in unreconciled_ids
