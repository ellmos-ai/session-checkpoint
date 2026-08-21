"""Local, application-neutral session checkpoint storage."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1
EXPORT_SCHEMA = "ellmos.session-checkpoint-export.v1"
DEFAULT_MAX_PAYLOAD_BYTES = 1024 * 1024
DEFAULT_MAX_IMPORT_CHECKPOINTS = 1000
DEFAULT_MAX_IMPORT_PAYLOAD_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_IMPORT_FILE_BYTES = 32 * 1024 * 1024
_PRIVATE_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR
_TOKEN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,127})?\Z")
_EXPECTED_TABLES = {"checkpoint_meta", "checkpoints"}
_EXPECTED_COLUMNS = {
    "checkpoint_meta": {"key", "value"},
    "checkpoints": {
        "id",
        "namespace",
        "session_id",
        "kind",
        "name",
        "payload_json",
        "payload_sha256",
        "created_at",
        "source_ref",
    },
}


class CheckpointError(RuntimeError):
    """Base class for expected carrier failures."""


class CheckpointValidationError(CheckpointError):
    """Input or stored checkpoint data does not satisfy the public contract."""


class CheckpointNotFound(CheckpointError):
    """The requested checkpoint does not exist in the requested namespace."""


class CheckpointConflict(CheckpointError):
    """An import or source reference conflicts with existing state."""


class StoreSchemaError(CheckpointError):
    """The configured SQLite file is not a compatible checkpoint store."""


class StoreSecurityError(CheckpointError):
    """A sensitive carrier file could not be restricted to its owner on POSIX."""


def _restrict_private_file(path: Path) -> None:
    """Apply and verify owner-only POSIX mode bits.

    Windows ACLs are inherited from the containing directory and cannot be represented by
    ``os.chmod``. Callers must therefore place stores and exports in an ACL-protected directory
    on Windows.
    """

    if os.name != "posix":
        return
    try:
        path.chmod(_PRIVATE_FILE_MODE)
        actual_mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as error:
        raise StoreSecurityError(f"Could not restrict sensitive file {path}: {error}") from error
    if actual_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise StoreSecurityError(
            f"Sensitive file {path} has non-private POSIX mode {oct(actual_mode)}"
        )


def _create_private_file(path: Path) -> bool:
    """Create an empty owner-only file without following a pre-existing path."""

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        descriptor = os.open(path, flags, _PRIVATE_FILE_MODE)
    except FileExistsError:
        return False
    try:
        os.close(descriptor)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    _restrict_private_file(path)
    return True


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_token(field: str, value: Any) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise CheckpointValidationError(
            f"{field} must match {_TOKEN_RE.pattern!r} and be at most 128 characters"
        )
    return value


def _normalize_text(field: str, value: Any, *, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise CheckpointValidationError(
            f"{field} must be a non-empty string of at most {maximum} characters"
        )
    if any(ord(character) < 32 for character in value):
        raise CheckpointValidationError(f"{field} must not contain control characters")
    return value


def _normalize_optional_text(field: str, value: Any, *, maximum: int) -> str | None:
    if value is None:
        return None
    return _normalize_text(field, value, maximum=maximum)


def _positive_int(field: str, value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise CheckpointValidationError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(field: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise CheckpointValidationError(f"{field} must be a non-negative integer")
    return value


def _normalize_created_at(value: Any | None) -> str:
    if value is None:
        return _utc_now()
    if not isinstance(value, str):
        raise CheckpointValidationError("created_at must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CheckpointValidationError("created_at must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise CheckpointValidationError("created_at must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_payload(payload: Any, *, max_payload_bytes: int) -> tuple[dict[str, Any], str, str]:
    if not isinstance(payload, dict):
        raise CheckpointValidationError("payload must be a JSON object")
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise CheckpointValidationError(f"payload is not valid JSON: {error}") from error
    payload_bytes = encoded.encode("utf-8")
    if len(payload_bytes) > max_payload_bytes:
        raise CheckpointValidationError(
            f"payload exceeds the {max_payload_bytes}-byte carrier limit"
        )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return json.loads(encoded), encoded, digest


@dataclass(frozen=True, slots=True)
class PreparedCheckpoint:
    namespace: str
    session_id: str
    kind: str
    name: str
    payload: dict[str, Any]
    payload_json: str
    payload_sha256: str
    created_at: str
    source_ref: str | None

    def plan(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "session_id": self.session_id,
            "kind": self.kind,
            "name": self.name,
            "payload_sha256": self.payload_sha256,
            "payload_bytes": len(self.payload_json.encode("utf-8")),
            "created_at": self.created_at,
            "source_ref": self.source_ref,
        }


def prepare_checkpoint(
    *,
    namespace: str,
    session_id: str,
    payload: Any,
    name: str | None = None,
    kind: str = "manual",
    created_at: str | None = None,
    source_ref: str | None = None,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
) -> PreparedCheckpoint:
    """Validate and canonicalize checkpoint input without touching a store."""

    _positive_int("max_payload_bytes", max_payload_bytes)
    normalized_created_at = _normalize_created_at(created_at)
    normalized_name = name or "checkpoint_" + normalized_created_at.replace(":", "").replace("-", "")
    normalized_payload, payload_json, digest = _canonical_payload(
        payload, max_payload_bytes=max_payload_bytes
    )
    return PreparedCheckpoint(
        namespace=_normalize_token("namespace", namespace),
        session_id=_normalize_text("session_id", session_id, maximum=512),
        kind=_normalize_token("kind", kind),
        name=_normalize_text("name", normalized_name, maximum=256),
        payload=normalized_payload,
        payload_json=payload_json,
        payload_sha256=digest,
        created_at=normalized_created_at,
        source_ref=_normalize_optional_text("source_ref", source_ref, maximum=256),
    )


@dataclass(frozen=True, slots=True)
class Checkpoint:
    id: int
    namespace: str
    session_id: str
    kind: str
    name: str
    payload: dict[str, Any]
    payload_sha256: str
    created_at: str
    source_ref: str | None = None

    def as_dict(self, *, include_payload: bool = True) -> dict[str, Any]:
        result = asdict(self)
        if not include_payload:
            result.pop("payload")
        return result


class CheckpointStore:
    """Owns checkpoint rows in one local SQLite database."""

    def __init__(
        self,
        path: str | Path,
        *,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        max_import_checkpoints: int = DEFAULT_MAX_IMPORT_CHECKPOINTS,
        max_import_payload_bytes: int = DEFAULT_MAX_IMPORT_PAYLOAD_BYTES,
    ):
        self.path = Path(path).expanduser().resolve()
        self.max_payload_bytes = _positive_int("max_payload_bytes", max_payload_bytes)
        self.max_import_checkpoints = _positive_int(
            "max_import_checkpoints", max_import_checkpoints
        )
        self.max_import_payload_bytes = _positive_int(
            "max_import_payload_bytes", max_import_payload_bytes
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _create_private_file(self.path)
        self._initialize()
        _restrict_private_file(self.path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            if tables and tables != _EXPECTED_TABLES:
                raise StoreSchemaError(
                    f"Refusing incompatible SQLite file {self.path}; tables={sorted(tables)}"
                )
            if not tables:
                with connection:
                    connection.executescript(
                        """
                        CREATE TABLE checkpoint_meta (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL
                        );
                        CREATE TABLE checkpoints (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            namespace TEXT NOT NULL,
                            session_id TEXT NOT NULL,
                            kind TEXT NOT NULL,
                            name TEXT NOT NULL,
                            payload_json TEXT NOT NULL,
                            payload_sha256 TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            source_ref TEXT,
                            UNIQUE(namespace, source_ref)
                        );
                        CREATE INDEX idx_checkpoints_namespace_created
                            ON checkpoints(namespace, created_at DESC, id DESC);
                        PRAGMA user_version = 1;
                        """
                    )
                    connection.execute(
                        "INSERT INTO checkpoint_meta (key, value) VALUES ('schema_version', ?)",
                        (str(SCHEMA_VERSION),),
                    )
            for table, expected_columns in _EXPECTED_COLUMNS.items():
                actual_columns = {
                    row[1]
                    for row in connection.execute(f"PRAGMA table_info([{table}])").fetchall()
                }
                if actual_columns != expected_columns:
                    raise StoreSchemaError(
                        f"Incompatible {table} columns in {self.path}: "
                        f"expected={sorted(expected_columns)}, actual={sorted(actual_columns)}"
                    )
            row = connection.execute(
                "SELECT value FROM checkpoint_meta WHERE key = 'schema_version'"
            ).fetchone()
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            if row is None or row[0] != str(SCHEMA_VERSION) or user_version != SCHEMA_VERSION:
                raise StoreSchemaError(
                    f"Unsupported checkpoint store schema in {self.path}: "
                    f"meta={row[0] if row else None}, user_version={user_version}"
                )

    def _row_to_checkpoint(self, row: sqlite3.Row) -> Checkpoint:
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError) as error:
            raise StoreSchemaError(f"Checkpoint {row['id']} contains invalid JSON") from error
        _, encoded, digest = _canonical_payload(
            payload, max_payload_bytes=self.max_payload_bytes
        )
        if encoded != row["payload_json"] or digest != row["payload_sha256"]:
            raise StoreSchemaError(f"Checkpoint {row['id']} failed payload integrity verification")
        return Checkpoint(
            id=_positive_int("id", row["id"]),
            namespace=_normalize_token("namespace", row["namespace"]),
            session_id=_normalize_text("session_id", row["session_id"], maximum=512),
            kind=_normalize_token("kind", row["kind"]),
            name=_normalize_text("name", row["name"], maximum=256),
            payload=payload,
            payload_sha256=row["payload_sha256"],
            created_at=_normalize_created_at(row["created_at"]),
            source_ref=_normalize_optional_text("source_ref", row["source_ref"], maximum=256),
        )

    def create(
        self,
        *,
        namespace: str,
        session_id: str,
        payload: Any,
        name: str | None = None,
        kind: str = "manual",
        created_at: str | None = None,
        source_ref: str | None = None,
    ) -> Checkpoint:
        prepared = prepare_checkpoint(
            namespace=namespace,
            session_id=session_id,
            payload=payload,
            name=name,
            kind=kind,
            created_at=created_at,
            source_ref=source_ref,
            max_payload_bytes=self.max_payload_bytes,
        )
        try:
            with self._connection() as connection, connection:
                cursor = connection.execute(
                    """
                    INSERT INTO checkpoints
                        (namespace, session_id, kind, name, payload_json,
                         payload_sha256, created_at, source_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prepared.namespace,
                        prepared.session_id,
                        prepared.kind,
                        prepared.name,
                        prepared.payload_json,
                        prepared.payload_sha256,
                        prepared.created_at,
                        prepared.source_ref,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM checkpoints WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
        except sqlite3.IntegrityError as error:
            raise CheckpointConflict(
                f"source_ref already exists in namespace {prepared.namespace!r}"
            ) from error
        if row is None:
            raise StoreSchemaError("Created checkpoint could not be read back")
        return self._row_to_checkpoint(row)

    def get(self, checkpoint_id: int, *, namespace: str = "default") -> Checkpoint:
        checkpoint_id = _positive_int("checkpoint_id", checkpoint_id)
        namespace = _normalize_token("namespace", namespace)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM checkpoints WHERE id = ? AND namespace = ?",
                (checkpoint_id, namespace),
            ).fetchone()
        if row is None:
            raise CheckpointNotFound(
                f"Checkpoint {checkpoint_id} not found in namespace {namespace!r}"
            )
        return self._row_to_checkpoint(row)

    def list(
        self,
        *,
        namespace: str = "default",
        limit: int = 20,
        offset: int = 0,
    ) -> list[Checkpoint]:
        namespace = _normalize_token("namespace", namespace)
        limit = _positive_int("limit", limit)
        offset = _nonnegative_int("offset", offset)
        if limit > 1000:
            raise CheckpointValidationError("limit must not exceed 1000")
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM checkpoints
                WHERE namespace = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (namespace, limit, offset),
            ).fetchall()
        return [self._row_to_checkpoint(row) for row in rows]

    def delete(
        self,
        checkpoint_id: int,
        *,
        namespace: str = "default",
        dry_run: bool = True,
    ) -> Checkpoint:
        checkpoint = self.get(checkpoint_id, namespace=namespace)
        if dry_run:
            return checkpoint
        with self._connection() as connection, connection:
            cursor = connection.execute(
                "DELETE FROM checkpoints WHERE id = ? AND namespace = ?",
                (checkpoint.id, checkpoint.namespace),
            )
            if cursor.rowcount != 1:
                raise CheckpointNotFound(
                    f"Checkpoint {checkpoint.id} disappeared before deletion"
                )
        return checkpoint

    def export_bundle(self, *, namespace: str | None = None) -> dict[str, Any]:
        params: tuple[Any, ...] = ()
        where = ""
        if namespace is not None:
            namespace = _normalize_token("namespace", namespace)
            where = "WHERE namespace = ?"
            params = (namespace,)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM checkpoints {where} ORDER BY id ASC", params
            ).fetchall()
        checkpoints = [self._row_to_checkpoint(row).as_dict() for row in rows]
        return {
            "schema": EXPORT_SCHEMA,
            "store_schema_version": SCHEMA_VERSION,
            "exported_at": _utc_now(),
            "namespace": namespace,
            "checkpoints": checkpoints,
        }

    def _checkpoint_from_export(self, item: Any) -> Checkpoint:
        if not isinstance(item, dict):
            raise CheckpointValidationError("Every imported checkpoint must be an object")
        required = {
            "id",
            "namespace",
            "session_id",
            "kind",
            "name",
            "payload",
            "payload_sha256",
            "created_at",
            "source_ref",
        }
        if set(item) != required:
            raise CheckpointValidationError(
                f"Imported checkpoint fields must be exactly {sorted(required)}"
            )
        prepared = prepare_checkpoint(
            namespace=item["namespace"],
            session_id=item["session_id"],
            payload=item["payload"],
            name=item["name"],
            kind=item["kind"],
            created_at=item["created_at"],
            source_ref=item["source_ref"],
            max_payload_bytes=self.max_payload_bytes,
        )
        if item["payload_sha256"] != prepared.payload_sha256:
            raise CheckpointValidationError(
                f"Imported checkpoint {item.get('id')} has a payload hash mismatch"
            )
        return Checkpoint(
            id=_positive_int("id", item["id"]),
            namespace=prepared.namespace,
            session_id=prepared.session_id,
            kind=prepared.kind,
            name=prepared.name,
            payload=prepared.payload,
            payload_sha256=prepared.payload_sha256,
            created_at=prepared.created_at,
            source_ref=prepared.source_ref,
        )

    def import_bundle(self, bundle: Any, *, dry_run: bool = True) -> dict[str, Any]:
        if not isinstance(bundle, dict):
            raise CheckpointValidationError("Import bundle must be an object")
        if bundle.get("schema") != EXPORT_SCHEMA:
            raise CheckpointValidationError("Unsupported checkpoint export schema")
        if bundle.get("store_schema_version") != SCHEMA_VERSION:
            raise CheckpointValidationError("Unsupported checkpoint store schema version")
        raw_items = bundle.get("checkpoints")
        if not isinstance(raw_items, list):
            raise CheckpointValidationError("Import bundle checkpoints must be an array")
        if len(raw_items) > self.max_import_checkpoints:
            raise CheckpointValidationError(
                f"Import bundle contains more than {self.max_import_checkpoints} checkpoints"
            )
        candidates: list[Checkpoint] = []
        aggregate_payload_bytes = 0
        for raw_item in raw_items:
            candidate = self._checkpoint_from_export(raw_item)
            encoded_payload = json.dumps(
                candidate.payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            aggregate_payload_bytes += len(encoded_payload)
            if aggregate_payload_bytes > self.max_import_payload_bytes:
                raise CheckpointValidationError(
                    "Import bundle aggregate payload exceeds the "
                    f"{self.max_import_payload_bytes}-byte carrier limit"
                )
            candidates.append(candidate)
        ids = [item.id for item in candidates]
        if len(ids) != len(set(ids)):
            raise CheckpointConflict("Import bundle contains duplicate checkpoint ids")
        source_refs = [
            (item.namespace, item.source_ref)
            for item in candidates
            if item.source_ref is not None
        ]
        if len(source_refs) != len(set(source_refs)):
            raise CheckpointConflict("Import bundle contains duplicate namespace/source_ref pairs")

        inserted: list[int] = []
        unchanged: list[int] = []
        with self._connection() as connection:
            for candidate in candidates:
                existing_row = connection.execute(
                    "SELECT * FROM checkpoints WHERE id = ?", (candidate.id,)
                ).fetchone()
                if existing_row is not None:
                    existing = self._row_to_checkpoint(existing_row)
                    if existing != candidate:
                        raise CheckpointConflict(
                            f"Checkpoint id {candidate.id} conflicts with existing state"
                        )
                    unchanged.append(candidate.id)
                    continue
                if candidate.source_ref is not None:
                    ref_row = connection.execute(
                        """
                        SELECT id FROM checkpoints
                        WHERE namespace = ? AND source_ref = ?
                        """,
                        (candidate.namespace, candidate.source_ref),
                    ).fetchone()
                    if ref_row is not None:
                        raise CheckpointConflict(
                            f"source_ref {candidate.source_ref!r} conflicts in namespace "
                            f"{candidate.namespace!r}"
                        )
                inserted.append(candidate.id)

            if not dry_run:
                try:
                    with connection:
                        for candidate in candidates:
                            if candidate.id in unchanged:
                                continue
                            payload_json = json.dumps(
                                candidate.payload,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                                allow_nan=False,
                            )
                            connection.execute(
                                """
                                INSERT INTO checkpoints
                                    (id, namespace, session_id, kind, name, payload_json,
                                     payload_sha256, created_at, source_ref)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    candidate.id,
                                    candidate.namespace,
                                    candidate.session_id,
                                    candidate.kind,
                                    candidate.name,
                                    payload_json,
                                    candidate.payload_sha256,
                                    candidate.created_at,
                                    candidate.source_ref,
                                ),
                            )
                except sqlite3.IntegrityError as error:
                    raise CheckpointConflict(
                        "Checkpoint import conflicted with state changed during apply"
                    ) from error
        return {
            "dry_run": dry_run,
            "inserted": inserted,
            "unchanged": unchanged,
        }
