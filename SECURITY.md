# Security policy

Checkpoint payloads are application-defined and may contain sensitive local context. Keep the
store and exports outside shared or published directories unless the application has explicitly
redacted them. On POSIX, the carrier creates these files with owner-only mode bits and restricts
compatible existing stores when opened. On Windows, use a directory ACL that grants access only
to the intended account; Python mode bits are not Windows ACLs. The package performs no network
access.

Imports are bounded by record count and aggregate canonical payload. The JSON CLI also bounds the
import file before parsing. Create-payload files are capped at 8 MiB before parsing and the
canonical payload is capped at 1 MiB by default. Applications may configure stricter core limits
for their local risk and data shape.

SHA-256 verifies local payload integrity; it is not authentication or encryption. Applications
that accept checkpoint bundles from another trust domain need their own authenticated transport
or signature layer before import.

## Vulnerability Reporting & Response SLA

Do not report a vulnerability by placing payload samples, paths, secrets, or store files in a
public issue. Use a private maintainer channel and provide the smallest synthetic reproduction.

- **Initial Response SLA:** Within **48 hours** of report receipt.
- **Triage & Assessment Target:** Within **5 business days**.
- **Execution Privileges:** Strictly unprivileged user-mode (`RunAsInvoker`). Zero administrative or root elevation.
