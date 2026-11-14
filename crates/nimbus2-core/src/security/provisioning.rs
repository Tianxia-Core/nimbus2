// ffp: FFP-NIMBUS2-PROVISIONING edge-agent rust
//! Single-Currency (EUR) Tiered Capacity Policy for Nimbus².

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Tier {
    Starter,
    Growth,
    Business,
    Enterprise,
}

impl Tier {
    pub fn currency(&self) -> &'static str {
        "EUR"
    }

    pub fn price_eur(&self) -> u32 {
        match self {
            Tier::Starter => 49,
            Tier::Growth => 299,
            Tier::Business => 999,
            Tier::Enterprise => 9999,
        }
    }

    pub fn streams(&self) -> u32 {
        match self {
            Tier::Starter => 225,
            Tier::Growth => 675,
            Tier::Business => 2048,
            Tier::Enterprise => 9999,
        }
    }

    pub fn countries(&self) -> u32 {
        match self {
            Tier::Starter => 10,
            Tier::Growth => 42,
            Tier::Business => 120,
            Tier::Enterprise => 195,
        }
    }

    pub fn serp_requests_per_day(&self) -> u32 {
        match self {
            Tier::Starter => 1_000,
            Tier::Growth => 10_000,
            Tier::Business => 100_000,
            Tier::Enterprise => 1_000_000,
        }
    }
}
