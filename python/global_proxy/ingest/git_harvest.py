# ffp: FFP-NIMBUS2-GIT-HARVEST io-edge python
"""GitHub & Gitee scraper — discovers proxy lists in public repositories.

Uses asynchronous REST/GraphQL API calls to search for repos containing
raw proxy lists, SOCKS5 endpoints, and WireGuard configurations.
"""

import asyncio
import logging
import re
from typing import AsyncIterator, Dict, List, Optional, Set
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Well-known proxy list repo patterns
REPO_QUERY_PATTERNS = [
    "proxy list",
    "socks5 proxy",
    "free proxy",
    "proxy list txt",
    "uk proxy",
]

# File patterns we care about
TARGET_FILE_PATTERNS = re.compile(
    r"(?:proxy|socks|http|ip.?list|node|endpoint)"
    r".*(?:\.txt|\.csv|\.json|\.yaml|\.yml|\.md)$",
    re.IGNORECASE,
)

# Inline proxy matchers
PROXY_LINE_RE = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3}){3})\s*:\s*(\d{2,5})"
    r"(?:\s*:\s*(\S+)\s*:\s*(\S+))?$"
)

DATACENTER_ASN_KEYWORDS = {
    "m247", "digitalocean", "hetzner", "amazon", "aws",
    "ovh", "online.net", "vultr", "linode", "contabo",
    "datacamp", "softlayer", "rackspace", "azure", "gcloud",
}


