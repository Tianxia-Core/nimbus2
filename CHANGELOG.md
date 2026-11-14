# Changelog

All notable changes to **Nimbus²** are documented in this file.

## [2.4.0] - 2026-11-12

### Added
- Unified `nimbus2-core`, `nimbus2-product`, `global-proxy-engine`, and `nimbus2-das` into `Tianxia-Core/nimbus2`.
- Added self-contained `CGO_ENABLED=0` Go CLI (`go/cmd/nimbus2`) supporting `proxy`, `health`, `bench`, `validate`, `detect`, `multiboot`, and `tui` across Linux (`x86_64`, `aarch64`), Windows (`x86_64.exe`), and Android (`aarch64`).
- Implemented BLAKE3-XOF + constant-time MAC Etamanga authenticated encryption (`crates/nimbus2-core/src/security/etamanga.rs`).
- Implemented real runtime `/proc` SOFTEM hardware tier classifier and ISO MBR/ISO9660 + BLAKE3/SHA-256 multiboot verifier.
- Added Ed25519 release signatures, `SHA256SUMS`, CycloneDX 1.5 `SBOM.cdx.json`, and GitHub Actions CI matrix.

### Removed
- Eliminated all placeholder stubs from `crates/nimbus2-core`.
- Purged legacy build caches, `__pycache__`, and stale session artifacts from merged repositories.
