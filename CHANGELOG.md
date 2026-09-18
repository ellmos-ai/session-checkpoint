# Changelog

## 0.1.1 — 2026-09-18

- Added CI workflow concurrency controls with `cancel-in-progress: true` (`ci.yml`, `codeql.yml`).
- Hardened Pytest configuration with `minversion = "7.0"`, `addopts = "-ra -q"`, and `norecursedirs` in `pyproject.toml`.
- Expanded PEP 621 URLs in `pyproject.toml` (`Documentation`, `Changelog`).
- Hardened `.gitignore` against multi-host cloud-sync conflicts, lock files, and test caches.
- Synchronized version 0.1.1 across all package manifests (`pyproject.toml`, `session_checkpoint/__init__.py`, `ellmos-module.v2.json`, `llms.txt`, and documentation).
- Expanded automated metadata test suite (`tests/test_metadata.py`) with contract tests for CI concurrency, Pytest options, cloud-sync ignore patterns, and cross-manifest version consistency.
- Added `llms.txt` documenting system invariants, CLI commands, and Python API for AI discoverability.
- Added standard PEP 621 metadata classifiers and homepage URL in `pyproject.toml`.
- Added Plan-D pointer and aligned repository mirror parity with `.TOPICS/.AI/.MODULES/.RUNTIME`.

## 0.1.0 — 2026-08-08

- Added module-owned SQLite checkpoint storage.
- Added Python API and JSON-only CLI for create, get, list, and delete.
- Added canonical payload hashing, namespace isolation, and source-reference uniqueness.
- Added dry-run-first delete/import plus reversible export/import.
- Added bounded import count, aggregate payload, and CLI input size.
- Added owner-only POSIX creation for stores and atomic JSON exports, with an explicit Windows ACL
  boundary.
- Added synthetic tests and private release gate.
