// ffp: FFP-NIMBUS2-STATUS edge-agent rust
//! Runtime Status Snapshot for Nimbus² v2.4.0.

use crate::engine::detect;
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct RuntimeStatus {
    pub product: &'static str,
    pub version: &'static str,
    pub publisher: &'static str,
    pub device: detect::DeviceProfile,
    pub subsystems: Vec<&'static str>,
}

pub fn snapshot() -> RuntimeStatus {
    RuntimeStatus {
        product: "Nimbus² Polyglot Proxy & Multiboot Suite",
        version: "2.4.0",
        publisher: "Rasa-X-Machina (Proposed Estonian Deep-Tech Entity)",
        device: detect::detect_device(),
        subsystems: vec![
            "crates/nimbus2-core (Rust Engine & AEAD Envelope)",
            "go/cmd/nimbus2 (Static Concurrent Proxy, Health, Bench & TUI)",
            "python/global_proxy (Multi-Country ASN & Residential Tunnel Suite)",
            "platform/ (SOFTEM, Multiboot & Monitoring Orchestration)",
        ],
    }
}
