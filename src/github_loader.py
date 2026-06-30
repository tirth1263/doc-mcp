import asyncio
import base64
import re
from dataclasses import dataclass
from typing import Optional
import aiohttp
from src.config import GITHUB_API_KEY, GITHUB_CONCURRENT_REQUESTS


@dataclass
class FileContent:
    path: str
    content: str
    sha: str
    url: str


def parse_repo_url(repo_input: str) -> tuple[str, str]:
    """Parse owner/repo from URL or shorthand."""
    repo_input = repo_input.strip().rstrip("/")
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.\s]+?)(?:\.git)?$",
        r"^([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, repo_input)
        if match:
            return match.group(1), match.group(2)
    raise ValueError(f"Cannot parse repository from: {repo_input}")


class GitHubLoader:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_API_KEY:
            self.headers["Authorization"] = f"token {GITHUB_API_KEY}"
        self.semaphore = asyncio.Semaphore(GITHUB_CONCURRENT_REQUESTS)

    async def _get(self, session: aiohttp.ClientSession, url: str) -> dict:
        async with self.semaphore:
            async with session.get(url, headers=self.headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def list_markdown_files(self, owner: str, repo: str) -> list[dict]:
        """Return list of markdown files with path and sha."""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
        async with aiohttp.ClientSession() as session:
            data = await self._get(session, url)
        return [
            item for item in data.get("tree", [])
            if item["type"] == "blob" and item["path"].endswith((".md", ".mdx"))
        ]

    async def fetch_file(self, session: aiohttp.ClientSession, owner: str, repo: str, file_info: dict) -> Optional[FileContent]:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_info['path']}"
        try:
            data = await self._get(session, url)
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return FileContent(
                path=file_info["path"],
                content=content,
                sha=data["sha"],
                url=data.get("html_url", ""),
            )
        except Exception as e:
            print(f"Error fetching {file_info['path']}: {e}")
            return None

    async def fetch_files(self, owner: str, repo: str, file_infos: list[dict], progress_cb=None) -> list[FileContent]:
        results = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_file(session, owner, repo, fi) for fi in file_infos]
            for i, coro in enumerate(asyncio.as_completed(tasks)):
                result = await coro
                if result:
                    results.append(result)
                if progress_cb:
                    progress_cb(i + 1, len(tasks))
        return results

    def list_markdown_files_sync(self, owner: str, repo: str) -> list[dict]:
        return asyncio.run(self.list_markdown_files(owner, repo))

    def fetch_files_sync(self, owner: str, repo: str, file_infos: list[dict], progress_cb=None) -> list[FileContent]:
        return asyncio.run(self.fetch_files(owner, repo, file_infos, progress_cb))
