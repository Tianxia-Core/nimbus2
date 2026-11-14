# ffp: FFP-NIMBUS2-PROXY-SERVER io-edge python
"""Local SOCKS5/HTTP proxy server with rotation and sticky sessions.

Binds to 127.0.0.1:1080 and acts as a unified gateway forwarding
connections through the pool of validated UK residential proxies.
Supports dynamic IP rotation per request and sticky session pinning.
"""

import asyncio
import json
import logging
import random
import struct
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 1080
STICKY_DEFAULT_MINUTES = 15


@dataclass
class ProxyNode:
    """A validated proxy endpoint."""
    host: str
    port: int
    protocol: str = "http"
    username: str = ""
    password: str = ""
    latency_ms: float = 0.0
    country: str = "GB"
    asn: str = ""
    last_used: float = 0.0
    active_sessions: int = 0


@dataclass
class StickySession:
    """A pinned session mapping a client to a specific proxy."""
    client_key: str
    proxy: ProxyNode
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class ProxyPool:
    """Thread-safe proxy pool with rotation and sticky sessions."""

    def __init__(self):
        self._nodes: List[ProxyNode] = []
        self._sticky: Dict[str, StickySession] = {}
        self._lock = asyncio.Lock()

    async def add_nodes(self, nodes: List[ProxyNode]) -> None:
        """Add validated proxy nodes to the pool."""
        async with self._lock:
            existing_keys = {(n.host, n.port) for n in self._nodes}
            for node in nodes:
                if (node.host, node.port) not in existing_keys:
                    self._nodes.append(node)
                    existing_keys.add((node.host, node.port))

    async def remove_node(self, host: str, port: int) -> None:
        """Remove a node from the pool."""
        async with self._lock:
            self._nodes = [
                n for n in self._nodes if not (n.host == host and n.port == port)
            ]

    async def get_random(self) -> Optional[ProxyNode]:
        """Get a random proxy node from the pool."""
        async with self._lock:
            if not self._nodes:
                return None
            return random.choice(self._nodes)

    async def get_best(self) -> Optional[ProxyNode]:
        """Get the lowest-latency proxy node."""
        async with self._lock:
            if not self._nodes:
                return None
            return min(self._nodes, key=lambda n: n.latency_ms)

    async def get_sticky(
        self, client_key: str, duration_minutes: int = STICKY_DEFAULT_MINUTES
    ) -> ProxyNode:
        """Get or create a sticky session for a client."""
        async with self._lock:
            # Check existing session
            if client_key in self._sticky:
                session = self._sticky[client_key]
                if not session.is_expired:
                    return session.proxy
                else:
                    del self._sticky[client_key]

            # Create new sticky session
            if not self._nodes:
                raise RuntimeError("No proxy nodes available")

            # Prefer least-used node for new sessions
            node = min(self._nodes, key=lambda n: n.active_sessions)
            node.active_sessions += 1
            self._sticky[client_key] = StickySession(
                client_key=client_key,
                proxy=node,
                expires_at=time.time() + (duration_minutes * 60),
            )
            return node

    async def release_sticky(self, client_key: str) -> None:
        """Release a sticky session."""
        async with self._lock:
            session = self._sticky.pop(client_key, None)
            if session:
                session.proxy.active_sessions = max(
                    0, session.proxy.active_sessions - 1
                )

    async def mark_used(self, host: str, port: int) -> None:
        """Update last_used timestamp for a node."""
        async with self._lock:
            for node in self._nodes:
                if node.host == host and node.port == port:
                    node.last_used = time.time()
                    break

    async def snapshot(self) -> List[Dict]:
        """Return a JSON-serialisable snapshot of the pool."""
        async with self._lock:
            return [
                {
                    "host": n.host,
                    "port": n.port,
                    "protocol": n.protocol,
                    "latency_ms": n.latency_ms,
                    "country": n.country,
                    "asn": n.asn,
                    "active_sessions": n.active_sessions,
                }
                for n in self._nodes
            ]

    @property
    def size(self) -> int:
        return len(self._nodes)


