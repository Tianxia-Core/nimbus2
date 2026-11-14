# Contributing to Nimbus²

Thank you for contributing to **Nimbus²**!

## Engineering Standards

1. **Zero Stubs**: Every function, CLI command, and protocol handler must implement complete behavior backed by automated tests.
2. **Polyglot Fitness (`FFP-First`)**: Every source file must declare its `# ffp:` or `// ffp:` header at the top of the file.
3. **Bounded Concurrency & Clean Shutdown**: All network loops must honor context cancellation, explicit socket timeouts, and semaphore caps.
4. **Zero Committed Secrets or Build Caches**: Never commit `target/`, `__pycache__/`, `.pyc`, `.keystore`, or API credentials.
5. **Single-Currency Documentation (`EUR`)**: Commercial tier examples must consistently use `EUR` (`€`).

## Verification Before Submitting a Pull Request

```bash
cd go && go test -race -v ./...
cd ../crates/nimbus2-core && cargo test
```
