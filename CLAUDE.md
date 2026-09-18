---
name: "session-checkpoint"
type: project-docs
version: 0.1.1
created: "2026-08-08"
updated: "2026-09-18"
reason_last_change: "Path A repository hygiene, CI hardening, PEP 621 metadata, and contract test expansion"
last_verified: "2026-09-18"
author: "Lukas Geiger / ellmos-ai contributors"
description: |
  Agent instructions for the application-neutral session checkpoint carrier.
---

# CLAUDE.md — Project instructions

**Version:** 0.1.1
**Updated:** 2026-09-18
**Reason:** Initial private carrier implementation
**Purpose:** Preserve the narrow state, privacy, and compatibility boundary of this module.

> If you find stale guidance or misleading references, correct this file. If new work would not
> have been discoverable from the files you read, improve those files before finishing.

## Project boundary

This package stores immutable, application-provided session checkpoint payloads in a dedicated
local SQLite database. It does not collect application state, restore another application's
state, synchronize databases, call a network, or know BACH tables and paths.

## Required workflow

1. Read `START.md`, `STATE.md`, and `TODO.md`.
2. Respect active `LOCK*.txt` files and preserve foreign changes.
3. Run `python -m pytest -q` before and after code changes.
4. Keep the Python API and JSON-only CLI aligned.
5. Record state-format or compatibility decisions in `DECISIONS.md`.

## Hard rules

- The store must be a separate local SQLite file owned by this module.
- Payloads are JSON objects, canonicalized and verified by SHA-256 on every read.
- Namespace boundaries apply to get, list, and delete operations.
- Import conflicts fail before any row is written.
- CLI errors use JSON on stdout and do not emit tracebacks for expected failures.
- Delete and import remain dry-run by default; mutation needs explicit `--apply`.
- No user paths, host names, credentials, personal fixtures, or application databases are tracked.
- German end-user documentation uses real umlauts.
- Do not publish or make the repository public while `PRIVATE.txt` exists.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
