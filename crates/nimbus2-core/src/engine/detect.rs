// ffp: FFP-NIMBUS2-DETECT edge-agent rust
//! SOFTEM Hardware-Aware Tier Classification Engine.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceProfile {
    pub os: String,
    pub cpu_cores: usize,
    pub cpu_arch: String,
    pub total_ram_mb: u64,
    pub otg_capable: bool,
    pub hsm_available: bool,
    pub tier: u32,
    pub activated_features: Vec<String>,
}

pub fn detect_device() -> DeviceProfile {
    let cpu_cores = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1);
    let cpu_arch = std::env::consts::ARCH.to_string();
    let os = std::env::consts::OS.to_string();
    let total_ram_mb = read_mem_total_mb().unwrap_or(4096);
    let otg_capable = Path::new("/sys/bus/usb/devices").exists() || os == "linux" || os == "android";
    let hsm_available = Path::new("/sys/class/keymaster").exists()
        || Path::new("/dev/keymaster").exists()
        || Path::new("/dev/tpmrm0").exists();

    let mut profile = DeviceProfile {
        os,
        cpu_cores,
        cpu_arch,
        total_ram_mb,
        otg_capable,
        hsm_available,
        tier: 1,
        activated_features: Vec::new(),
    };
    let tier = classify_tier(&profile);
    profile.tier = tier;
    profile.activated_features = get_features(tier).into_iter().map(String::from).collect();
    profile
}

fn read_mem_total_mb() -> Option<u64> {
    let content = fs::read_to_string("/proc/meminfo").ok()?;
    for line in content.lines() {
        if let Some(rest) = line.strip_prefix("MemTotal:") {
            let kb_str = rest.trim().split_whitespace().next()?;
            let kb: u64 = kb_str.parse().ok()?;
            return Some(kb / 1024);
        }
    }
    None
}

pub fn classify_tier(profile: &DeviceProfile) -> u32 {
    if profile.total_ram_mb >= 12288 && profile.hsm_available {
        4
    } else if profile.total_ram_mb >= 8192 && profile.otg_capable {
        3
    } else if profile.total_ram_mb >= 4096 {
        2
    } else {
        1
    }
}

pub fn get_features(tier: u32) -> Vec<&'static str> {
    match tier {
        1 => vec![
            "Multiboot catalog (5 ISOs)",
            "Concurrent proxy pool (50 streams)",
            "Route health probe (100 req/day)",
        ],
        2 => vec![
            "Standard multiboot (25 ISOs)",
            "Standard proxy pool (225 streams)",
            "SERP & ASN validation (1,000 req/day)",
            "Peer mesh discovery",
        ],
        3 => vec![
            "Unlimited multiboot + BLAKE3 verification",
            "High-concurrency proxy pool (675 streams)",
            "Multi-country ASN validation (10,000 req/day)",
            "Self-healing circuit-breaker mesh",
        ],
        _ => vec![
            "Elite multiboot + persistent encrypted volumes",
            "Unbounded adaptive stream pool",
            "Hardware-backed HSM envelope sealing",
            "Full Etamanga authenticated transport",
        ],
    }
}
