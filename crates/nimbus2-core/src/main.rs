// ffp: FFP-NIMBUS2-MAIN concurrent-daemon rust
//! `nimbus2-engine` CLI binary for the Nimbus² Rust Core Crate.

use nimbus2_core::engine::{detect, multiboot, proxy, status};
use std::env;
use std::path::Path;
use std::process;

fn print_usage() {
    eprintln!(
        "Nimbus² Core Engine v2.4.0 (Rust)\n\
         Usage:\n\
         \x20 nimbus2-engine status [--json]\n\
         \x20 nimbus2-engine detect [--json]\n\
         \x20 nimbus2-engine proxy [--listen 127.0.0.1:8080] [--streams 225]\n\
         \x20 nimbus2-engine multiboot <catalog|usb|verify> [iso_path]"
    );
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() || args[0] == "--help" || args[0] == "-h" {
        print_usage();
        return;
    }
    let json_flag = args.iter().any(|a| a == "--json");

    match args[0].as_str() {
        "status" => {
            let snap = status::snapshot();
            if json_flag {
                println!("{}", serde_json::to_string_pretty(&snap).unwrap_or_default());
            } else {
                println!("{} v{}", snap.product, snap.version);
                println!("Publisher: {}", snap.publisher);
                println!("Device Tier: {} ({} cores, {} MB RAM)", snap.device.tier, snap.device.cpu_cores, snap.device.total_ram_mb);
                for sub in snap.subsystems {
                    println!("  [OK] {}", sub);
                }
            }
        }
        "detect" => {
            let dev = detect::detect_device();
            if json_flag {
                println!("{}", serde_json::to_string_pretty(&dev).unwrap_or_default());
            } else {
                println!("SOFTEM Hardware Profile:");
                println!("  OS/Arch: {} / {}", dev.os, dev.cpu_arch);
                println!("  CPU Cores: {}", dev.cpu_cores);
                println!("  RAM: {} MB", dev.total_ram_mb);
                println!("  Tier: {}", dev.tier);
                for feat in dev.activated_features {
                    println!("  + {}", feat);
                }
            }
        }
        "proxy" => {
            let mut listen = "127.0.0.1:8080".to_string();
            let mut streams = 225usize;
            let mut i = 1;
            while i < args.len() {
                match args[i].as_str() {
                    "--listen" if i + 1 < args.len() => {
                        listen = args[i + 1].clone();
                        i += 2;
                    }
                    "--streams" if i + 1 < args.len() => {
                        streams = args[i + 1].parse().unwrap_or(225);
                        i += 2;
                    }
                    _ => i += 1,
                }
            }
            match proxy::ProxyServer::bind(&listen, streams) {
                Ok(srv) => {
                    println!("[nimbus2-engine] Listening on {} (max_streams={})", listen, streams);
                    if let Err(e) = srv.serve_until_shutdown() {
                        eprintln!("[nimbus2-engine] proxy error: {}", e);
                        process::exit(1);
                    }
                }
                Err(e) => {
                    eprintln!("[nimbus2-engine] failed to bind {}: {}", listen, e);
                    process::exit(1);
                }
            }
        }
        "multiboot" => {
            let sub = args.get(1).map(String::as_str).unwrap_or("catalog");
            match sub {
                "catalog" => {
                    for entry in multiboot::catalog() {
                        println!("{:<18} {:<32} [{}]", entry.id, entry.label, entry.category);
                    }
                }
                "usb" => {
                    let devs = multiboot::detect_removable_block_devices();
                    if devs.is_empty() {
                        println!("No removable USB block devices currently attached.");
                    } else {
                        for d in devs {
                            println!("{}", d);
                        }
                    }
                }
                "verify" => {
                    if let Some(p) = args.get(2) {
                        match multiboot::verify_iso_image(Path::new(p)) {
                            Ok(v) => println!("{}", serde_json::to_string_pretty(&v).unwrap_or_default()),
                            Err(e) => {
                                eprintln!("ISO verification failed: {}", e);
                                process::exit(1);
                            }
                        }
                    } else {
                        eprintln!("Usage: nimbus2-engine multiboot verify <iso_path>");
                        process::exit(2);
                    }
                }
                _ => {
                    print_usage();
                    process::exit(2);
                }
            }
        }
        _ => {
            print_usage();
            process::exit(2);
        }
    }
}
