from dataclasses import dataclass
import os
from typing import Any, Dict, Optional

import httpx


QUALITY_GATE_MARKER = "<!-- quality-gate-agent -->"


@dataclass(frozen=True)
class GitHubPullRequest:
    owner: str
    repo: str
    number: int


class GitHubClient:
    def __init__(
        self,
        token: Optional[str] = None,
        api_url: str = "https://api.github.com",
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._token = token or os.getenv("GITHUB_TOKEN")
        self._client = httpx.Client(
            base_url=api_url.rstrip("/"),
            headers=self._headers(),
            timeout=30.0,
            transport=transport,
        )

    def _headers(self, accept: str = "application/vnd.github+json") -> Dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def get_pull_request_diff(self, pull_request: GitHubPullRequest) -> str:
        response = self._client.get(
            f"/repos/{pull_request.owner}/{pull_request.repo}/pulls/{pull_request.number}",
            headers=self._headers("application/vnd.github.v3.diff"),
        )
        response.raise_for_status()
        return response.text

    def upsert_pull_request_comment(
        self,
        pull_request: GitHubPullRequest,
        body: str,
    ) -> str:
        if not self._token:
            raise ValueError("GITHUB_TOKEN is required to publish a pull request comment.")

        comments_path = (
            f"/repos/{pull_request.owner}/{pull_request.repo}/issues/"
            f"{pull_request.number}/comments"
        )
        comments_response = self._client.get(comments_path)
        comments_response.raise_for_status()
        comments = comments_response.json()
        marked_body = f"{QUALITY_GATE_MARKER}\n{body}"

        existing_comment = next(
            (
                comment
                for comment in comments
                if QUALITY_GATE_MARKER in str(comment.get("body", ""))
            ),
            None,
        )

        if existing_comment:
            response = self._client.patch(
                f"/repos/{pull_request.owner}/{pull_request.repo}/issues/comments/"
                f"{existing_comment['id']}",
                json={"body": marked_body},
            )
        else:
            response = self._client.post(
                comments_path,
                json={"body": marked_body},
            )

        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
        return str(payload["html_url"])

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
