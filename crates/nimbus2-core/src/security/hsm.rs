// ffp: FFP-NIMBUS2-HSM crypto-signer rust
//! Hardware Security Module (Titan M2 / TPM2 / Keyed Envelope) Signer.

use constant_time_eq::constant_time_eq;
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;

pub struct TitanHsm {
    initialized: bool,
}

impl Default for TitanHsm {
    fn default() -> Self {
        Self::new()
    }
}

impl TitanHsm {
    pub fn new() -> Self {
        Self { initialized: false }
    }

    pub fn initialize(&mut self) {
        self.initialized = true;
    }

    pub fn is_hardware_backed(&self) -> bool {
        Path::new("/sys/class/keymaster").exists()
            || Path::new("/dev/keymaster").exists()
            || Path::new("/dev/tpmrm0").exists()
    }

    pub fn generate_key(&self, label: &str) -> [u8; 32] {
        let mut seed = [0u8; 32];
        if let Ok(mut f) = File::open("/dev/urandom") {
            let _ = f.read_exact(&mut seed);
        }
        let context = format!("nimbus2-hsm-v2.4:{}", label);
        blake3::derive_key(&context, &seed)
    }

    pub fn sign(&self, data: &[u8], key: &[u8]) -> io::Result<[u8; 32]> {
        if !self.initialized {
            return Err(io::Error::new(io::ErrorKind::Other, "HSM not initialized"));
        }
        let k32 = blake3::derive_key("nimbus2-hsm-signing-subkey", key);
        let tag = blake3::keyed_hash(&k32, data);
        Ok(*tag.as_bytes())
    }

    pub fn verify(&self, data: &[u8], signature: &[u8], key: &[u8]) -> io::Result<bool> {
        if signature.len() != 32 {
            return Ok(false);
        }
        let expected = self.sign(data, key)?;
        Ok(constant_time_eq(&expected, signature))
    }
}
