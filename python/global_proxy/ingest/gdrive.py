# ffp: FFP-NIMBUS2-GDRIVE io-edge python
"""Google Drive ingester — scans Drive folders for proxy node files.

Supports rclone-based enumeration and direct Drive API via service account.
Parses .txt (host:port:user:pass), .json (structured), and .csv credential files.
"""

import asyncio
import json
import csv
import io
import logging
import os
import subprocess
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


class GDriveIngester:
    """Scans a Google Drive folder (via rclone or API) for proxy definitions."""

    VALID_EXTENSIONS = {".txt", ".json", ".csv"}

    def __init__(
        self,
        rclone_remote: str = "gdrive",
        folder_path: str = "/Proxies",
        service_account_path: Optional[str] = None,
    ):
        self.rclone_remote = rclone_remote
        self.folder_path = folder_path
        self.service_account_path = service_account_path

    async def _rclone_list_files(self) -> List[Dict[str, str]]:
        """Use rclone ls to enumerate files in the configured remote folder."""
        remote = f"{self.rclone_remote}:{self.folder_path}"
        try:
            proc = await asyncio.create_subprocess_exec(
                "rclone", "ls", remote, "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode != 0:
                logger.warning("rclone ls failed: %s", stderr.decode(errors="replace"))
                return []
            raw = stdout.decode(errors="replace").strip()
            if not raw:
                return []
            entries = []
            for line in raw.splitlines():
                try:
                    obj = json.loads(line)
                    entries.append(obj)
                except json.JSONDecodeError:
                    continue
            return entries
        except FileNotFoundError:
            logger.error("rclone not found — install it or use the Drive API path")
            return []
        except asyncio.TimeoutError:
            logger.error("rclone ls timed out")
            return []

    async def _rclone_cat(self, remote_path: str) -> Optional[str]:
        """Read a single file's content via rclone cat."""
        full = f"{self.rclone_remote}:{self.folder_path}/{remote_path}"
        try:
            proc = await asyncio.create_subprocess_exec(
                "rclone", "cat", full,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            return stdout.decode(errors="replace")
        except Exception as exc:
            logger.warning("rclone cat %s failed: %s", remote_path, exc)
            return None

    def _parse_txt(self, content: str) -> List[Dict[str, str]]:
        """Parse host:port:user:pass or host:port lines."""
        proxies = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) >= 2:
                proxy: Dict[str, str] = {
                    "host": parts[0],
                    "port": parts[1],
                    "protocol": "http",
                }
                if len(parts) >= 4:
                    proxy["username"] = parts[2]
                    proxy["password"] = parts[3]
                proxies.append(proxy)
        return proxies

    def _parse_json(self, content: str) -> List[Dict[str, str]]:
        """Parse JSON containing a list of proxy objects or a single object."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [self._normalize_proxy(p) for p in data if isinstance(p, dict)]
        if isinstance(data, dict):
            if "proxies" in data and isinstance(data["proxies"], list):
                return [self._normalize_proxy(p) for p in data["proxies"] if isinstance(p, dict)]
            return [self._normalize_proxy(data)]
        return []

    def _parse_csv(self, content: str) -> List[Dict[str, str]]:
        """Parse CSV with columns like host,port,username,password."""
        proxies = []
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            host = row.get("host") or row.get("ip") or row.get("address", "")
            port = row.get("port", "")
            if host and port:
                proxy: Dict[str, str] = {
                    "host": host.strip(),
                    "port": str(port).strip(),
                    "protocol": "http",
                }
                for field in ("username", "user", "login"):
                    if field in row and row[field]:
                        proxy["username"] = row[field].strip()
                        break
                for field in ("password", "pass", "passwd"):
                    if field in row and row[field]:
                        proxy["password"] = row[field].strip()
                        break
                proxies.append(proxy)
        return proxies

    @staticmethod
    def _normalize_proxy(raw: Dict) -> Dict[str, str]:
        """Normalize a raw dict into the standard proxy dict format."""
        host = str(raw.get("host") or raw.get("ip") or raw.get("address", "")).strip()
        port = str(raw.get("port", "")).strip()
        return {
            "host": host,
            "port": port,
            "protocol": str(raw.get("protocol", "http")).strip(),
            "username": str(raw.get("username", "")).strip(),
            "password": str(raw.get("password", "")).strip(),
        }

    async def harvest(self) -> AsyncIterator[Dict[str, str]]:
        """Yield proxy dicts found in the configured Drive folder."""
        entries = await self._rclone_list_files()
        for entry in entries:
            name = entry.get("Name", "")
            ext = Path(name).suffix.lower()
            if ext not in self.VALID_EXTENSIONS:
                continue
            content = await self._rclone_cat(name)
            if not content:
                continue
            if ext == ".txt":
                proxies = self._parse_txt(content)
            elif ext == ".json":
                proxies = self._parse_json(content)
            elif ext == ".csv":
                proxies = self._parse_csv(content)
            else:
                continue
            for p in proxies:
                if p.get("host") and p.get("port"):
                    logger.info("gdrive: found proxy %s:%s", p["host"], p["port"])
                    yield p
