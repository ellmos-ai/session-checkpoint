# Security policy

Checkpoint payloads are application-defined and may contain sensitive local context. Keep the
store and exports outside shared or published directories unless the application has explicitly
redacted them. The package performs no network access.

SHA-256 verifies local payload integrity; it is not authentication or encryption. Applications
that accept checkpoint bundles from another trust domain need their own authenticated transport
or signature layer before import.

Do not report a vulnerability by placing payload samples, paths, secrets, or store files in a
public issue. Use a private maintainer channel and provide the smallest synthetic reproduction.
