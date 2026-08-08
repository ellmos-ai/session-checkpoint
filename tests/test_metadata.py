from __future__ import annotations

import json
from pathlib import Path


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
