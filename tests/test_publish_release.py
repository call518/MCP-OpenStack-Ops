"""Verify release publication without writing Git state or calling GitHub."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import publish_release

REPOSITORY = "example/project"
CURRENT = "b" * 40
BASE = "a" * 40


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"calls": [], "created": [], "releases": [[]]}

    def execute(*args: str) -> str:
        state["calls"].append(args)
        if args[:3] == ("gh", "release", "create"):
            path = Path(args[args.index("--notes-file") + 1])
            state["created"].append((args, path.read_text()))
            return "https://github.com/example/project/releases/tag/0.6.6"
        if args[:2] == ("gh", "api"):
            if "--paginate" in args:
                if state.get("api_failure"):
                    raise subprocess.CalledProcessError(1, args, stderr="API failed")
                return json.dumps(state["releases"])
            return state.get("remote", CURRENT)
        if args == ("git", "rev-parse", "HEAD"):
            return state.get("head", CURRENT)
        if args[:3] == ("git", "rev-parse", "--verify"):
            return (
                CURRENT
                if args[-1].endswith("0.6.6^{commit}")
                or args[-1].endswith("0.6.6rc1^{commit}")
                else BASE
            )
        if args[:3] == ("git", "merge-base", "--is-ancestor"):
            if state.get("unrelated"):
                raise subprocess.CalledProcessError(1, args)
            return ""
        if args[:2] == ("git", "log"):
            return (
                f"{'c' * 40}\0feat: first change\n\nBREAKING CHANGE: use start\n\0\n"
                f"{CURRENT}\0fix: second change\n\n```sh\n$(touch marker)\n```\n\0"
            )
        raise AssertionError(args)

    monkeypatch.setattr(publish_release, "command", execute)
    return state


def release(tag: str, published_at: str, *, draft: bool = False) -> dict[str, Any]:
    return {"tag_name": tag, "published_at": published_at, "draft": draft}


def test_uses_previous_published_release_across_pages(commands) -> None:
    commands["releases"] = [
        [release("0.6.5", "2026-10-24T12:00:00Z", draft=True)],
        [release("0.6.4", "2026-10-23T12:00:00Z")],
        [release("0.6.3", "2026-10-22T12:00:00Z")],
    ]
    publish_release.publish_release(REPOSITORY, "0.6.6")
    args, notes = commands["created"][0]
    assert "--verify-tag" in args
    assert args[args.index("--title") + 1] == "0.6.6"
    assert "Changes since 0.6.4." in notes
    assert "0.6.4...0.6.6" in notes
    assert notes.index("first change") < notes.index("second change")
    assert "BREAKING CHANGE: use start" in notes
    assert "$(touch marker)" in notes
    assert "````text" in notes
    assert ("git", "merge-base", "--is-ancestor", BASE, CURRENT) in commands["calls"]
    log = next(call for call in commands["calls"] if call[:2] == ("git", "log"))
    assert "--reverse" in log and "--topo-order" in log
    assert f"{BASE}..{CURRENT}" in log
    assert not Path(args[args.index("--notes-file") + 1]).exists()


def test_published_release_is_not_overwritten(commands) -> None:
    commands["releases"] = [[release("0.6.6", "2026-10-24T12:00:00Z")]]
    publish_release.publish_release(REPOSITORY, "0.6.6")
    assert commands["created"] == []
    assert not any(call[:2] == ("git", "log") for call in commands["calls"])


def test_existing_draft_requires_manual_review(commands) -> None:
    commands["releases"] = [[release("0.6.6", "", draft=True)]]
    with pytest.raises(ValueError, match="draft already exists"):
        publish_release.publish_release(REPOSITORY, "0.6.6")
    assert commands["created"] == []


def test_first_release_includes_all_history(commands) -> None:
    publish_release.publish_release(REPOSITORY, "0.6.6")
    _, notes = commands["created"][0]
    assert "Initial release." in notes
    assert "Full Changelog" not in notes
    log = next(call for call in commands["calls"] if call[:2] == ("git", "log"))
    assert log[-2:] == (CURRENT, "--")


def test_prerelease_is_not_marked_latest(commands) -> None:
    publish_release.publish_release(REPOSITORY, "0.6.6rc1")
    args, _ = commands["created"][0]
    assert "--prerelease" in args and "--latest=false" in args


@pytest.mark.parametrize("field", ["remote", "head"])
def test_mismatched_commit_blocks_publication(commands, field) -> None:
    commands[field] = "d" * 40
    with pytest.raises(ValueError, match="must match"):
        publish_release.publish_release(REPOSITORY, "0.6.6")
    assert commands["created"] == []


@pytest.mark.parametrize("failure", ["api_failure", "unrelated"])
def test_api_or_ancestry_failure_does_not_publish(commands, failure) -> None:
    commands["releases"] = [[release("0.6.4", "2026-10-23T12:00:00Z")]]
    commands[failure] = True
    with pytest.raises(subprocess.CalledProcessError):
        publish_release.publish_release(REPOSITORY, "0.6.6")
    assert commands["created"] == []


def test_invalid_tag_does_not_call_commands(commands) -> None:
    with pytest.raises(ValueError):
        publish_release.publish_release(REPOSITORY, "$(touch marker)")
    assert commands["calls"] == []


def test_release_job_is_separate_and_uses_scoped_permissions() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/pypi-publish.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["release"]
    assert job["needs"] == "publish-to-pypi"
    assert job["permissions"] == {"contents": "write"}
    assert job["concurrency"]["cancel-in-progress"] is False
    assert job["concurrency"]["queue"] == "max"
    assert job["steps"][0]["with"]["fetch-depth"] == 0
    assert job["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert (
        job["steps"][-1]["run"] == 'python3 -m scripts.publish_release "$RELEASE_TAG"'
    )
    for name in ("publish-to-testpypi", "publish-to-pypi"):
        assert workflow["jobs"][name]["permissions"] == {"id-token": "write"}

