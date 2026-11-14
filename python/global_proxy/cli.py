#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-CLI io-edge python
"""UK-Proxy-Engine CLI — control interface for the proxy orchestrator.

Usage:
    python cli.py --rotate               Rotate to a new UK exit IP
    python cli.py --test-ip <IP:PORT>    Test a specific proxy endpoint
    python cli.py --export-socks5        Export active SOCKS5 endpoints as JSON
    python cli.py --sync-drive           Sync proxy lists from Google Drive
    python cli.py --start                Start the local tunnel server
    python cli.py --status               Show current proxy pool status
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from ingest.gdrive import GDriveIngester
from ingest.git_harvest import GitHarvester
from ingest.academic_harvest import AcademicHarvester
from ingest.web_harvest import WebHarvester
from ingest.nimbus_tester import NimbusProxyTester
from ingest.kai3_rotation import KAIRotation
from ingest.ireb_recovery import IREBRecovery
from ingest.pari_analyzer import PARIAnalyzer
from ingest.millihan_optimizer import MillihanOptimizer
from ingest.densehan_optimizer import DenseHanOptimizer
from validator.asn_check import ASNChecker
from validator.latency import LatencyChecker
from validator.veritas_rex import VeritasRex
from tunnel.proxy_server import ProxyPool, ProxyTunnelManager, ProxyNode

logger = logging.getLogger("uk_proxy_engine")

if HAS_RICH:
    console = Console()
else:
    console = None


def _print_json(data: dict) -> None:
    """Print data as formatted JSON."""
    if HAS_RICH:
        console.print_json(json.dumps(data, indent=2))
    else:
        print(json.dumps(data, indent=2))


def _print_table(title: str, rows: List[Dict], columns: List[str]) -> None:
    """Print data as a table."""
    if not HAS_RICH:
        for row in rows:
            print(json.dumps({c: row.get(c, "") for c in columns}))
        return
    table = Table(title=title)
    for col in columns:
        table.add_column(col, style="cyan")
    for row in rows:
        table.add_row(*[str(row.get(c, "")) for c in columns])
    console.print(table)


def _print_status(msg: str, style: str = "bold green") -> None:
    """Print a status message."""
    if HAS_RICH:
        console.print(f"[{style}]{msg}[/{style}]")
    else:
        print(msg)


async def cmd_rotate(args: argparse.Namespace) -> None:
    """Rotate to a new UK exit IP."""
    _print_status("Rotating UK exit IP...")
    tunnel = ProxyTunnelManager()

    # Run all harvesters
    proxies = await _run_all_harvesters()
    if not proxies:
        _print_status("No proxies discovered", style="bold red")
        return

    # Validate
    validated = await _validate_proxies(proxies)
    if not validated:
        _print_status("No valid UK residential proxies found", style="bold red")
        return

    # Pick the best one
    best = min(validated, key=lambda p: p.get("latency_ms", 99999))
    _print_json({
        "action": "rotate",
        "new_exit_ip": best["proxy"]["host"],
        "port": best["proxy"]["port"],
        "latency_ms": best["latency_ms"],
        "exit_country": best.get("exit_country", "GB"),
    })


async def cmd_test_ip(args: argparse.Namespace) -> None:
    """Test a specific proxy endpoint."""
    target = args.test_ip
    if ":" not in target:
        _print_status("Format: IP:PORT", style="bold red")
        return

    host, port = target.rsplit(":", 1)
    proxy = {"host": host, "port": port, "protocol": args.protocol or "http"}

    _print_status(f"Testing proxy {host}:{port}...")
    checker = LatencyChecker(
        max_latency_ms=args.max_latency,
        require_uk_exit=not args.skip_geo,
    )
    result = await checker.validate(proxy)

    _print_json({
        "proxy": f"{host}:{port}",
        "valid": result["ok"],
        "latency_ms": round(result["latency_ms"], 1),
        "header_leakage": result["header_leakage"],
        "exit_country": result.get("exit_country"),
        "errors": result["errors"],
    })


async def cmd_export_socks5(args: argparse.Namespace) -> None:
    """Export active SOCKS5 endpoints as JSON."""
    tunnel = ProxyTunnelManager()
    status = await tunnel.status()

    endpoints = []
    for node in status.get("nodes", []):
        endpoints.append({
            "socks5": f"socks5://{node['host']}:{node['port']}",
            "http": f"http://{node['host']}:{node['port']}",
            "latency_ms": node.get("latency_ms", 0),
            "country": node.get("country", "GB"),
        })

    _print_json({
        "total": len(endpoints),
        "local_socks5": f"socks5://{status['bind']}",
        "endpoints": endpoints,
    })


async def cmd_sync_drive(args: argparse.Namespace) -> None:
    """Sync proxy lists from Google Drive."""
    _print_status("Syncing proxy lists from Google Drive...")
    ingester = GDriveIngester(
        rclone_remote=args.gdrive_remote,
        folder_path=args.gdrive_folder,
    )
    proxies = []
    async for proxy in ingester.harvest():
        proxies.append(proxy)

    _print_json({
        "action": "sync_drive",
        "proxies_found": len(proxies),
        "proxies": proxies[:50],  # cap output
    })


async def cmd_start(args: argparse.Namespace) -> None:
    """Start the local tunnel server."""
    _print_status(
        f"Starting UK-Proxy-Engine tunnel on "
        f"{args.bind_host}:{args.bind_port}..."
    )

    tunnel = ProxyTunnelManager(args.bind_host, args.bind_port)

    # Background: harvest and validate
    async def _background_harvest() -> None:
        while True:
            try:
                proxies = await _run_all_harvesters()
                if proxies:
                    validated = await _validate_proxies(proxies)
                    good = [v["proxy"] for v in validated if v.get("ok")]
                    if good:
                        await tunnel.pool.add_nodes([
                            ProxyNode(
                                host=p["host"],
                                port=int(p["port"]),
                                protocol=p.get("protocol", "http"),
                                username=p.get("username", ""),
                                password=p.get("password", ""),
                            )
                            for p in good
                        ])
                        _print_status(
                            f"Pool updated: {tunnel.pool.size} valid proxies"
                        )
            except Exception as exc:
                logger.warning("Harvest cycle failed: %s", exc)
            await asyncio.sleep(args.refresh_interval)

    await tunnel.start()
    harvest_task = asyncio.create_task(_background_harvest())

    try:
        _print_status("Tunnel is running. Press Ctrl+C to stop.")
        _print_json({
            "status": "running",
            "bind": f"{args.bind_host}:{args.bind_port}",
            "protocol": "socks5",
        })
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        harvest_task.cancel()
        await tunnel.stop()
        _print_status("Tunnel stopped.")


async def cmd_status(args: argparse.Namespace) -> None:
    """Show current proxy pool status."""
    tunnel = ProxyTunnelManager()
    status = await tunnel.status()

    _print_table(
        title="UK-Proxy-Engine Pool Status",
        rows=status.get("nodes", []),
        columns=["host", "port", "protocol", "latency_ms", "country", "asn", "active_sessions"],
    )

    if not HAS_RICH:
        _print_json(status)


async def _run_all_harvesters() -> List[Dict]:
    """Run all ingestion sources and return combined proxy list."""
    all_proxies: List[Dict] = []

    # Drive
    try:
        drive = GDriveIngester()
        async for p in drive.harvest():
            p["source"] = "gdrive"
            all_proxies.append(p)
    except Exception as exc:
        logger.debug("Drive harvest skipped: %s", exc)

    # Git
    try:
        git = GitHarvester()
        async for p in git.harvest():
            all_proxies.append(p)
    except Exception as exc:
        logger.debug("Git harvest skipped: %s", exc)

    # Web
    try:
        web = WebHarvester()
        async for p in web.harvest():
            p["source"] = p.get("source", "web")
            all_proxies.append(p)
    except Exception as exc:
        logger.debug("Web harvest skipped: %s", exc)

    return all_proxies


async def _validate_proxies(proxies: List[Dict]) -> List[Dict]:
    """Validate a batch of proxies through ASN and latency checks."""
    if not proxies:
        return []

    asn_checker = ASNChecker()
    latency_checker = LatencyChecker()

    import httpx
    results = []
    async with httpx.AsyncClient() as client:
        for proxy in proxies[:200]:  # cap at 200 for practical limits
            host = proxy.get("host", "")
            # ASN check
            asn_result = await asn_checker.check_uk_residential(host, client)
            if not asn_result.get("is_valid"):
                continue
            # Latency check
            lat_result = await latency_checker.validate(proxy)
            lat_result["asn_info"] = asn_result
            results.append(lat_result)

    return results


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="uk-proxy-engine",
        description="UK Residential Proxy Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    sub = parser.add_subparsers(dest="command")

    # rotate
    sub.add_parser("rotate", help="Rotate to a new UK exit IP")

    # test-ip
    test_p = sub.add_parser("test-ip", help="Test a specific proxy")
    test_p.add_argument("target", help="IP:PORT to test")
    test_p.add_argument("--protocol", default="http", help="Proxy protocol")
    test_p.add_argument("--max-latency", type=int, default=250, help="Max latency in ms")
    test_p.add_argument("--skip-geo", action="store_true", help="Skip UK exit check")

    # export-socks5
    sub.add_parser("export-socks5", help="Export SOCKS5 endpoints as JSON")

    # sync-drive
    sync_p = sub.add_parser("sync-drive", help="Sync from Google Drive")
    sync_p.add_argument("--gdrive-remote", default="gdrive", help="Rclone remote name")
    sync_p.add_argument("--gdrive-folder", default="/Proxies", help="Drive folder path")

    # start
    start_p = sub.add_parser("start", help="Start the tunnel server")
    start_p.add_argument("--bind-host", default="127.0.0.1", help="Bind host")
    start_p.add_argument("--bind-port", type=int, default=1080, help="Bind port")
    start_p.add_argument(
        "--refresh-interval", type=int, default=300,
        help="Harvest refresh interval in seconds",
    )

    # status
    sub.add_parser("status", help="Show pool status")

    return parser


def main() -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "rotate": cmd_rotate,
        "test-ip": cmd_test_ip,
        "export-socks5": cmd_export_socks5,
        "sync-drive": cmd_sync_drive,
        "start": cmd_start,
        "status": cmd_status,
    }

    handler = cmd_map.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    asyncio.run(handler(args))


if __name__ == "__main__":
    main()
