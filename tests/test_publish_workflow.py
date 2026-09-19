"""The PyPI workflow publishes only an existing immutable release tag."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]

WORKFLOW = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(
    encoding="utf-8"
)


def test_sdist_excludes_local_virtual_environments_and_build_caches():
    """A checkout carrying a local venv must not ship it to PyPI.

    hatchling walks the working tree, so a developer venv or a uv build cache
    beside the sources lands in the sdist unless the exclude list names it.
    """
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    exclude = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]
    assert {
        ".venv*",
        "**/.venv*",
        ".uv-build-cache",
        "**/.uv-build-cache",
    } <= set(exclude)


def test_publish_workflow_actions_use_full_commit_shas():
    uses = re.findall(r"^\s*-?\s*uses:\s*[^@\s]+@([^\s#]+)", WORKFLOW, re.MULTILINE)
    assert uses
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in uses)


def test_manual_publish_requires_and_checks_out_an_existing_tag():
    assert re.search(r"workflow_dispatch:\s*\n\s*inputs:\s*\n\s*tag:", WORKFLOW)
    assert "ref: refs/tags/${{ steps.candidate.outputs.tag }}" in WORKFLOW
    assert 'git show-ref --verify --quiet "refs/tags/$TAG"' in WORKFLOW
    assert 'git rev-parse "$TAG^{commit}"' in WORKFLOW
    assert 'git ls-remote origin "refs/tags/$TAG^{}"' in WORKFLOW


def test_publish_requires_matching_version_and_published_release():
    assert '[[ "$TAG" != "v$version" ]]' in WORKFLOW
    assert "releases/tags/$TAG" in WORKFLOW
    assert "select(.draft == false and .prerelease == false)" in WORKFLOW
