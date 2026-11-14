// ffp: FFP-NIMBUS2-TUI concurrent-daemon rust
//! `nimbus2-tui` — Terminal Cockpit & Live Telemetry Renderer for Nimbus² v2.4.0.

use nimbus2_core::engine::{multiboot, status};
use nimbus2_core::security::hsm::TitanHsm;
use std::env;
use std::thread;
use std::time::Duration;

fn render_frame(iteration: u64) -> String {
    let snap = status::snapshot();
    let mut hsm = TitanHsm::new();
    hsm.initialize();
    let key = hsm.generate_key("tui-health-probe");
    let hsm_ok = hsm
        .sign(b"nimbus2-tui-heartbeat", &key)
        .and_then(|sig| hsm.verify(b"nimbus2-tui-heartbeat", &sig, &key))
        .unwrap_or(false);
    let catalog_count = multiboot::catalog().len();

    let mut out = String::with_capacity(1024);
    out.push_str("┌──────────────────────────────────────────────────────────────────────────┐\n");
    out.push_str(&format!(
        "│  NIMBUS² TERMINAL COCKPIT v{:<8} · FRAME #{:<6} · {:<18} │\n",
        snap.version,
        iteration,
        if hsm_ok { "HSM VERIFIED" } else { "HSM DEGRADED" }
    ));
    out.push_str("├──────────────────────────────────────────────────────────────────────────┤\n");
    out.push_str(&format!(
        "│  Host Arch / OS : {:<14} / {:<14}   Tier : T{:<12} │\n",
        snap.device.cpu_arch, snap.device.os, snap.device.tier
    ));
    out.push_str(&format!(
        "│  Compute / RAM  : {:<4} cores     / {:<8} MB      ISOs : {:<13} │\n",
        snap.device.cpu_cores, snap.device.total_ram_mb, catalog_count
    ));
    out.push_str("├──────────────────────────────────────────────────────────────────────────┤\n");
    for sub in &snap.subsystems {
        out.push_str(&format!("│  [ONLINE] {:<62} │\n", sub));
    }
    out.push_str("└──────────────────────────────────────────────────────────────────────────┘\n");
    out
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("Usage: nimbus2-tui [--once] [--json] [--frames N]");
        return;
    }
    if args.iter().any(|a| a == "--json") {
        let snap = status::snapshot();
        println!(
            "{}",
            serde_json::to_string_pretty(&snap).unwrap_or_else(|_| "{}".to_string())
        );
        return;
    }

    let mut max_frames: u64 = 1;
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--frames" && i + 1 < args.len() {
            max_frames = args[i + 1].parse().unwrap_or(1).max(1);
            i += 2;
        } else {
            i += 1;
        }
    }

    for frame in 1..=max_frames {
        if frame > 1 {
            print!("\x1b[2J\x1b[H");
        }
        print!("{}", render_frame(frame));
        if frame < max_frames {
            thread::sleep(Duration::from_millis(250));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tui_frame_renders_verified_state() {
        let rendered = render_frame(1);
        assert!(rendered.contains("NIMBUS² TERMINAL COCKPIT"));
        assert!(rendered.contains("HSM VERIFIED"));
        assert!(rendered.contains("[ONLINE]"));
    }
}
