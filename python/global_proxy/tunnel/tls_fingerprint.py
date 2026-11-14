# ffp: FFP-NIMBUS2-TLS-FINGERPRINT io-edge python
"""TLS Fingerprint Impersonation — browser-matching TLS handshake profiles.

Implements browser-matching TLS ClientHello profiles for Chrome and Edge
to make outbound proxy connections appear as genuine UK residential browsers.
"""

import ssl
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class TLSProfile:
    """A TLS ClientHello fingerprint profile."""
    name: str
    tls_version: int  # e.g. 0x0303 for TLS 1.2, 0x0304 for TLS 1.3
    cipher_suites: List[int] = field(default_factory=list)
    extensions: List[int] = field(default_factory=list)
    elliptic_curves: List[int] = field(default_factory=list)
    signature_algorithms: List[int] = field(default_factory=list)
    alpn_protocols: List[str] = field(default_factory=lambda: ["h2", "http/1.1"])
    supported_groups: List[int] = field(default_factory=lambda: [23, 24, 25])


# Chrome 120+ profile (2024)
CHROME_120 = TLSProfile(
    name="Chrome/120.0",
    tls_version=0x0303,
    cipher_suites=[
        0x1301,  # TLS_AES_128_GCM_SHA256
        0x1302,  # TLS_AES_256_GCM_SHA384
        0x1303,  # TLS_CHACHA20_POLY1305_SHA256
        0xC02B,  # ECDHE_ECDSA_AES_128_GCM_SHA256
        0xC02F,  # ECDHE_RSA_AES_128_GCM_SHA256
        0xC02C,  # ECDHE_ECDSA_AES_256_GCM_SHA384
        0xC030,  # ECDHE_RSA_AES_256_GCM_SHA384
        0xCCA9,  # ECDHE_ECDSA_CHACHA20_POLY1305
        0xCCA8,  # ECDHE_RSA_CHACHA20_POLY1305
        0x009C,  # RSA_AES_128_GCM_SHA256
        0x009D,  # RSA_AES_256_GCM_SHA384
        0x002F,  # RSA_AES_128_CBC_SHA256
        0x0035,  # RSA_AES_256_CBC_SHA256
        0x000A,  # RSA_AES_128_CBC_SHA
        0x0013,  # RSA_AES_256_CBC_SHA
    ],
    extensions=[
        0x0000,  # server_name
        0x0005,  # status_request
        0x000A,  # supported_groups
        0x000B,  # ec_point_formats
        0x000D,  # signature_algorithms
        0x0010,  # application_layer_protocol_negotiation
        0x0012,  # signed_certificate_timestamp (not in TLS 1.3)
        0x0017,  # extended_master_secret
        0x001B,  # compress_certificate
        0x0023,  # session_ticket
        0x002B,  # supported_versions
        0x002D,  # psk_key_exchange_modes
        0x0033,  # key_share
        0x7550,  # extensionEncryptedClientHello
        0xFF01,  # renegotiation_info
    ],
    elliptic_curves=[23, 24, 25, 29],
    signature_algorithms=[
        0x0403,  # ecdsa_secp256r1_sha256
        0x0804,  # rsa_pss_rsae_sha256
        0x0401,  # rsa_pkcs1_sha256
        0x0503,  # ecdsa_secp384r1_sha384
        0x0805,  # rsa_pss_rsae_sha384
        0x0501,  # rsa_pkcs1_sha384
        0x0806,  # rsa_pss_rsae_sha512
        0x0601,  # rsa_pkcs1_sha512
    ],
    alpn_protocols=["h2", "http/1.1"],
    supported_groups=[23, 24, 25, 29],
)

# Edge 120+ profile (essentially identical to Chrome since Edge is Chromium-based)
EDGE_120 = TLSProfile(
    name="Edge/120.0",
    tls_version=0x0303,
    cipher_suites=CHROME_120.cipher_suites.copy(),
    extensions=CHROME_120.extensions.copy(),
    elliptic_curves=CHROME_120.elliptic_curves.copy(),
    signature_algorithms=CHROME_120.signature_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    supported_groups=[23, 24, 25, 29],
)

# Firefox 121 profile
FIREFOX_121 = TLSProfile(
    name="Firefox/121.0",
    tls_version=0x0303,
    cipher_suites=[
        0x1301,
        0x1303,
        0x1302,
        0xC02B,
        0xC02F,
        0xC02C,
        0xC030,
        0xCCA9,
        0xCCA8,
        0x009C,
        0x009D,
        0x002F,
        0x0035,
    ],
    extensions=[
        0x0000,
        0x0005,
        0x000A,
        0x000B,
        0x000D,
        0x0010,
        0x0017,
        0x002B,
        0x002D,
        0x0033,
        0xFF01,
    ],
    elliptic_curves=[23, 24, 25, 29],
    signature_algorithms=[
        0x0403,
        0x0503,
        0x0603,
        0x0804,
        0x0805,
        0x0806,
        0x0401,
        0x0501,
        0x0601,
    ],
    alpn_protocols=["h2", "http/1.1"],
    supported_groups=[23, 24, 25, 29],
)

