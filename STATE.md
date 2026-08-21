---
name: "session-checkpoint-state"
type: project-state
version: 0.1.0
updated: 2026-08-21
last_verified: 2026-08-21
description: "Current verified project state and claim boundary."
---

# STATE.md — Current state

**Version:** 0.1
**Updated:** 2026-08-21
**Reason:** Private public-readiness and bounded create-input hardening
**Purpose:** State what exists, what is proven, and what remains open.

## Implemented

- Local SQLite checkpoint store with module-owned schema version 1.
- Create, get, list, and conservative delete through Python and JSON CLI.
- Canonical JSON-object payloads with SHA-256 verification on read.
- Namespace isolation and unique application source references.
- Reversible JSON export/import with dry-run and fail-closed conflict preflight.
- Bounded import count, aggregate payload, and CLI input-file size.
- Bounded create-payload files before JSON parsing.
- Owner-only POSIX file creation and explicit Windows directory-ACL boundary.
- No network access and no application-specific state collection.
- Pinned cross-platform CI and non-uploading CodeQL workflows for private verification.

## Claim boundary

This is a neutral carrier. It is not a BACH adapter, BACH parity evidence, a session restorer, a
database synchronizer, an installer, a bundle, or an off-host acceptance test.

## Next

Pin the first verified commit in open-ocean's K9 contract and exercise the carrier with the
anonymized BACH-shaped checkpoint fixture. BACH integration waits until the judging hold ends.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
