# Third-Party Licenses & Transparency — session-checkpoint

> Comprehensive Level 1 Software Bill of Materials (SBOM) and license audit for `session-checkpoint` (ellmos-ai / open-bricks).
> Stand: 2026-09-22.

---

## 1. Project License & Attribution

`session-checkpoint` is published under the **MIT License**.
See [LICENSE](LICENSE) and [NOTICE](NOTICE) for full attribution.

```text
MIT License

Copyright (c) 2026 Lukas Geiger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. Direct Runtime Dependencies

`session-checkpoint` is architected with a strict **Zero-Mandatory-Runtime-Dependencies** invariant:
The entire store engine, SQLite driver interface, JSON canonicalization, SHA-256 cryptographic verification, CLI runner, and export/import handlers rely solely on the **Python Standard Library**.

| Component | License (SPDX) | Type | Origin / Copyright | Notes |
|:---|:---|:---|:---|:---|
| **Python Standard Library** (`sqlite3`, `hashlib`, `json`, `pathlib`, `argparse`, `dataclasses`, `os`, `sys`, `stat`) | `PSF-2.0` | Core Runtime | Python Software Foundation | Bundled with Python 3.10+ runtimes; 100% offline, zero network egress |

**Zero Runtime Overhead:** No external C-extensions, no third-party package dependencies, zero network sockets opened.

---

## 3. Development & Testing Tooling

The following tools are used strictly in development, linting, packaging, and testing (`.[dev]`):

| Tool | License (SPDX) | Role in Project | Link |
|:---|:---|:---|:---|
| **`pytest`** | `MIT` | Automated test runner & regression suite | [pytest.org](https://pytest.org) |
| **`ruff`** | `MIT` / `Apache-2.0` | High-performance Python linter & code style enforcer | [astral.sh/ruff](https://astral.sh/ruff) |
| **`build`** | `MIT` | PEP 517 build frontend | [pypa/build](https://github.com/pypa/build) |
| **`twine`** | `Apache-2.0` | Secure package distribution utility | [twine.readthedocs.io](https://twine.readthedocs.io) |
| **`tomli`** | `MIT` | TOML parser for Python < 3.11 compatibility | [github.com/hukkin/tomli](https://github.com/hukkin/tomli) |

None of these packages are shipped, required, or imported during standard runtime operation.

---

## 4. Governance & Runtime Invariants Cross-Reference

| Invariant ID | Definition | Implementation Mechanism |
|:---|:---|:---|
| `INV-LOCAL-01` | **100% Local-First Storage (Zero Egress)** | Dedicated local SQLite file; zero network socket creation, 100% air-gapped safe. |
| `INV-CANON-02` | **Deterministic Canonical JSON Hashing** | Keys sorted alphabetically, compact separators (`","`, `":"`), UTF-8 encoded bytes. |
| `INV-FAILCLOSE-03` | **Fail-Closed Cryptographic Verification** | SHA-256 verified on every `get()` and `list()`; raises `CheckpointIntegrityError` upon corruption. |
| `INV-BOUNDARY-04` | **Application Boundary Isolation** | Carrier never inspects application schemas, never restores application internal state. |
| `INV-NAMESP-05` | **Strict Namespace Segregation** | Mandatory `namespace` parameter on all operations; prevents cross-application access. |
| `INV-LIMITS-06` | **Enforced Resource Caps** | 1 MiB default canonical payload cap (8 MiB pre-parse CLI cap); 1,000 checkpoints / 16 MiB import cap. |
| `INV-DRYRUN-07` | **Conservative Mutation (Dry-Run by Default)** | `delete` and `import` operations default to dry-run planning; require explicit `--apply` / `apply=True`. |
| `INV-PERM-08` | **POSIX Least-Privilege & Windows ACL** | Enforces `0600` owner-only mode bits on POSIX; documents explicit directory ACL boundaries on Windows. |
| `INV-REVERSIBLE-09` | **Reversible Migration Bundles** | Export/import preserve numeric IDs, timestamps, and payload hashes for byte-for-byte migration audits. |
| `INV-SLA-10` | **RunAsInvoker & 48h Security SLA** | Executes in unprivileged user space; 48-hour security response acknowledgment target. |

---

## 5. Security & Elevation Certification

- **Non-Elevation:** `session-checkpoint` runs strictly under `RunAsInvoker` user privileges. It never requests administrative elevation (UAC), root permissions, or kernel-level drivers.
- **Copyleft Isolation:** 100% permissive MIT and PSF-2.0 licenses. No viral copyleft (GPL / AGPL) components are incorporated or required at runtime.
