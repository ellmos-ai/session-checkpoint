from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility path
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_module_manifest_declares_the_narrow_boundary():
    manifest = json.loads((ROOT / "ellmos-module.v2.json").read_text(encoding="utf-8"))
    assert manifest["id"] == "session-checkpoint"
    assert manifest["boundaries"]["network"] == "none"
    assert manifest["state"]["ownership"] == "module"
    assert "session.checkpoint" in manifest["provides"]
    assert manifest["visibility"] == "private"


def test_tracked_text_has_no_host_or_personal_paths():
    forbidden = (
        "ASUS" + "-GEI",
        "WORKSTATION" + "-LG",
        "C:" + "\\Users\\",
        "One" + "Drive",
        "bach" + ".db",
    )
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.name.startswith("LOCK."):
            continue
        if path.suffix not in {".py", ".md", ".json", ".toml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in text, f"{value!r} leaked into {path.relative_to(ROOT)}"


def test_german_readme_uses_real_umlauts_without_mojibake():
    text = (ROOT / "README_de.md").read_text(encoding="utf-8")
    assert "für" in text
    assert "Löschung" in text
    assert not any(marker in text for marker in ("Ã", "Â", "â€", "�"))


def test_ci_workflows_pin_actions_and_keep_permissions_read_only():
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert {path.name for path in workflows} == {"ci.yml", "codeql.yml"}
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        assert "contents: read" in text
        for line in text.splitlines():
            if "uses:" not in line:
                continue
            reference = line.split("uses:", 1)[1].strip().split()[0]
            assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference), (
                f"Unpinned action in {path.name}: {reference}"
            )
    codeql = next(path for path in workflows if path.name == "codeql.yml")
    assert "upload: false" in codeql.read_text(encoding="utf-8")


def test_release_hygiene_metadata_is_present():
    patterns = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    required = {
        "*.pyc",
        ".env",
        ".idea/",
        ".vscode/",
        "data/",
        "LOCK*.txt",
    }
    assert required <= set(patterns)
    todo = (ROOT / "TODO.md").read_text(encoding="utf-8")
    assert "## STATUS" in todo
    assert "| Category | Status |" in todo


def test_mit_license_metadata_is_consistent():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]

    licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert licence.startswith("MIT License\n")
    assert "Copyright (c) 2026 Lukas Geiger" in licence
    assert "public package release has been approved" in (ROOT / "README.md").read_text(
        encoding="utf-8"
    )
    assert "öffentliche Paketfreigabe wurde nicht erteilt" in (
        ROOT / "README_de.md"
    ).read_text(encoding="utf-8")
