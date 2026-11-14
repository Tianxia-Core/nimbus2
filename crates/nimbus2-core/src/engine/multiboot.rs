// ffp: FFP-NIMBUS2-MULTIBOOT edge-agent rust
//! Multiboot USB & ISO Integrity Manifest Engine.

use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::io::{self, Read};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DistroCatalogEntry {
    pub id: &'static str,
    pub label: &'static str,
    pub category: &'static str,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IsoVerification {
    pub path: String,
    pub size_bytes: u64,
    pub blake3_hex: String,
    pub bootable_signature_present: bool,
}

pub fn catalog() -> Vec<DistroCatalogEntry> {
    vec![
        DistroCatalogEntry { id: "nixos-24.11", label: "NixOS 24.11 Sovereign Minimal", category: "Immutable OS" },
        DistroCatalogEntry { id: "ubuntu-24.04", label: "Ubuntu 24.04 LTS", category: "Desktop" },
        DistroCatalogEntry { id: "fedora-41", label: "Fedora 41 Workstation", category: "Desktop" },
        DistroCatalogEntry { id: "kali-2026", label: "Kali Linux 2026", category: "Security" },
        DistroCatalogEntry { id: "tails-6.x", label: "Tails 6 Amnesic", category: "Privacy" },
        DistroCatalogEntry { id: "systemrescue-11", label: "SystemRescue 11", category: "Recovery" },
        DistroCatalogEntry { id: "alpine-3.20", label: "Alpine Linux 3.20", category: "Embedded" },
    ]
}

pub fn verify_iso_image(path: &Path) -> io::Result<IsoVerification> {
    let mut f = File::open(path)?;
    let meta = f.metadata()?;
    let mut hasher = blake3::Hasher::new();
    let mut buf = [0u8; 65536];
    let mut header = Vec::new();
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        if header.len() < 40960 {
            let need = (40960 - header.len()).min(n);
            header.extend_from_slice(&buf[..need]);
        }
        hasher.update(&buf[..n]);
    }
    // Check MBR 0x55AA signature at offset 510 or ISO9660 "CD001" at 0x8001
    let mbr_sig = header.len() >= 512 && header[510] == 0x55 && header[511] == 0xAA;
    let cd001_sig = header.len() >= 0x8006 && &header[0x8001..0x8006] == b"CD001";
    Ok(IsoVerification {
        path: path.display().to_string(),
        size_bytes: meta.len(),
        blake3_hex: hasher.finalize().to_hex().to_string(),
        bootable_signature_present: mbr_sig || cd001_sig,
    })
}

pub fn detect_removable_block_devices() -> Vec<String> {
    let mut out = Vec::new();
    if let Ok(entries) = fs::read_dir("/sys/block") {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();
            let rem_path = entry.path().join("removable");
            if let Ok(val) = fs::read_to_string(rem_path) {
                if val.trim() == "1" {
                    out.push(format!("/dev/{}", name));
                }
            }
        }
    }
    out.sort();
    out
}
