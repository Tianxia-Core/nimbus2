<p align="center">
  <img src="./brand-kit/01-logos/lockups-and-social/dual-lockup-rxm-x-tianxiaos.svg" alt="RASA-X-MACHINA · tianxiaOS" width="680"/>
</p>

# nimbus²

[![CI](https://github.com/Tianxia-Core/nimbus2/actions/workflows/ci.yml/badge.svg)](https://github.com/Tianxia-Core/nimbus2/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-v2.4.0-00d4aa)](https://github.com/Tianxia-Core/nimbus2/releases/tag/v2.4.0)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL--2.0-0ea5e9?style=flat-square)](LICENSE)

**Nimbus²** is the unified polyglot network proxy, route benchmarking, ASN validation, and cryptographic multiboot verification suite maintained by **RASA-X-MACHINA** *(Proposed Estonian Deep-Tech Entity — Tallinn, Estonia)*.

<!-- BUILD_LAW_SHOWCASE_START -->

---

## 🌍 In Plain English — What `nimbus2` Is & Why It Matters (Layman's Guide)

- **The Everyday Problem:** Distributed servers and edge devices drop connections when routes degrade, ISP paths shift, or background daemons hang silently.
- **How It Works (Without the Jargon):** `nimbus²` supervises multi-node mesh links, validates network ASN routes, benchmarks latency paths in real time, and shifts traffic cleanly before users notice a stall.
- **Why It Is Different:** Ships as Ed25519-signed multi-OS binaries (`.deb`, `.rpm`, `.AppImage`, `flake.nix`, `.exe`) built under **[Build Law](https://github.com/Tianxia-Core/Build-Law)** (`Apache-2.0`).
- **How It Benefits You:** Platform and SRE teams get resilient cross-region connectivity and instant route diagnostics in a single lightweight binary.
- **How to Install & Use It in 60 Seconds:** Install directly from **[nimbus2 Releases](https://github.com/Tianxia-Core/nimbus2/releases/latest)** or via `nix run github:Tianxia-Core/nimbus2`.

---

## 🏛️ Governed by [`Build Law`](https://github.com/Tianxia-Core/Build-Law) — Engineering Philosophy & Stakeholder Pathways

This repository is a live production showcase of **[`Build Law`](https://github.com/Tianxia-Core/Build-Law)**—the open-source (`MIT`) **4-Pillar, 14-Gate Constitutional Engineering & `5.0×–8.8×` Token-Efficiency Standard** created by **[Collins Takem](https://rasaxmachina.com/collins)** (**RASA-X-MACHINA**):
- **Developers & AI Builders:** Drop **[`Build Law`](https://github.com/Tianxia-Core/Build-Law)** into Claude Code, Cursor, OpenCode, VS Code (`.vsix`), GitHub Copilot, Windsurf, Cline, Aider, or any chat LLM in 60 seconds.
- **CTOs & B2B Engineering Leaders:** Need similar `Rust`/`Go`/`Nix`/Security/FinOps rigor applied to your infrastructure? Scope a fixed-price **72-Hour `VRTTI` Architecture Sprint** at **[vrtti.rasaxmachina.com](https://vrtti.rasaxmachina.com)**.
- **Investors, Researchers, Press & Executive Hiring Committees:** Inspect our cryptographic release proofs across **[`@Tianxia-Core`](https://github.com/Tianxia-Core)**, press assets at **[rasaxmachina.com/press](https://rasaxmachina.com/press)**, and founder dossier at **[rasaxmachina.com/collins](https://rasaxmachina.com/collins)**.

<!-- BUILD_LAW_SHOWCASE_END -->

---
## Consolidated Architecture & Attribution

`Tianxia-Core/nimbus2` consolidates five previously split repositories into one cohesive, zero-stub polyglot monorepo:

| Directory | Consolidated Origin | Responsibility |
| :--- | :--- | :--- |
| [`crates/nimbus2-core/`](crates/nimbus2-core/) | `nimbus2-core` & `nimbus2-das/core` | Rust concurrent proxy engine, SOFTEM hardware classifier, BLAKE3-XOF Etamanga authenticated envelope encryption, HSM envelope signer, and ISO integrity verifier |
| [`go/cmd/nimbus2/`](go/cmd/nimbus2/) | Unified Static CLI (`v2.4.0`) | Zero-dependency (`CGO_ENABLED=0`) static executable providing HTTP/HTTPS `CONNECT` proxy pooling, TLS 1.3 health probing, percentile route benchmarking, config validation, and interactive ANSI TUI |
| [`python/global_proxy/`](python/global_proxy/) | `Tianxia-Core/global-proxy-engine` | Asynchronous multi-country residential/ISP ASN validation, TLS ClientHello fingerprinting, and SOCKS5/HTTP rotation |
| [`platform/`](platform/) | `nimbus2-product` & `nimbus2-das` | Multi-platform orchestration scripts, polymorphic route management, monitoring, and build harnesses |
| [`config/brand/`](config/brand/) & [`docs/`](docs/) | `nimbus2-das` & `nimbus2-landing-portal` | Design tokens, NJVM synthesis architecture notes, and release verification guides |

---

## Prebuilt Signed Executables (`v2.4.0`)

Every GitHub Release ships self-contained binaries signed with the RASA-X-MACHINA **Ed25519** release key (`RELEASE_SIGNING_KEY.pub.pem`), accompanied by `SHA256SUMS`, `SHA256SUMS.sig`, and a CycloneDX 1.5 `SBOM.cdx.json`:

- `nimbus2-v2.4.0-linux-x86_64` — Static Linux `x86_64` ELF (`CGO_ENABLED=0`)
- `nimbus2-v2.4.0-linux-aarch64` — Static Linux `aarch64` ELF (`CGO_ENABLED=0`)
- `nimbus2-v2.4.0-windows-x86_64.exe` — Static Windows `x86_64` PE32+ executable
- `nimbus2-v2.4.0-android-aarch64` — Native Android `arm64-v8a` PIE executable

### Cryptographic Signature Verification (OpenSSL 3.x)

```bash
sha256sum -c SHA256SUMS
openssl pkeyutl -verify -pubin -inkey RELEASE_SIGNING_KEY.pub.pem \
  -rawin -in SHA256SUMS -sigfile SHA256SUMS.sig
```

---

## Quick Start

```bash
# 1. Inspect runtime SOFTEM hardware tier & recommended stream capacity
./nimbus2-v2.4.0-linux-x86_64 detect --json

# 2. Launch bounded HTTP/HTTPS CONNECT proxy pool (graceful SIGINT/SIGTERM shutdown)
./nimbus2-v2.4.0-linux-x86_64 proxy --listen 127.0.0.1:8080 --streams 225 --timeout 15

# 3. Probe upstream TLS 1.3 health & latency
./nimbus2-v2.4.0-linux-x86_64 health --targets https://rasaxmachina.com --json

# 4. Run concurrent route latency benchmark (min / mean / p50 / p95 / p99 / RPS)
./nimbus2-v2.4.0-linux-x86_64 bench --target http://127.0.0.1:8080/__nimbus2/health --concurrency 16 --requests 200

# 5. Validate JSON daemon configuration
./nimbus2-v2.4.0-linux-x86_64 validate --config config.example.json

# 6. Render interactive terminal cockpit (or single snapshot via --once)
./nimbus2-v2.4.0-linux-x86_64 tui --once
```

---

## Building From Source

```bash
# Go static CLI & test suite
cd go && go test -v ./... && CGO_ENABLED=0 go build -ldflags="-s -w" -o ../bin/nimbus2 ./cmd/nimbus2

# Rust core engine & test suite
cd crates/nimbus2-core && cargo test && cargo build --release
```

## Governance & Legal Notice

- **Security Policy**: See [SECURITY.md](SECURITY.md) for responsible disclosure ([Encrypted Security Dispatch](https://rasaxmachina.com/collins#encrypted-dispatch)).
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Entity Candor**: Maintained by **RASA-X-MACHINA** *(Proposed Estonian OÜ — Startup Committee & e-Residency incorporation in progress, Tallinn, Estonia)*.
