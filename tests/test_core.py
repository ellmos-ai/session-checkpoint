from __future__ import annotations

import json
import os
import sqlite3
import stat

import pytest

from session_checkpoint import (
    CheckpointConflict,
    CheckpointNotFound,
    CheckpointStore,
    CheckpointValidationError,
    StoreSchemaError,
)


def test_create_get_list_and_namespace_isolation(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite")
    first = store.create(
        namespace="app-a",
        session_id="session-001",
        name="first",
        payload={"open_tasks": [{"id": 7, "title": "Synthetic task"}]},
        created_at="2026-08-08T07:00:00Z",
    )
    second = store.create(
        namespace="app-a",
        session_id="session-002",
        name="second",
        payload={"recent_memory": ["Synthetic note"]},
        created_at="2026-08-08T08:00:00Z",
    )
    store.create(
        namespace="app-b",
        session_id="session-003",
        name="foreign",
        payload={},
        created_at="2026-08-08T09:00:00Z",
    )

    assert store.get(first.id, namespace="app-a").payload["open_tasks"][0]["id"] == 7
    assert [item.id for item in store.list(namespace="app-a")] == [second.id, first.id]
    assert len(store.list(namespace="app-b")) == 1
    with pytest.raises(CheckpointNotFound):
        store.get(first.id, namespace="app-b")


def test_payload_is_canonical_and_must_be_an_object(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite")
    item = store.create(
        namespace="test",
        session_id="session-001",
        payload={"z": 1, "a": [2, 3]},
    )
    with sqlite3.connect(store.path) as connection:
        encoded = connection.execute(
            "SELECT payload_json FROM checkpoints WHERE id = ?", (item.id,)
        ).fetchone()[0]
    assert encoded == '{"a":[2,3],"z":1}'
    with pytest.raises(CheckpointValidationError, match="JSON object"):
        store.create(namespace="test", session_id="session-002", payload=["not", "object"])


def test_payload_limit_is_measured_in_utf8_bytes(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite", max_payload_bytes=20)
    with pytest.raises(CheckpointValidationError, match="carrier limit"):
        store.create(
            namespace="test",
            session_id="session-001",
            payload={"text": "ä" * 10},
        )


def test_source_reference_is_unique_per_namespace(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite")
    store.create(
        namespace="bach",
        session_id="session-001",
        payload={},
        source_ref="legacy:1",
    )
    with pytest.raises(CheckpointConflict):
        store.create(
            namespace="bach",
            session_id="session-002",
            payload={},
            source_ref="legacy:1",
        )
    store.create(
        namespace="other",
        session_id="session-002",
        payload={},
        source_ref="legacy:1",
    )


def test_delete_is_dry_run_by_default(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite")
    item = store.create(namespace="test", session_id="session-001", payload={})

    planned = store.delete(item.id, namespace="test")
    assert planned.id == item.id
    assert store.get(item.id, namespace="test").id == item.id

    deleted = store.delete(item.id, namespace="test", dry_run=False)
    assert deleted.id == item.id
    with pytest.raises(CheckpointNotFound):
        store.get(item.id, namespace="test")


def test_corrupt_payload_or_hash_fails_closed(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite")
    item = store.create(namespace="test", session_id="session-001", payload={"value": 1})
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE checkpoints SET payload_json = ? WHERE id = ?",
            ('{"value":2}', item.id),
        )
        connection.commit()
    with pytest.raises(StoreSchemaError, match="integrity"):
        store.get(item.id, namespace="test")


def test_refuses_an_unrelated_sqlite_database(tmp_path):
    path = tmp_path / "foreign.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
    with pytest.raises(StoreSchemaError, match="incompatible"):
        CheckpointStore(path)
    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert tables == {"unrelated"}


def test_export_import_round_trip_is_idempotent(tmp_path):
    source = CheckpointStore(tmp_path / "source.sqlite")
    first = source.create(
        namespace="bach",
        session_id="session-001",
        name="first",
        payload={"open_tasks": []},
        created_at="2026-08-08T07:00:00Z",
        source_ref="bach-session-snapshots:1",
    )
    second = source.create(
        namespace="bach",
        session_id="session-002",
        name="second",
        payload={"recent_memory": ["Synthetic"]},
        created_at="2026-08-08T08:00:00Z",
        source_ref="bach-session-snapshots:2",
    )
    bundle = source.export_bundle(namespace="bach")

    target = CheckpointStore(tmp_path / "target.sqlite")
    plan = target.import_bundle(bundle)
    assert plan == {"dry_run": True, "inserted": [first.id, second.id], "unchanged": []}
    assert target.list(namespace="bach") == []

    applied = target.import_bundle(bundle, dry_run=False)
    assert applied["inserted"] == [first.id, second.id]
    assert target.get(second.id, namespace="bach").payload["recent_memory"] == ["Synthetic"]

    repeated = target.import_bundle(bundle, dry_run=False)
    assert repeated == {
        "dry_run": False,
        "inserted": [],
        "unchanged": [first.id, second.id],
    }


def test_import_conflict_rolls_back_every_candidate(tmp_path):
    source = CheckpointStore(tmp_path / "source.sqlite")
    source.create(
        namespace="bach",
        session_id="session-001",
        payload={"value": "incoming"},
        created_at="2026-08-08T07:00:00Z",
    )
    source.create(
        namespace="bach",
        session_id="session-002",
        payload={"value": "second"},
        created_at="2026-08-08T08:00:00Z",
    )
    bundle = source.export_bundle(namespace="bach")

    target = CheckpointStore(tmp_path / "target.sqlite")
    target.create(
        namespace="bach",
        session_id="different",
        payload={"value": "existing"},
        created_at="2026-08-08T09:00:00Z",
    )
    with pytest.raises(CheckpointConflict):
        target.import_bundle(bundle, dry_run=False)
    assert len(target.list(namespace="bach")) == 1


def test_import_rejects_duplicate_source_references_before_writing(tmp_path):
    source = CheckpointStore(tmp_path / "source.sqlite")
    first = source.create(
        namespace="bach",
        session_id="session-001",
        payload={"value": "first"},
        source_ref="legacy:1",
    )
    second = source.create(
        namespace="bach",
        session_id="session-002",
        payload={"value": "second"},
        source_ref="legacy:2",
    )
    bundle = source.export_bundle()
    bundle["checkpoints"][1]["source_ref"] = first.source_ref

    target = CheckpointStore(tmp_path / "target.sqlite")
    with pytest.raises(CheckpointConflict, match="duplicate namespace/source_ref"):
        target.import_bundle(bundle, dry_run=False)
    assert target.list(namespace="bach") == []


def test_refuses_expected_table_names_with_wrong_columns(tmp_path):
    path = tmp_path / "lookalike.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE checkpoint_meta (key TEXT PRIMARY KEY, value TEXT)")
        connection.execute("CREATE TABLE checkpoints (id INTEGER PRIMARY KEY)")
    with pytest.raises(StoreSchemaError, match="Incompatible checkpoints columns"):
        CheckpointStore(path)


def test_export_is_json_serializable(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.sqlite")
    store.create(namespace="test", session_id="session-001", payload={"umlaut": "für"})
    encoded = json.dumps(store.export_bundle(), ensure_ascii=False)
    assert "für" in encoded


def test_import_rejects_too_many_checkpoints_before_writing(tmp_path):
    source = CheckpointStore(tmp_path / "source.sqlite")
    source.create(namespace="test", session_id="session-001", payload={"value": 1})
    source.create(namespace="test", session_id="session-002", payload={"value": 2})
    bundle = source.export_bundle()

    target = CheckpointStore(tmp_path / "target.sqlite", max_import_checkpoints=1)
    with pytest.raises(CheckpointValidationError, match="more than 1 checkpoints"):
        target.import_bundle(bundle, dry_run=False)
    assert target.list(namespace="test") == []


def test_import_rejects_aggregate_payload_bytes_before_writing(tmp_path):
    source = CheckpointStore(tmp_path / "source.sqlite")
    source.create(namespace="test", session_id="session-001", payload={"value": "one"})
    source.create(namespace="test", session_id="session-002", payload={"value": "two"})
    bundle = source.export_bundle()
    aggregate_bytes = sum(
        len(
            json.dumps(
                item["payload"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        for item in bundle["checkpoints"]
    )

    target = CheckpointStore(
        tmp_path / "target.sqlite",
        max_import_payload_bytes=aggregate_bytes - 1,
    )
    with pytest.raises(CheckpointValidationError, match="aggregate payload exceeds"):
        target.import_bundle(bundle, dry_run=False)
    assert target.list(namespace="test") == []

    boundary = CheckpointStore(
        tmp_path / "boundary.sqlite",
        max_import_payload_bytes=aggregate_bytes,
    )
    applied = boundary.import_bundle(bundle, dry_run=False)
    assert applied["inserted"] == [1, 2]


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are not Windows ACLs")
def test_store_and_export_are_private_files_on_posix(tmp_path):
    from session_checkpoint.cli import _atomic_json_write

    store = CheckpointStore(tmp_path / "store.sqlite")
    exported = _atomic_json_write(tmp_path / "export.json", {"checkpoints": []})

    assert stat.S_IMODE(store.path.stat().st_mode) & (stat.S_IRWXG | stat.S_IRWXO) == 0
    assert stat.S_IMODE(exported.stat().st_mode) & (stat.S_IRWXG | stat.S_IRWXO) == 0
