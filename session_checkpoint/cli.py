"""JSON-only command line interface for session-checkpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .core import (
    EXPORT_SCHEMA,
    DEFAULT_MAX_IMPORT_FILE_BYTES,
    SCHEMA_VERSION,
    CheckpointError,
    CheckpointStore,
    _restrict_private_file,
    prepare_checkpoint,
)


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _read_object(
    path: str | Path,
    *,
    label: str,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    source = Path(path).expanduser()
    if max_bytes is None:
        encoded = source.read_bytes()
    else:
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        with source.open("rb") as handle:
            encoded = handle.read(max_bytes + 1)
        if len(encoded) > max_bytes:
            raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")
    value = json.loads(encoded.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _atomic_json_write(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _restrict_private_file(temporary)
        os.replace(temporary, target)
        _restrict_private_file(target)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="session-checkpoint",
        description="Store application-neutral session checkpoints in a local SQLite database.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize or verify a checkpoint store")
    init.add_argument("--store", required=True)

    create = sub.add_parser("create", help="Create one checkpoint from a JSON object")
    create.add_argument("--store", required=True)
    create.add_argument("--namespace", default="default")
    create.add_argument("--session-id", required=True)
    create.add_argument("--payload-file", required=True)
    create.add_argument("--name")
    create.add_argument("--kind", default="manual")
    create.add_argument("--created-at")
    create.add_argument("--source-ref")
    create.add_argument("--dry-run", action="store_true")

    get = sub.add_parser("get", help="Return one checkpoint including its payload")
    get.add_argument("--store", required=True)
    get.add_argument("--namespace", default="default")
    get.add_argument("--id", required=True, type=int)

    listing = sub.add_parser("list", help="List checkpoint metadata without payloads")
    listing.add_argument("--store", required=True)
    listing.add_argument("--namespace", default="default")
    listing.add_argument("--limit", type=int, default=20)
    listing.add_argument("--offset", type=int, default=0)

    delete = sub.add_parser("delete", help="Plan deletion; mutation requires --apply")
    delete.add_argument("--store", required=True)
    delete.add_argument("--namespace", default="default")
    delete.add_argument("--id", required=True, type=int)
    delete.add_argument("--apply", action="store_true")

    export = sub.add_parser("export", help="Export checkpoints to a local JSON file")
    export.add_argument("--store", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--namespace")

    importer = sub.add_parser("import", help="Plan import; mutation requires --apply")
    importer.add_argument("--store", required=True)
    importer.add_argument("--input", required=True)
    importer.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create" and args.dry_run:
            payload = _read_object(args.payload_file, label="payload-file")
            prepared = prepare_checkpoint(
                namespace=args.namespace,
                session_id=args.session_id,
                payload=payload,
                name=args.name,
                kind=args.kind,
                created_at=args.created_at,
                source_ref=args.source_ref,
            )
            _print({"ok": True, "result": {"dry_run": True, "plan": prepared.plan()}})
            return 0

        store = CheckpointStore(args.store)
        if args.command == "init":
            result = {
                "store": str(store.path),
                "schema_version": SCHEMA_VERSION,
            }
        elif args.command == "create":
            payload = _read_object(args.payload_file, label="payload-file")
            result = store.create(
                namespace=args.namespace,
                session_id=args.session_id,
                payload=payload,
                name=args.name,
                kind=args.kind,
                created_at=args.created_at,
                source_ref=args.source_ref,
            ).as_dict()
        elif args.command == "get":
            result = store.get(args.id, namespace=args.namespace).as_dict()
        elif args.command == "list":
            result = [
                item.as_dict(include_payload=False)
                for item in store.list(
                    namespace=args.namespace,
                    limit=args.limit,
                    offset=args.offset,
                )
            ]
        elif args.command == "delete":
            item = store.delete(
                args.id,
                namespace=args.namespace,
                dry_run=not args.apply,
            )
            result = {
                "dry_run": not args.apply,
                "checkpoint": item.as_dict(include_payload=False),
                "deleted": [item.id] if args.apply else [],
            }
        elif args.command == "export":
            output = Path(args.output).expanduser().resolve()
            if output == store.path:
                raise ValueError("Export output must not overwrite the checkpoint store")
            bundle = store.export_bundle(namespace=args.namespace)
            written = _atomic_json_write(output, bundle)
            result = {
                "schema": EXPORT_SCHEMA,
                "output": str(written),
                "checkpoints": len(bundle["checkpoints"]),
            }
        elif args.command == "import":
            bundle = _read_object(
                args.input,
                label="input",
                max_bytes=DEFAULT_MAX_IMPORT_FILE_BYTES,
            )
            result = store.import_bundle(bundle, dry_run=not args.apply)
        else:
            raise AssertionError(args.command)
        _print({"ok": True, "result": result})
        return 0
    except (CheckpointError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        _print({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
