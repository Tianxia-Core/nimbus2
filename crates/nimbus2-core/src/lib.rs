// ffp: FFP-NIMBUS2-CORE concurrent-daemon rust
//! Nimbus² v2.4.0 Core Library — Unified Rust Engine.
//! Consolidates `nimbus2-core` and `nimbus2-das/core` with zero stubs.

pub mod engine;
pub mod intelligence;
pub mod security;

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::{TcpListener, TcpStream};
    use std::sync::atomic::Ordering;
    use std::thread;

    #[test]
    fn test_softem_detect_real_hardware() {
        let profile = engine::detect::detect_device();
        assert!(profile.cpu_cores >= 1);
        assert!(!profile.cpu_arch.is_empty());
        let tier = engine::detect::classify_tier(&profile);
        assert!((1..=4).contains(&tier));
    }

    #[test]
    fn test_etamanga_seal_and_open_roundtrip() {
        let key = b"nimbus2-sovereign-master-key-32b";
        let plaintext = b"Sovereign proxy route frame payload v2.4.0";
        let sealed = security::etamanga::seal(plaintext, key).expect("seal");
        assert_ne!(&sealed[..], plaintext);
        let opened = security::etamanga::open(&sealed, key).expect("open");
        assert_eq!(opened, plaintext);

        let mut tampered = sealed.clone();
        let last = tampered.len() - 1;
        tampered[last] ^= 0x55;
        assert!(security::etamanga::open(&tampered, key).is_err());
    }

    #[test]
    fn test_hsm_sign_and_verify() {
        let mut hsm = security::hsm::TitanHsm::new();
        hsm.initialize();
        let key = hsm.generate_key("ed25519-envelope");
        assert_eq!(key.len(), 32);
        let msg = b"route-attestation-epoch-42";
        let sig = hsm.sign(msg, &key).expect("sign");
        assert!(hsm.verify(msg, &sig, &key).expect("verify ok"));
        assert!(!hsm.verify(b"forged", &sig, &key).expect("verify fail"));
    }

    #[test]
    fn test_proxy_http_forward_roundtrip() {
        let upstream = TcpListener::bind("127.0.0.1:0").expect("bind upstream");
        let up_addr = upstream.local_addr().expect("up addr");
        let up_handle = thread::spawn(move || {
            if let Ok((mut conn, _)) = upstream.accept() {
                let mut buf = [0u8; 512];
                let _ = conn.read(&mut buf);
                let body = b"NIMBUS2_UPSTREAM_OK";
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                    body.len()
                );
                let _ = conn.write_all(resp.as_bytes());
                let _ = conn.write_all(body);
            }
        });

        let server = engine::proxy::ProxyServer::bind("127.0.0.1:0", 16).expect("bind proxy");
        let proxy_addr = server.local_addr().expect("proxy addr");
        let stats = server.stats();
        let srv_handle = thread::spawn(move || {
            server.serve_max_connections(1).expect("serve 1");
        });

        let mut client = TcpStream::connect(proxy_addr).expect("connect proxy");
        let req = format!(
            "GET http://{}/health HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n",
            up_addr, up_addr
        );
        client.write_all(req.as_bytes()).expect("write req");
        let mut out = String::new();
        client.read_to_string(&mut out).expect("read resp");
        assert!(out.contains("200 OK"));
        assert!(out.contains("NIMBUS2_UPSTREAM_OK"));

        up_handle.join().expect("join up");
        srv_handle.join().expect("join srv");
        assert_eq!(stats.total_connections.load(Ordering::Relaxed), 1);
    }

    #[test]
    fn test_intelligence_miner_and_provisioning_eur() {
        let sample = b"GET https://rasaxmachina.com/api?node=198.51.100.42:8443 HTTP/1.1";
        let patterns = intelligence::miner::mine_patterns(sample);
        assert!(patterns.iter().any(|p| p.contains("endpoint:198.51.100.42:8443")));
        let tier = security::provisioning::Tier::Growth;
        assert_eq!(tier.currency(), "EUR");
        assert_eq!(tier.price_eur(), 299);
    }
}
