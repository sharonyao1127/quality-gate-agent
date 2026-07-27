import json

import httpx
import pytest

from src.github_client import (
    QUALITY_GATE_MARKER,
    GitHubClient,
    GitHubPullRequest,
)


PULL_REQUEST = GitHubPullRequest(owner="example", repo="project", number=42)


def test_get_pull_request_diff_requests_diff_media_type():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/example/project/pulls/42"
        assert request.headers["accept"] == "application/vnd.github.v3.diff"
        return httpx.Response(200, text="diff --git a/app.py b/app.py")

    with GitHubClient(transport=httpx.MockTransport(handler)) as client:
        diff = client.get_pull_request_diff(PULL_REQUEST)

    assert diff.startswith("diff --git")


def test_upsert_pull_request_comment_creates_marked_comment():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        payload = json.loads(request.content)
        assert payload["body"].startswith(QUALITY_GATE_MARKER)
        return httpx.Response(
            201,
            json={"html_url": "https://github.com/example/project/pull/42#issuecomment-1"},
        )

    with GitHubClient(token="token", transport=httpx.MockTransport(handler)) as client:
        comment_url = client.upsert_pull_request_comment(PULL_REQUEST, "## Result")

    assert requests[-1].method == "POST"
    assert comment_url.endswith("issuecomment-1")


def test_upsert_pull_request_comment_updates_existing_comment():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json=[{"id": 99, "body": f"{QUALITY_GATE_MARKER}\nold"}],
            )
        assert request.method == "PATCH"
        assert request.url.path.endswith("/issues/comments/99")
        return httpx.Response(
            200,
            json={"html_url": "https://github.com/example/project/pull/42#issuecomment-99"},
        )

    with GitHubClient(token="token", transport=httpx.MockTransport(handler)) as client:
        comment_url = client.upsert_pull_request_comment(PULL_REQUEST, "## Updated")

    assert comment_url.endswith("issuecomment-99")


def test_publish_comment_requires_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with GitHubClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            client.upsert_pull_request_comment(PULL_REQUEST, "body")
