# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :--- |
| `2.4.x` | Yes |
| `< 2.4.0` | Superseded (upgrade to unified `Tianxia-Core/nimbus2` `v2.4.0+`) |

## Reporting a Vulnerability

Please **do not** open public GitHub issues for suspected security vulnerabilities.

Report vulnerabilities privately to **[Encrypted Security Dispatch](https://rasaxmachina.com/collins#encrypted-dispatch)** with:
1. Affected component (`crates/nimbus2-core`, `go/cmd/nimbus2`, `python/global_proxy`, or `platform/`).
2. Minimal reproduction steps or proof-of-concept input.
3. Expected impact and suggested mitigation.

We acknowledge valid reports within **48 hours** and publish signed patches with updated `SHA256SUMS.sig` and CycloneDX `SBOM.cdx.json`.

## Release Artifact Integrity

All official release binaries are signed using **Ed25519 (RFC 8032)** via OpenSSL 3.x `-rawin`:

```bash
openssl pkeyutl -verify -pubin -inkey RELEASE_SIGNING_KEY.pub.pem \
  -rawin -in <artifact> -sigfile <artifact>.sig
```