class GitHarvester:
    """Async scraper for GitHub/Gitee proxy repositories."""

    GITHUB_API = "https://api.github.com"
    GITEE_API = "https://gitee.com/api/v5"

    def __init__(
        self,
        github_token: Optional[str] = None,
        gitee_token: Optional[str] = None,
        max_repos: int = 30,
        max_files_per_repo: int = 50,
    ):
        self.github_token = github_token
        self.gitee_token = gitee_token
        self.max_repos = max_repos
        self.max_files_per_repo = max_files_per_repo

    def _github_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    def _gitee_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    async def _search_github_repos(self, client: httpx.AsyncClient) -> List[Dict]:
        """Search GitHub for repositories matching proxy queries."""
        repos: List[Dict] = []
        seen_urls: Set[str] = set()
        for query in REPO_QUERY_PATTERNS:
            url = f"{self.GITHUB_API}/search/repositories"
            params = {"q": query, "sort": "updated", "per_page": 10}
            try:
                resp = await client.get(url, params=params, headers=self._github_headers())
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("items", []):
                    clone_url = item.get("clone_url", "")
                    if clone_url and clone_url not in seen_urls:
                        seen_urls.add(clone_url)
                        repos.append({
                            "platform": "github",
                            "full_name": item.get("full_name", ""),
                            "clone_url": clone_url,
                            "default_branch": item.get("default_branch", "main"),
                        })
            except httpx.HTTPStatusError as exc:
                logger.warning("GitHub search error %s for query '%s'", exc.response.status_code, query)
            except Exception as exc:
                logger.warning("GitHub search failed for '%s': %s", query, exc)
            if len(repos) >= self.max_repos:
                break
        return repos[:self.max_repos]

    async def _search_gitee_repos(self, client: httpx.AsyncClient) -> List[Dict]:
        """Search Gitee for repositories matching proxy queries."""
        repos: List[Dict] = []
        seen_urls: Set[str] = set()
        for query in REPO_QUERY_PATTERNS[:3]:
            url = f"{self.GITEE_API}/search/repositories"
            params: Dict = {"q": query, "per_page": 10}
            if self.gitee_token:
                params["access_token"] = self.gitee_token
            try:
                resp = await client.get(url, params=params, headers=self._gitee_headers())
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        html_url = item.get("html_url", "")
                        if html_url and html_url not in seen_urls:
                            seen_urls.add(html_url)
                            repos.append({
                                "platform": "gitee",
                                "full_name": item.get("full_name", ""),
                                "clone_url": item.get("clone_url", ""),
                                "default_branch": item.get("default_branch", "master"),
                            })
            except Exception as exc:
                logger.warning("Gitee search failed for '%s': %s", query, exc)
        return repos

    async def _list_repo_files(
        self, client: httpx.AsyncClient, repo: Dict
    ) -> List[Dict[str, str]]:
        """List files in a repo via the tree API."""
        platform = repo["platform"]
        full_name = repo["full_name"]
        branch = repo.get("default_branch", "main")
        if platform == "github":
            url = f"{self.GITHUB_API}/repos/{full_name}/git/trees/{branch}"
            headers = self._github_headers()
        else:
            url = f"{self.GITEE_API}/repos/{full_name}/git/trees/{branch}"
            headers = self._gitee_headers()
            if self.gitee_token:
                url += f"?access_token={self.gitee_token}"
        try:
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            tree = data.get("tree", [])
            files = []
            for item in tree[:self.max_files_per_repo]:
                path = item.get("path", "")
                if TARGET_FILE_PATTERNS.search(path):
                    files.append({
                        "path": path,
                        "sha": item.get("sha", ""),
                        "size": str(item.get("size", 0)),
                    })
            return files
        except Exception as exc:
            logger.debug("Failed to list files for %s: %s", full_name, exc)
            return []

    async def _get_file_content(
        self, client: httpx.AsyncClient, repo: Dict, file_path: str
    ) -> Optional[str]:
        """Fetch raw file content from a repo."""
        platform = repo["platform"]
        full_name = repo["full_name"]
        branch = repo.get("default_branch", "main")
        if platform == "github":
            url = (
                f"https://raw.githubusercontent.com"
                f"/{full_name}/{branch}/{file_path}"
            )
            headers = self._github_headers()
        else:
            url = f"{self.GITEE_API}/repos/{full_name}/contents/{file_path}"
            headers = self._gitee_headers()
            if self.gitee_token:
                sep = "&" if "?" in url else "?"
                url += f"{sep}access_token={self.gitee_token}"
        try:
            resp = await client.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            if platform == "gitee":
                data = resp.json()
                import base64
                content = data.get("content", "")
                encoding = data.get("encoding", "")
                if encoding == "base64":
                    return base64.b64decode(content).decode(errors="replace")
                return content
            return resp.text
        except Exception as exc:
            logger.debug("Failed to fetch %s/%s: %s", full_name, file_path, exc)
            return None

    def _extract_proxies(self, content: str) -> List[Dict[str, str]]:
        """Extract proxy definitions from raw text."""
        proxies: List[Dict[str, str]] = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            match = PROXY_LINE_RE.match(line)
            if match:
                host, port = match.group(1), match.group(2)
                username = match.group(3) or ""
                password = match.group(4) or ""
                proxies.append({
                    "host": host,
                    "port": port,
                    "protocol": "http",
                    "username": username,
                    "password": password,
                })
                continue
            # Also try JSON-like proxy entries in markdown
            json_match = re.search(
                r'"host"\s*:\s*"([^"]+)".*?"port"\s*:\s*(\d+)', line
            )
            if json_match:
                proxies.append({
                    "host": json_match.group(1),
                    "port": json_match.group(2),
                    "protocol": "http",
                    "username": "",
                    "password": "",
                })
        return proxies

    async def harvest(self) -> AsyncIterator[Dict[str, str]]:
        """Yield proxy dicts discovered from GitHub and Gitee."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            github_repos = await self._search_github_repos(client)
            gitee_repos = await self._search_gitee_repos(client)
            all_repos = github_repos + gitee_repos

            for repo in all_repos:
                files = await self._list_repo_files(client, repo)
                for finfo in files:
                    content = await self._get_file_content(
                        client, repo, finfo["path"]
                    )
                    if not content:
                        continue
                    proxies = self._extract_proxies(content)
                    for p in proxies:
                        yield {
                            "host": p["host"],
                            "port": p["port"],
                            "protocol": p.get("protocol", "http"),
                            "username": p.get("username", ""),
                            "password": p.get("password", ""),
                            "source": f"{repo['platform']}:{repo['full_name']}",
                        }
