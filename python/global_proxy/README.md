# UK-Proxy-Engine

Production-ready, asynchronous Python tool that continuously discovers, validates, and exposes clean UK Residential and Mobile (ISP) proxy endpoints as a local SOCKS5/HTTP tunnel interface.

## Architecture

```
uk_proxy_fabricator/
├── ingest/                     # Multi-source ingestion engine
│   ├── gdrive.py               # Google Drive folder scanner (rclone)
│   ├── git_harvest.py          # GitHub & Gitee proxy repo scraper
│   ├── academic_harvest.py     # Arxiv/CNKI anti-detection research
│   └── web_harvest.py          # DuckDuckGo/SearXNG proxy discovery
├── validator/                  # ASN filter & validation matrix
│   ├── asn_check.py            # Global residential/mobile ASN enforcement
│   └── latency.py              # Latency, anonymity & GeoIP verification
├── tunnel/                     # Local proxy tunnel & rotator
│   ├── proxy_server.py         # SOCKS5 server with rotation & sticky sessions
│   └── tls_fingerprint.py      # Chrome/Edge/Firefox TLS ClientHello profiles
├── cli.py                      # CLI control interface
├── requirements.txt
└── README.md
```

## Install

```bash
pip install -r requirements.txt
```

Optional: install [rclone](https://rclone.org/) for Google Drive integration.

## Usage

```bash
# Start the tunnel server (harvests + validates + serves on 127.0.0.1:1080)
python cli.py start

# Rotate to a new UK exit IP
python cli.py rotate

# Test a specific proxy
python cli.py test-ip 185.23.45.67:8080

# Export active endpoints as JSON
python cli.py export-socks5

# Show current pool status
python cli.py status

# Sync proxy lists from Google Drive
python cli.py sync-drive --gdrive-remote mydrive --gdrive-folder /Proxies

# Verbose mode
python cli.py start --verbose
```

## Ingestion Sources

| Source | Module | Method |
|--------|--------|--------|
| Google Drive | `ingest/gdrive.py` | rclone API — scans `.txt`, `.json`, `.csv` files |
| GitHub/Gitee | `ingest/git_harvest.py` | REST API — searches repos for proxy lists |
| Arxiv/CNKI | `ingest/academic_harvest.py` | Arxiv Atom API — extracts anti-detection techniques |
| Web Search | `ingest/web_harvest.py` | DuckDuckGo Lite + SearXNG instances |

## Validation Pipeline

1. **ASN Check** — queries ipinfo.io, rejects datacenter ASNs, enforces Global residential/mobile
2. **Latency Test** — verifies < 250ms response through the proxy
3. **Header Leakage** — detects `X-Forwarded-For`, `Via`, and other proxy indicators
4. **GeoIP Exit** — confirms UK exit node (country: GB)

## Supported UK ASNs

- Virgin Media (AS5089)
- BT / BT Consumer (AS2856)
- Sky Broadband (AS5607)
- EE / BT Mobile (AS12576)
- Vodafone UK (AS25152)
- O2 / Telefonica UK (AS2856)
- TalkTalk (AS9105)
- Plusnet (AS2856)
- Hyperoptic (AS57361)
- Three / Hutchison UK (AS3356)
- And more...

## TLS Fingerprinting

`tunnel/tls_fingerprint.py` provides browser-matching TLS profiles:
- Chrome 120+ (default)
- Edge 120+
- Firefox 121+

## Code Quality

- Zero brittle external dependencies (only `httpx`, `aiohttp`, `pysocks`, `rich`)
- Full `asyncio` concurrency throughout
- Graceful error handling with automatic retry fallbacks
- Clean JSON status streams for monitoring
