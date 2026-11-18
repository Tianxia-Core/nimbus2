# Governance — Nimbus² (`Tianxia-Core/nimbus2`)

`Nimbus²` is maintained by **Collins Takem** (`@collinstaken525-cloud`) under the **RASA-X-MACHINA** sovereign systems organization (`https://rasaxmachina.com`), governed constitutively by **`Tianxia-Core/Build-Law`**.

## Architectural & Release Invariants
1. **14-Gate Completeness (`PARAMASIVA`)**: Zero `TODO`/`FIXME`/stubs; every release passes `go test ./...`, `nimbus2 cleanroom --mode audit`, and `build-law check`.
2. **Two-Edition Isolation (`PUBLIC_CLEANROOM_SEED`)**: Public commits and multi-OS release artifacts never bundle populated databases, personal spreadsheets, private keys, or internal mesh telemetry. End users bootstrap fresh environments via `nimbus2 init-clean`.
3. **Cryptographic Provenance**: All release artifacts are accompanied by Ed25519 detached signatures (`.sig`), `SHA256SUMS`, and CycloneDX 1.5 `SBOM.cdx.json`.
