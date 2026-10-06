# DECISIONS.md — Architecture decisions

**Version:** 0.1
**Updated:** 2026-09-21
**Reason:** Bound imported IDs below the SQLite AUTOINCREMENT ceiling
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

## ADR-007: Bounded import and private local files

An import is validated before any database write and is bounded by record count and aggregate
canonical payload size. The CLI also bounds bytes before JSON parsing, preventing an oversized
local file from bypassing the core limits through whitespace or encoding expansion. Limits are
constructor parameters so an embedding application can make them stricter without forking the
carrier.

Stores and JSON exports may contain sensitive application context. They are created with
owner-only POSIX mode bits and rechecked after atomic replacement. On Windows, the carrier relies
on the containing directory's ACL and documents that boundary rather than claiming that
`os.chmod` configures Windows security descriptors.

## ADR-008: MIT licence, with publication still gated

The owner selected the MIT licence on 2026-08-22. The licence and package metadata therefore use
SPDX identifier `MIT`. This decision permits later distribution but does not make the repository
public, publish a package, create a tag, or satisfy the remaining integration and release gates in
`PRIVATE.txt`.

## ADR-009: Imported IDs preserve SQLite allocator headroom

Exports retain numeric local IDs so round trips stay deterministic, but imported IDs are untrusted
input to SQLite's signed 64-bit AUTOINCREMENT allocator. An imported maximum row ID permanently
exhausts future automatic allocation even if that row is deleted. Imports therefore reject IDs
above 2^62 - 1. This preserves half of the positive SQLite row-ID domain for later local creates
while leaving any practically reachable carrier ID portable.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
