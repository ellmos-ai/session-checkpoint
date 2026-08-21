# Changelog

## Unreleased

- Added the owner-selected MIT licence and aligned package and release-gate metadata; publication
  remains separately gated.
- Kept metadata checks compatible with supported Python 3.10 via the conditional `tomli` fallback.
- Bounded create-payload files before JSON parsing while retaining the canonical payload limit.
- Added pinned cross-platform CI, build validation, CLI smoke coverage, and non-uploading CodeQL
  analysis for the private readiness phase.
- Added repository metadata, a structured TODO status register, and the shared release-ignore
  baseline including ephemeral lock files.

## 0.1.0 — 2026-08-08

- Added module-owned SQLite checkpoint storage.
- Added Python API and JSON-only CLI for create, get, list, and delete.
- Added canonical payload hashing, namespace isolation, and source-reference uniqueness.
- Added dry-run-first delete/import plus reversible export/import.
- Added bounded import count, aggregate payload, and CLI input size.
- Added owner-only POSIX creation for stores and atomic JSON exports, with an explicit Windows ACL
  boundary.
- Added synthetic tests and private release gate.
