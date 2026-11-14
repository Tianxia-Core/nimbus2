// ffp: FFP-NIMBUS2-ETAMANGA crypto-signer rust
//! Etamanga Authenticated Envelope Encryption (BLAKE3-XOF + Constant-Time Keyed MAC).

use constant_time_eq::constant_time_eq;
use std::fs::File;
use std::io::{self, Read};
use std::time::{SystemTime, UNIX_EPOCH};

const NONCE_LEN: usize = 24;
const TAG_LEN: usize = 32;

fn fill_entropy(buf: &mut [u8]) -> io::Result<()> {
    if let Ok(mut f) = File::open("/dev/urandom") {
        if f.read_exact(buf).is_ok() {
            return Ok(());
        }
    }
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(1);
    let mut h = blake3::Hasher::new();
    h.update(&nanos.to_le_bytes());
    h.update(&std::process::id().to_le_bytes());
    h.finalize_xof().fill(buf);
    Ok(())
}

pub fn seal(plaintext: &[u8], master_key: &[u8]) -> io::Result<Vec<u8>> {
    let mut nonce = [0u8; NONCE_LEN];
    fill_entropy(&mut nonce)?;

    let enc_key = blake3::derive_key("nimbus2-etamanga-v2.4-stream-enc", master_key);
    let mac_key = blake3::derive_key("nimbus2-etamanga-v2.4-stream-mac", master_key);

    let mut stream_hasher = blake3::Hasher::new_keyed(&enc_key);
    stream_hasher.update(&nonce);
    let mut keystream = vec![0u8; plaintext.len()];
    stream_hasher.finalize_xof().fill(&mut keystream);

    let ciphertext: Vec<u8> = plaintext
        .iter()
        .zip(keystream.iter())
        .map(|(p, k)| p ^ k)
        .collect();

    let mut mac = blake3::Hasher::new_keyed(&mac_key);
    mac.update(&nonce);
    mac.update(&ciphertext);
    let tag = mac.finalize();

    let mut out = Vec::with_capacity(NONCE_LEN + ciphertext.len() + TAG_LEN);
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ciphertext);
    out.extend_from_slice(tag.as_bytes());
    Ok(out)
}

pub fn open(sealed: &[u8], master_key: &[u8]) -> io::Result<Vec<u8>> {
    if sealed.len() < NONCE_LEN + TAG_LEN {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "sealed frame truncated"));
    }
    let nonce = &sealed[..NONCE_LEN];
    let tag = &sealed[sealed.len() - TAG_LEN..];
    let ciphertext = &sealed[NONCE_LEN..sealed.len() - TAG_LEN];

    let enc_key = blake3::derive_key("nimbus2-etamanga-v2.4-stream-enc", master_key);
    let mac_key = blake3::derive_key("nimbus2-etamanga-v2.4-stream-mac", master_key);

    let mut mac = blake3::Hasher::new_keyed(&mac_key);
    mac.update(nonce);
    mac.update(ciphertext);
    let expected = mac.finalize();

    if !constant_time_eq(expected.as_bytes(), tag) {
        return Err(io::Error::new(io::ErrorKind::PermissionDenied, "authentication tag mismatch"));
    }

    let mut stream_hasher = blake3::Hasher::new_keyed(&enc_key);
    stream_hasher.update(nonce);
    let mut keystream = vec![0u8; ciphertext.len()];
    stream_hasher.finalize_xof().fill(&mut keystream);

    Ok(ciphertext
        .iter()
        .zip(keystream.iter())
        .map(|(c, k)| c ^ k)
        .collect())
}
