# ARCHITECTURE.md — State and trust boundary

**Version:** 0.1
**Updated:** 2026-08-08
**Reason:** Initial carrier architecture
**Purpose:** Define ownership, data flow, invariants, and adapter seams.

## Data flow

```text
application collector -> JSON object -> CheckpointStore -> local checkpoint SQLite
application formatter <- verified JSON <- CheckpointStore <- local checkpoint SQLite
```

The collector and formatter are outside this package. The carrier never opens an application's
database and never interprets payload fields.

## State ownership

The module owns one configured SQLite file and the tables `checkpoint_meta` and `checkpoints`.
It refuses an existing SQLite file with any other application tables. A namespace is required
for every row-level operation, so one consumer cannot accidentally fetch or delete another
consumer's row by numeric ID alone.

## Checkpoint record

| Field | Contract |
|---|---|
| `id` | positive local integer, preserved by export/import |
| `namespace` | safe application token |
| `session_id` | opaque non-empty application session identifier |
| `kind` | safe application-defined token, default `manual` |
| `name` | human-readable local name |
| `payload` | JSON object, maximum 1 MiB by default |
| `payload_sha256` | SHA-256 of canonical UTF-8 JSON |
| `created_at` | timezone-aware ISO-8601 normalized to UTC |
| `source_ref` | optional unique reference within a namespace |

Payload hashes detect local corruption and bad migrations; they are not signatures and do not
authenticate an application or user.

## Mutation and recovery

- Create writes exactly one immutable row.
- Get and list verify canonical bytes and the stored hash before returning data.
- Delete is a dry-run unless the caller explicitly applies it.
- Import validates the entire bundle and checks all ID/source-reference conflicts before writing
  any row. Exact repeats are idempotent; differences fail closed.
- Export/import preserve IDs and payload hashes so migration and rollback can be compared.

## Adapter seam

An application adapter owns:

1. collecting current state into a JSON object,
2. choosing namespace, session ID, kind, name, and optional source reference,
3. mapping carrier errors to the application's public errors,
4. formatting loaded payloads for the user,
5. applying restored state, if the application ever defines a restore operation.

The carrier's `get` operation only materializes a checkpoint. It never claims to restore state.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