class SOCKS5ProxyServer:
    """Async SOCKS5 proxy server with rotation support."""

    def __init__(
        self,
        pool: ProxyPool,
        bind_host: str = DEFAULT_BIND_HOST,
        bind_port: int = DEFAULT_BIND_PORT,
    ):
        self.pool = pool
        self.bind_host = bind_host
        self.bind_port = bind_port
        self._server: Optional[asyncio.AbstractServer] = None

    async def start(self) -> None:
        """Start the SOCKS5 server."""
        self._server = await asyncio.start_server(
            self._handle_client, self.bind_host, self.bind_port
        )
        logger.info(
            "SOCKS5 proxy listening on %s:%d", self.bind_host, self.bind_port
        )

    async def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single SOCKS5 client connection."""
        try:
            # Step 1: Authentication negotiation
            header = await reader.readexactly(2)
            version, nmethods = struct.unpack("!BB", header)
            if version != 0x05:
                writer.close()
                return
            methods = await reader.readexactly(nmethods)
            # No auth required
            writer.write(b"\x05\x00")
            await writer.drain()

            # Step 2: Connection request
            req = await reader.readexactly(4)
            ver, cmd, _, atyp = struct.unpack("!BBBB", req)
            if ver != 0x05 or cmd != 0x01:
                writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
                writer.close()
                return

            # Parse destination address
            if atyp == 0x01:  # IPv4
                addr_data = await reader.readexactly(4)
                dest_host = ".".join(str(b) for b in addr_data)
            elif atyp == 0x03:  # Domain
                len_byte = await reader.readexactly(1)
                domain_len = struct.unpack("!B", len_byte)[0]
                domain = await reader.readexactly(domain_len)
                dest_host = domain.decode("ascii", errors="replace")
            elif atyp == 0x04:  # IPv6
                addr_data = await reader.readexactly(16)
                dest_host = ":".join(
                    f"{addr_data[i]:02x}{addr_data[i+1]:02x}"
                    for i in range(0, 16, 2)
                )
            else:
                writer.write(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
                writer.close()
                return

            port_data = await reader.readexactly(2)
            dest_port = struct.unpack("!H", port_data)[0]

            # Get proxy for this connection (rotation)
            node = await self.pool.get_random()
            if not node:
                writer.write(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
                writer.close()
                return

            # Step 3: Connect through upstream proxy
            upstream_reader, upstream_writer = await asyncio.wait_for(
                self._connect_via_proxy(node, dest_host, dest_port),
                timeout=15,
            )

            # Send success response
            writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()

            await self.pool.mark_used(node.host, node.port)

            # Step 4: Bidirectional relay
            await self._relay(reader, writer, upstream_reader, upstream_writer)

        except asyncio.IncompleteReadError:
            pass
        except Exception as exc:
            logger.debug("SOCKS5 client error: %s", exc)
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _connect_via_proxy(
        self, node: ProxyNode, dest_host: str, dest_port: int
    ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Connect to destination through an upstream SOCKS5 proxy."""
        # Connect to the upstream proxy
        reader, writer = await asyncio.open_connection(node.host, node.port)

        # SOCKS5 handshake with upstream
        writer.write(b"\x05\x01\x00")  # No auth
        await writer.drain()
        resp = await reader.readexactly(2)
        if resp[1] != 0x00:
            raise ConnectionError("SOCKS5 upstream auth failed")

        # Request connection to destination
        dest_bytes = dest_host.encode("ascii")
        req = bytearray([
            0x05, 0x01, 0x00,
            0x03, len(dest_bytes),
        ])
        req.extend(dest_bytes)
        req.extend(struct.pack("!H", dest_port))
        writer.write(bytes(req))
        await writer.drain()

        # Read response
        resp = await reader.readexactly(10)
        if resp[1] != 0x00:
            raise ConnectionError(f"SOCKS5 upstream connect failed: {resp[1]}")

        return reader, writer

    async def _relay(
        self,
        client_r: asyncio.StreamReader,
        client_w: asyncio.StreamWriter,
        upstream_r: asyncio.StreamReader,
        upstream_w: asyncio.StreamWriter,
    ) -> None:
        """Bidirectional data relay between client and upstream proxy."""
        async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
            try:
                while True:
                    data = await src.read(8192)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except (asyncio.IncompleteReadError, ConnectionError, OSError):
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        task1 = asyncio.create_task(_pipe(client_r, upstream_w))
        task2 = asyncio.create_task(_pipe(upstream_r, client_w))
        await asyncio.gather(task1, task2, return_exceptions=True)


class ProxyTunnelManager:
    """Unified manager for the proxy pool and tunnel server."""

    def __init__(
        self,
        bind_host: str = DEFAULT_BIND_HOST,
        bind_port: int = DEFAULT_BIND_PORT,
    ):
        self.pool = ProxyPool()
        self.server = SOCKS5ProxyServer(self.pool, bind_host, bind_port)

    async def start(self) -> None:
        """Start the tunnel server."""
        await self.server.start()

    async def stop(self) -> None:
        """Stop the tunnel server."""
        await self.server.stop()

    async def load_proxies(self, proxy_dicts: List[Dict]) -> int:
        """Load proxy dicts into the pool. Returns count added."""
        nodes = []
        for p in proxy_dicts:
            try:
                nodes.append(ProxyNode(
                    host=p["host"],
                    port=int(p["port"]),
                    protocol=p.get("protocol", "http"),
                    username=p.get("username", ""),
                    password=p.get("password", ""),
                    latency_ms=float(p.get("latency_ms", 0)),
                    country=p.get("country", "GB"),
                    asn=p.get("asn", ""),
                ))
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping invalid proxy dict: %s", exc)
        await self.pool.add_nodes(nodes)
        return len(nodes)

    async def status(self) -> Dict:
        """Return current tunnel status."""
        nodes = await self.pool.snapshot()
        return {
            "bind": f"{self.server.bind_host}:{self.server.bind_port}",
            "pool_size": self.pool.size,
            "nodes": nodes,
        }