# Available profiles for rotation
PROFILES = {
    "chrome": CHROME_120,
    "edge": EDGE_120,
    "firefox": FIREFOX_121,
}


def get_profile(name: str = "chrome") -> TLSProfile:
    """Get a named TLS profile."""
    key = name.lower()
    if key not in PROFILES:
        key = "chrome"
    return PROFILES[key]


def create_ssl_context(
    profile: Optional[TLSProfile] = None,
    hostname: Optional[str] = None,
) -> ssl.SSLContext:
    """Create an SSL context configured to match a browser TLS profile.

    Uses Python's ssl module to approximate the target profile. Full JA3
    matching requires custom OpenSSL builds or libraries like `tls-client`.
    This provides a best-effort approximation.
    """
    if profile is None:
        profile = CHROME_120

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Disable older TLS versions — match the profile's minimum
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    # Set the highest supported version
    if profile.tls_version >= 0x0304:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    else:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2

    # Build cipher list string for the context
    cipher_list = []
    for cs in profile.cipher_suites:
        if cs < 0x0300:  # Non-TLS 1.3 cipher suites use string names
            cipher_list.append(_cipher_id_to_name(cs))
    if cipher_list:
        try:
            ctx.set_ciphers(":".join(cipher_list))
        except ssl.SSLError:
            pass  # Fall back to defaults

    # Disable compression (matching modern browsers)
    ctx.options |= ssl.OP_NO_COMPRESSION

    # Enable SNI
    if hostname:
        ctx.hostname = hostname

    return ctx


def _cipher_id_to_name(cipher_id: int) -> str:
    """Map TLS cipher suite IDs to OpenSSL cipher names."""
    CIPHER_MAP = {
        0x000A: "AES128-SHA",
        0x0013: "AES256-SHA",
        0x002F: "AES128-SHA256",
        0x0035: "AES256-SHA256",
        0x009C: "AES128-GCM-SHA256",
        0x009D: "AES256-GCM-SHA384",
        0xC02B: "ECDHE-ECDSA-AES128-GCM-SHA256",
        0xC02C: "ECDHE-ECDSA-AES256-GCM-SHA384",
        0xC02F: "ECDHE-RSA-AES128-GCM-SHA256",
        0xC030: "ECDHE-RSA-AES256-GCM-SHA384",
        0xCCA8: "ECDHE-RSA-CHACHA20-POLY1305",
        0xCCA9: "ECDHE-ECDSA-CHACHA20-POLY1305",
    }
    return CIPHER_MAP.get(cipher_id, f"UNKNOWN-{cipher_id:04X}")


def build_client_hello_bytes(profile: Optional[TLSProfile] = None) -> bytes:
    """Build raw ClientHello bytes matching a TLS profile.

    This is useful for custom TLS implementations that need to send
    an exact ClientHello matching a browser fingerprint.
    """
    if profile is None:
        profile = CHROME_120

    # TLS ClientHello structure
    # Handshake type
    handshake = bytes([0x16, 0x03, 0x01])

    # ClientHello message
    client_hello = bytearray()

    # Legacy version
    client_hello.extend(b"\x03\x03")

    # Random (32 bytes)
    client_hello.extend(b"\x00" * 32)

    # Session ID length (0)
    client_hello.append(0x00)

    # Cipher suites
    cs_bytes = bytearray()
    for cs in profile.cipher_suites:
        cs_bytes.extend(cs.to_bytes(2, "big"))
    client_hello.extend(len(cs_bytes).to_bytes(2, "big"))
    client_hello.extend(cs_bytes)

    # Compression methods (null only)
    client_hello.append(0x01)
    client_hello.append(0x00)

    # Extensions
    ext_data = bytearray()
    for ext_id in profile.extensions:
        ext_data.extend(ext_id.to_bytes(2, "big"))
        # Empty extension data (placeholder)
        ext_data.extend(b"\x00\x00")

    client_hello.extend(len(ext_data).to_bytes(2, "big"))
    client_hello.extend(ext_data)

    # Wrap in handshake header
    msg = bytearray()
    msg.append(0x01)  # ClientHello
    msg.extend(len(client_hello).to_bytes(3, "big"))
    msg.extend(client_hello)

    # Final record
    record = bytearray(handshake)
    record.extend(len(msg).to_bytes(2, "big"))
    record.extend(msg)

    return bytes(record)
