"""Cross-system role synchronization, consistency journal, and compensating recovery.

Provides reliable distributed consistency between PostgreSQL (`profiles.role`)
and the Supabase Auth GoTrue Admin API (`app_metadata.role`).
"""

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models.profile import Profile

logger = logging.getLogger("dharascope.auth.role_sync")


class SyncState(str, Enum):
    """Synchronization lifecycle states for distributed role updates."""
    PENDING = "PENDING"
    IDP_UPDATED = "IDP_UPDATED"
    COMMITTED = "COMMITTED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"
    DESYNCHRONIZED = "DESYNCHRONIZED"
    RECONCILED = "RECONCILED"


@dataclass
class RoleSyncJournalEntry:
    """Audit record capturing the intended role change and synchronization progress."""
    sync_id: str
    user_id: str
    old_role: str
    new_role: str
    state: str
    created_at: float
    updated_at: float
    error: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class RoleSyncJournal:
    """Thread-safe persistent journal of role updates and synchronization states.

    Persists entries to disk (JSONL format) so that incomplete or desynchronized
    transitions survive application restarts and are durable for reconciliation.
    """

    def __init__(self, log_path: Optional[str] = None):
        if log_path is None:
            log_path = os.getenv(
                "ROLE_SYNC_JOURNAL_PATH",
                "outputs/metadata/role_sync_audit.jsonl",
            )
        self.log_path = Path(log_path)
        self._lock = threading.Lock()
        self._entries: Dict[str, RoleSyncJournalEntry] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load historical entries from the persistence log if available."""
        if not self.log_path.exists():
            return
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        entry = RoleSyncJournalEntry(**raw)
                        self._entries[entry.sync_id] = entry
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning("Could not read role sync journal from %s: %s", self.log_path, exc)

    def _persist_entry_unlocked(self, entry: RoleSyncJournalEntry) -> None:
        """Append an entry to the disk log with explicit physical sync."""
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
        except Exception as exc:
            logger.error("Failed to append role sync journal entry %s to disk: %s", entry.sync_id, exc)

    def record_intent(
        self,
        user_id: uuid.UUID,
        old_role: str,
        new_role: str,
    ) -> RoleSyncJournalEntry:
        """Record the initiation of a distributed role change."""
        now = time.time()
        sync_id = str(uuid.uuid4())
        entry = RoleSyncJournalEntry(
            sync_id=sync_id,
            user_id=str(user_id),
            old_role=old_role,
            new_role=new_role,
            state=SyncState.PENDING.value,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._entries[sync_id] = entry
            self._persist_entry_unlocked(entry)
        return entry

    def update_state(
        self,
        sync_id: str,
        state: SyncState,
        error: Optional[str] = None,
    ) -> RoleSyncJournalEntry:
        """Advance the lifecycle state of a synchronization entry."""
        with self._lock:
            entry = self._entries.get(sync_id)
            if not entry:
                now = time.time()
                entry = RoleSyncJournalEntry(
                    sync_id=sync_id,
                    user_id="unknown",
                    old_role="unknown",
                    new_role="unknown",
                    state=state.value,
                    created_at=now,
                    updated_at=now,
                    error=error,
                )
                self._entries[sync_id] = entry
            else:
                entry.state = state.value
                entry.updated_at = time.time()
                if error:
                    entry.error = error
            self._persist_entry_unlocked(entry)
            return entry

    def get_entry(self, sync_id: str) -> Optional[RoleSyncJournalEntry]:
        """Retrieve a journal entry by its unique sync_id."""
        with self._lock:
            return self._entries.get(sync_id)

    def get_user_entries(self, user_id: uuid.UUID) -> List[RoleSyncJournalEntry]:
        """Retrieve all synchronization records for a specific user."""
        target_uid = str(user_id)
        with self._lock:
            return [e for e in self._entries.values() if e.user_id == target_uid]

    def get_unreconciled_entries(self) -> List[RoleSyncJournalEntry]:
        """Retrieve all records in an incomplete, desynchronized, or failed state."""
        unreconciled_states = {
            SyncState.PENDING.value,
            SyncState.IDP_UPDATED.value,
            SyncState.COMPENSATING.value,
            SyncState.DESYNCHRONIZED.value,
            SyncState.FAILED.value,
        }
        with self._lock:
            return [e for e in self._entries.values() if e.state in unreconciled_states]


# Global singleton instance of the role sync journal
_GLOBAL_JOURNAL: Optional[RoleSyncJournal] = None
_JOURNAL_LOCK = threading.Lock()


def get_role_sync_journal() -> RoleSyncJournal:
    """Obtain or initialize the global RoleSyncJournal."""
    global _GLOBAL_JOURNAL
    with _JOURNAL_LOCK:
        if _GLOBAL_JOURNAL is None:
            _GLOBAL_JOURNAL = RoleSyncJournal()
        return _GLOBAL_JOURNAL


def execute_reliable_role_update(
    session: Session,
    target_profile: Profile,
    new_role: str,
    timeout: float = 10.0,
    journal: Optional[RoleSyncJournal] = None,
) -> Profile:
    """Execute a reliable distributed role change across Supabase Auth and PostgreSQL.

    Implements a two-phase consistency strategy with compensating recovery:
    1. Idempotency Guard: If the role is unchanged, returns immediately.
    2. Intent Logging: Records PENDING in the journal before touching remote services.
    3. IdP Update: Pushes new_role to Supabase GoTrue Admin API.
       - On IdP failure: Marks FAILED, raises HTTPException; PostgreSQL is never modified.
    4. Database Commit: Updates `profiles.role` and flushes session.
    5. Compensating Recovery on DB Failure:
       - If PostgreSQL flush fails, catches error and marks COMPENSATING.
       - Dispatches a compensating update to Supabase Auth to restore `old_role`.
       - If compensation succeeds: Marks COMPENSATED, rolls back PostgreSQL session,
         and raises HTTP 500 (both systems remain consistent at `old_role`).
       - If compensation fails: Marks DESYNCHRONIZED, logs critical error,
         rolls back PostgreSQL, and raises HTTP 502 (desynchronization alert).
    6. Success: Marks COMMITTED and returns the updated profile.

    Raises:
        HTTPException(400): If role is invalid.
        HTTPException(500): On database failure with successful compensation.
        HTTPException(502): On Supabase communication or desynchronization failure.
    """
    from src.auth import sync_user_role_to_supabase

    if new_role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid application role '{new_role}'. Allowed roles: 'admin', 'user'.",
        )

    old_role = target_profile.role
    if new_role == old_role:
        # Idempotent no-op
        return target_profile

    j = journal or get_role_sync_journal()
    entry = j.record_intent(
        user_id=target_profile.id,
        old_role=old_role,
        new_role=new_role,
    )

    # Step 1: Synchronize with Supabase Auth GoTrue Admin API first
    try:
        sync_user_role_to_supabase(
            user_id=target_profile.id,
            new_role=new_role,
            timeout=timeout,
        )
        j.update_state(entry.sync_id, SyncState.IDP_UPDATED)
    except HTTPException as exc:
        j.update_state(entry.sync_id, SyncState.FAILED, error=f"Supabase sync failed: {exc.detail}")
        raise exc
    except Exception as exc:
        err_msg = f"Unexpected error during Supabase sync: {str(exc)}"
        j.update_state(entry.sync_id, SyncState.FAILED, error=err_msg)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with identity provider: {str(exc)}",
        ) from exc

    # Step 2: Apply, flush, and commit database changes
    try:
        target_profile.role = new_role
        session.flush()
        session.commit()
    except Exception as db_exc:
        logger.warning(
            "PostgreSQL commit/flush raised an exception for user %s: %s. "
            "Outcome is ambiguous; establishing authoritative database role via fresh session.",
            target_profile.id,
            db_exc,
        )

        # Roll back the failed/broken session to clean up connection state
        try:
            session.rollback()
        except Exception:
            pass

        # Step 3: Establish authoritative PostgreSQL role using a fresh database session
        authoritative_role: Optional[str] = None
        db_verification_failed = False
        verify_error: Optional[Exception] = None
        try:
            from src.database.session import get_session_factory
            bind = session.get_bind()
            factory = get_session_factory(bind) if bind is not None else get_session_factory()
            fresh_session = factory()
            try:
                fresh_profile = fresh_session.scalar(
                    select(Profile).where(Profile.id == target_profile.id)
                )
                if fresh_profile is not None:
                    authoritative_role = fresh_profile.role
            finally:
                fresh_session.close()
        except Exception as verify_exc:
            verify_error = verify_exc
            db_verification_failed = True
            logger.error(
                "Failed to query database for authoritative role verification for user %s: %s",
                target_profile.id,
                verify_exc,
            )

        # Case 1: PostgreSQL cannot be queried
        if db_verification_failed or authoritative_role is None:
            logger.critical(
                "CRITICAL: PostgreSQL cannot be queried after ambiguous commit for user %s. "
                "Recording DESYNCHRONIZED; not compensating blindly.",
                target_profile.id,
            )
            j.update_state(
                entry.sync_id,
                SyncState.DESYNCHRONIZED,
                error=(
                    f"PostgreSQL commit ambiguous ({str(db_exc)}); "
                    f"authoritative verification failed ({str(verify_error) if db_verification_failed else 'profile not found'})"
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "CRITICAL: PostgreSQL commit outcome is ambiguous and database is unavailable for verification. "
                    "Cannot verify whether role was committed. Manual administrator reconciliation required."
                ),
            ) from db_exc

        # Case 2: PostgreSQL contains new_role (Commit succeeded, but acknowledgement was lost)
        if authoritative_role == new_role:
            logger.info(
                "Authoritative role check confirmed PostgreSQL committed '%s' for user %s despite commit exception. "
                "Reconciling Supabase to '%s'.",
                new_role,
                target_profile.id,
                new_role,
            )
            try:
                sync_user_role_to_supabase(
                    user_id=target_profile.id,
                    new_role=new_role,
                    timeout=timeout,
                )
            except Exception as idp_exc:
                logger.critical(
                    "CRITICAL: PostgreSQL has '%s', but Supabase reconciliation to '%s' failed for user %s: %s",
                    new_role,
                    new_role,
                    target_profile.id,
                    idp_exc,
                )
                j.update_state(
                    entry.sync_id,
                    SyncState.DESYNCHRONIZED,
                    error=f"PostgreSQL committed {new_role}, but Supabase reconciliation failed: {str(idp_exc)}",
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "CRITICAL: PostgreSQL successfully committed new role, but identity provider reconciliation failed. "
                        "Manual administrator reconciliation required."
                    ),
                ) from idp_exc

            # Both PostgreSQL and Supabase confirmed to have new_role
            target_profile.role = new_role
            j.update_state(
                entry.sync_id,
                SyncState.RECONCILED,
                error=f"Commit acknowledged via fresh session query ({str(db_exc)}); reconciled IdP to {new_role}",
            )
            return target_profile

        # Case 3: PostgreSQL contains old_role (Commit definitely failed/rolled back)
        if authoritative_role == old_role:
            logger.info(
                "Authoritative role check confirmed PostgreSQL retained '%s' for user %s. "
                "Initiating compensating update to restore Supabase to '%s'.",
                old_role,
                target_profile.id,
                old_role,
            )
            j.update_state(
                entry.sync_id,
                SyncState.COMPENSATING,
                error=f"DB retained {old_role} ({str(db_exc)}); restoring IdP",
            )
            compensation_success = False
            comp_error: Optional[Exception] = None
            try:
                sync_user_role_to_supabase(
                    user_id=target_profile.id,
                    new_role=old_role,
                    timeout=timeout,
                )
                compensation_success = True
                logger.info(
                    "Compensating update succeeded: Restored Supabase role to '%s' for user %s",
                    old_role,
                    target_profile.id,
                )
            except Exception as comp_exc:
                comp_error = comp_exc
                logger.critical(
                    "CRITICAL: Compensating update to Supabase failed for user %s! "
                    "Supabase has '%s', PostgreSQL has '%s'. Error: %s",
                    target_profile.id,
                    new_role,
                    old_role,
                    comp_exc,
                )

            if compensation_success:
                target_profile.role = old_role
                j.update_state(
                    entry.sync_id,
                    SyncState.COMPENSATED,
                    error=f"DB failed ({str(db_exc)}); verified DB has {old_role} and compensated IdP back to {old_role}",
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "Database failure occurred while updating user profile. "
                        "Compensating rollback restored identity provider to previous role."
                    ),
                ) from db_exc
            else:
                j.update_state(
                    entry.sync_id,
                    SyncState.DESYNCHRONIZED,
                    error=f"DB retained {old_role} ({str(db_exc)}); compensating rollback to IdP failed: {str(comp_error)}",
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "CRITICAL: Cross-system role desynchronization detected. "
                        "Identity provider was updated but database commit and compensating rollback failed. "
                        "Manual administrator reconciliation required."
                    ),
                ) from db_exc

        # Case 4: PostgreSQL contains an unexpected role
        logger.critical(
            "CRITICAL: PostgreSQL contains unexpected role '%s' for user %s (expected '%s' or '%s').",
            authoritative_role,
            target_profile.id,
            old_role,
            new_role,
        )
        j.update_state(
            entry.sync_id,
            SyncState.DESYNCHRONIZED,
            error=f"PostgreSQL has unexpected role '{authoritative_role}'; expected '{old_role}' or '{new_role}'",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="CRITICAL: Unexpected database role state detected. Manual reconciliation required.",
        ) from db_exc

    # Step 4: Both systems successfully updated
    j.update_state(entry.sync_id, SyncState.COMMITTED)
    return target_profile


def reconcile_user_role(
    session: Session,
    user_id: uuid.UUID,
    timeout: float = 10.0,
    journal: Optional[RoleSyncJournal] = None,
) -> dict:
    """Idempotently reconcile authorization role between PostgreSQL and Supabase Auth.

    Treats the PostgreSQL `profiles.role` as authoritative when verified by an admin,
    and synchronizes any drift back to Supabase Auth.
    """
    from src.auth import sync_user_role_to_supabase

    profile = session.scalar(select(Profile).where(Profile.id == user_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' does not exist in local database",
        )

    target_role = profile.role
    j = journal or get_role_sync_journal()

    # Re-apply authoritative role to Supabase Auth
    sync_user_role_to_supabase(user_id=user_id, new_role=target_role, timeout=timeout)

    # Record reconciliation in journal
    now = time.time()
    sync_id = str(uuid.uuid4())
    entry = RoleSyncJournalEntry(
        sync_id=sync_id,
        user_id=str(user_id),
        old_role=target_role,
        new_role=target_role,
        state=SyncState.RECONCILED.value,
        created_at=now,
        updated_at=now,
    )
    with j._lock:
        for prev_entry in j._entries.values():
            if prev_entry.user_id == str(user_id) and prev_entry.state in {
                SyncState.DESYNCHRONIZED.value,
                SyncState.COMPENSATING.value,
                SyncState.FAILED.value,
                SyncState.PENDING.value,
                SyncState.IDP_UPDATED.value,
            }:
                prev_entry.state = SyncState.RECONCILED.value
                prev_entry.updated_at = now
                j._persist_entry_unlocked(prev_entry)
        j._entries[sync_id] = entry
        j._persist_entry_unlocked(entry)

    logger.info("Successfully reconciled role for user %s to '%s'", user_id, target_role)
    return {
        "user_id": str(user_id),
        "authoritative_role": target_role,
        "status": "reconciled",
        "sync_id": sync_id,
    }
