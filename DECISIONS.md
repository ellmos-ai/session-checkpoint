# DECISIONS.md — Architecture decisions

**Version:** 0.1
**Updated:** 2026-08-08
**Reason:** Initial carrier decisions
**Purpose:** Preserve why the state boundary has this shape.

## ADR-001: Standalone capability instead of a chat-router extension

The live module catalogue has no `session.checkpoint` provider. Clutch owns chat and routing
sessions, MemoryHooker owns lifecycle search reminders, and sqlite-transit-sync owns database
transport. Making a neutral application checkpoint depend on any of them would cross a state
boundary for naming convenience. This carrier therefore has its own small API and local state.

## ADR-002: Dedicated SQLite file, never an application database

The carrier refuses unrelated tables rather than adding its schema to an application's database.
This gives the module one state owner, makes migration reversible, and prevents generic code from
guessing an application's schema or write lifecycle.

## ADR-003: JSON object plus canonical hash

A checkpoint is an application-defined object, not an untyped scalar or a database image.
Canonical JSON makes export comparisons deterministic. SHA-256 catches corruption but does not
claim sender authenticity.

## ADR-004: Numeric local IDs and source references

Numeric IDs preserve simple local CLI compatibility and can be retained during migration.
`source_ref` records a stable legacy or external identity without making it the primary key.
Both ID and source-reference collisions fail closed.

## ADR-005: Conservative destructive operations

Delete and import only plan by default. Explicit application code may pass `dry_run=False`; the
CLI requires `--apply`. Create is non-destructive and writes immediately unless `--dry-run` is
requested.

## ADR-006: Materialization is not restoration

The carrier returns stored payloads. It does not write tasks, memory, configuration, files, or
any other application state. If a later application defines restoration, that belongs in its
adapter and needs its own transaction and rollback contract.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
