from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "session_checkpoint", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(result.stdout)
    return result, payload


def test_cli_create_list_get_and_conservative_delete(tmp_path):
    store = tmp_path / "store.sqlite"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "session_id": "session-001",
                "open_tasks": [{"id": 1, "title": "Synthetic task"}],
                "recent_memory": ["Synthetic note"],
            }
        ),
        encoding="utf-8",
    )

    result, created = run_cli(
        "create",
        "--store",
        str(store),
        "--namespace",
        "bach",
        "--session-id",
        "session-001",
        "--name",
        "checkpoint-one",
        "--payload-file",
        str(payload_path),
    )
    assert result.returncode == 0
    assert result.stderr == ""
    checkpoint_id = created["result"]["id"]

    result, listing = run_cli(
        "list", "--store", str(store), "--namespace", "bach"
    )
    assert result.returncode == 0
    assert listing["result"][0]["name"] == "checkpoint-one"
    assert "payload" not in listing["result"][0]

    result, fetched = run_cli(
        "get", "--store", str(store), "--namespace", "bach", "--id", str(checkpoint_id)
    )
    assert result.returncode == 0
    assert fetched["result"]["payload"]["open_tasks"][0]["id"] == 1

    result, planned = run_cli(
        "delete", "--store", str(store), "--namespace", "bach", "--id", str(checkpoint_id)
    )
    assert result.returncode == 0
    assert planned["result"]["dry_run"] is True
    assert planned["result"]["deleted"] == []

    result, applied = run_cli(
        "delete",
        "--store",
        str(store),
        "--namespace",
        "bach",
        "--id",
        str(checkpoint_id),
        "--apply",
    )
    assert result.returncode == 0
    assert applied["result"]["deleted"] == [checkpoint_id]


def test_cli_create_dry_run_does_not_create_store(tmp_path):
    store = tmp_path / "store.sqlite"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text("{}", encoding="utf-8")
    result, payload = run_cli(
        "create",
        "--store",
        str(store),
        "--session-id",
        "session-001",
        "--payload-file",
        str(payload_path),
        "--dry-run",
    )
    assert result.returncode == 0
    assert payload["result"]["dry_run"] is True
    assert not store.exists()


def test_cli_scalar_payload_is_json_error_without_traceback(tmp_path):
    store = tmp_path / "store.sqlite"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text("7", encoding="utf-8")
    result, payload = run_cli(
        "create",
        "--store",
        str(store),
        "--session-id",
        "session-001",
        "--payload-file",
        str(payload_path),
    )
    assert result.returncode == 1
    assert result.stderr == ""
    assert payload["ok"] is False
    assert "JSON object" in payload["error"]


def test_cli_export_import_round_trip(tmp_path):
    source = tmp_path / "source.sqlite"
    target = tmp_path / "target.sqlite"
    payload_path = tmp_path / "payload.json"
    export_path = tmp_path / "export.json"
    payload_path.write_text('{"value":"synthetic"}', encoding="utf-8")
    result, _ = run_cli(
        "create",
        "--store",
        str(source),
        "--namespace",
        "bach",
        "--session-id",
        "session-001",
        "--payload-file",
        str(payload_path),
    )
    assert result.returncode == 0
    result, exported = run_cli(
        "export",
        "--store",
        str(source),
        "--namespace",
        "bach",
        "--output",
        str(export_path),
    )
    assert result.returncode == 0
    assert exported["result"]["checkpoints"] == 1

    result, planned = run_cli(
        "import", "--store", str(target), "--input", str(export_path)
    )
    assert result.returncode == 0
    assert planned["result"]["dry_run"] is True
    result, applied = run_cli(
        "import", "--store", str(target), "--input", str(export_path), "--apply"
    )
    assert result.returncode == 0
    assert applied["result"]["inserted"] == [1]
