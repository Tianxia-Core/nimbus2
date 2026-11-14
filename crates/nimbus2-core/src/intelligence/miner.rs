// ffp: FFP-NIMBUS2-MINER compute-kernel rust
//! Route Endpoint & Anomaly Pattern Miner.

use crate::intelligence::extractor::shannon_entropy;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct ThreatReport {
    pub entropy_bits: f64,
    pub extracted_patterns: Vec<String>,
    pub anomalies: Vec<String>,
}

pub fn mine_patterns(data: &[u8]) -> Vec<String> {
    let text = String::from_utf8_lossy(data);
    let mut out = Vec::new();
    for token in text.split(|c: char| c.is_whitespace() || matches!(c, '"' | '\'' | '?' | '&' | '=' | '<' | '>')) {
        if let Some((host, port_str)) = token.rsplit_once(':') {
            if !host.is_empty()
                && !host.starts_with("http")
                && port_str.chars().all(|d| d.is_ascii_digit())
                && !port_str.is_empty()
            {
                if let Ok(port) = port_str.parse::<u16>() {
                    if port > 0 && host.contains('.') {
                        let entry = format!("endpoint:{}:{}", host, port);
                        if !out.contains(&entry) {
                            out.push(entry);
                        }
                    }
                }
            }
        }
    }
    out
}

pub fn analyze_stream(data: &[u8]) -> ThreatReport {
    let entropy_bits = shannon_entropy(data);
    let extracted_patterns = mine_patterns(data);
    let mut anomalies = Vec::new();
    if entropy_bits > 7.8 && data.len() > 256 {
        anomalies.push("high_entropy_opaque_payload".to_string());
    }
    let text = String::from_utf8_lossy(data);
    if text.contains("X-Forwarded-For:") || text.contains("Via:") {
        anomalies.push("proxy_header_leakage_detected".to_string());
    }
    ThreatReport {
        entropy_bits,
        extracted_patterns,
        anomalies,
    }
}
