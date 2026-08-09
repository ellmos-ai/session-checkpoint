# session-checkpoint

Local, application-neutral session checkpoint storage for Python and JSON-speaking tools.

*[Deutsch](README_de.md)*

> **Private build.** This carrier was created for open-ocean's K9 session-checkpoint gap. It is
> deliberately not public or packaged while its integration and release gates remain open.

## What it does

- Stores application-provided checkpoint payloads in a dedicated local SQLite database.
- Exposes create, get, list, and conservative delete through a Python API and JSON-only CLI.
- Canonicalizes JSON-object payloads and verifies their SHA-256 on every read.
- Separates applications by namespace and protects imported source references from collision.
- Exports and imports complete local checkpoint sets for migration and rollback tests.
- Bounds imports to 1,000 checkpoints, 16 MiB aggregate canonical payload, and a 32 MiB CLI
  input file by default; Python callers can choose stricter carrier limits.

## What it does not do

The carrier does not inspect application tables, collect tasks or memory, restore application
state, synchronize databases, call a network, or decide what belongs in a checkpoint. Those are
adapter and application responsibilities. Similar words do not make database snapshots and
session checkpoints the same state.

## Install for development

```shell
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Python API

```python
from session_checkpoint import CheckpointStore

store = CheckpointStore("local-checkpoints.sqlite")
created = store.create(
    namespace="example-app",
    session_id="session-001",
    name="before-upgrade",
    payload={"open_items": [{"id": 1, "title": "Synthetic item"}]},
)
loaded = store.get(created.id, namespace="example-app")
```

`payload` must be a JSON object. The application assembles it before calling the carrier and
interprets it after retrieval.

## JSON CLI

```shell
session-checkpoint create \
  --store local-checkpoints.sqlite \
  --namespace example-app \
  --session-id session-001 \
  --name before-upgrade \
  --payload-file payload.json

session-checkpoint list --store local-checkpoints.sqlite --namespace example-app
session-checkpoint get --store local-checkpoints.sqlite --namespace example-app --id 1

# Deletion is only planned by default.
session-checkpoint delete --store local-checkpoints.sqlite --namespace example-app --id 1
session-checkpoint delete --store local-checkpoints.sqlite --namespace example-app --id 1 --apply
```

Expected CLI failures return exit code 1 and a JSON object on stdout. Export writes payloads to an
explicit local file; treat that file as sensitive application data. On POSIX, new stores and
exports are created with owner-only mode bits and compatible existing stores are restricted on
open. On Windows, place them in a directory whose ACL grants access only to the intended account;
Python mode bits do not configure Windows ACLs.

## Status and release

Version 0.1.0 is a private integration build. See `STATE.md`, `ARCHITECTURE.md`, and
`PRIVATE.txt`. No licence or public package release has been approved yet.
