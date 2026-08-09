# Changelog

## 0.1.0 — 2026-08-08

- Added module-owned SQLite checkpoint storage.
- Added Python API and JSON-only CLI for create, get, list, and delete.
- Added canonical payload hashing, namespace isolation, and source-reference uniqueness.
- Added dry-run-first delete/import plus reversible export/import.
- Added bounded import count, aggregate payload, and CLI input size.
- Added owner-only POSIX creation for stores and atomic JSON exports, with an explicit Windows ACL
  boundary.
- Added synthetic tests and private release gate.
