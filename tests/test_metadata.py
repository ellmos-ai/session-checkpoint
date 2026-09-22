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
    if (ROOT / "PRIVATE.txt").exists():
        assert manifest["visibility"] == "private"
    else:
        assert manifest["visibility"] == "public"


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
        assert "cancel-in-progress: true" in text
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
        "*conflicted copy*",
        "LOCK.*",
        "uv.lock",
    }
    assert required <= set(patterns)
    todo = ROOT / "TODO.md"
    if todo.exists():
        text = todo.read_text(encoding="utf-8")
        assert "## STATUS" in text
        assert "| Category | Status |" in text


def test_mit_license_metadata_is_consistent():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]

    licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert licence.startswith("MIT License\n")
    assert "Copyright (c) 2026 Lukas Geiger" in licence
    assert "MIT licence" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "MIT-Lizenz" in (ROOT / "README_de.md").read_text(encoding="utf-8")


def test_llms_txt_is_present_and_consistent():
    llms_path = ROOT / "llms.txt"
    assert llms_path.is_file(), "llms.txt must exist"
    text = llms_path.read_text(encoding="utf-8")
    assert "# session-checkpoint" in text
    assert "- Last-checked: 2026-09-18" in text
    assert "## System Overview" in text
    assert "## Key Invariants & Features" in text
    assert "## CLI Reference" in text
    assert "## Python API Reference" in text
    manifest = json.loads((ROOT / "ellmos-module.v2.json").read_text(encoding="utf-8"))
    assert f"- Version: {manifest['version']}" in text


def test_packaging_and_pep621_classifiers():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "classifiers" in project
    classifiers = set(project["classifiers"])
    assert "License :: OSI Approved :: MIT License" in classifiers
    assert "Operating System :: OS Independent" in classifiers
    assert "Programming Language :: Python :: 3" in classifiers
    assert "Programming Language :: Python :: 3.10" in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers
    assert "Programming Language :: Python :: 3.13" in classifiers
    urls = project.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Issues" in urls
    assert "Documentation" in urls
    assert "Changelog" in urls


def test_pytest_ini_options_guardrails():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ini = cfg.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert ini.get("minversion") == "7.0"
    norecursedirs = set(ini.get("norecursedirs", []))
    assert {".git", ".pytest_cache", "__pycache__"} <= norecursedirs


def test_version_consistency_across_manifests():
    import session_checkpoint

    pyproject_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    manifest_version = json.loads((ROOT / "ellmos-module.v2.json").read_text(encoding="utf-8"))[
        "version"
    ]
    pkg_version = session_checkpoint.__version__
    llms_text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    changelog_text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert pyproject_version == "0.1.1"
    assert manifest_version == "0.1.1"
    assert pkg_version == "0.1.1"
    assert f"- Version: {pyproject_version}" in llms_text
    assert f"## {pyproject_version} —" in changelog_text


def test_notice_attribution_and_statutory_disclaimer():
    notice = ROOT / "NOTICE"
    assert notice.is_file(), "NOTICE file must exist"
    text = notice.read_text(encoding="utf-8")
    assert "Lukas Geiger" in text
    assert "ellmos-ai" in text
    assert "open-bricks" in text
    assert "§ 521 BGB" in text
    assert "MIT License" in text


def test_third_party_licenses_sbom_invariants():
    sbom = ROOT / "THIRD_PARTY_LICENSES.md"
    assert sbom.is_file(), "THIRD_PARTY_LICENSES.md must exist"
    text = sbom.read_text(encoding="utf-8")
    assert "Level 1 Software Bill of Materials (SBOM)" in text
    assert "Zero-Mandatory-Runtime-Dependencies" in text
    for i in range(1, 11):
        if i == 1:
            code = "INV-LOCAL-01"
        elif i == 2:
            code = "INV-CANON-02"
        elif i == 3:
            code = "INV-FAILCLOSE-03"
        elif i == 4:
            code = "INV-BOUNDARY-04"
        elif i == 5:
            code = "INV-NAMESP-05"
        elif i == 6:
            code = "INV-LIMITS-06"
        elif i == 7:
            code = "INV-DRYRUN-07"
        elif i == 8:
            code = "INV-PERM-08"
        elif i == 9:
            code = "INV-REVERSIBLE-09"
        else:
            code = "INV-SLA-10"
        assert code in text, f"Missing invariant {code} in THIRD_PARTY_LICENSES.md"
    assert "RunAsInvoker" in text


def test_bilingual_navigation_parity_and_anchors():
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for i in range(1, 19):
        anchor = f'<a id="sec-{i:02d}">'
        assert anchor in en, f"Missing anchor {anchor} in README.md"
        assert anchor in de, f"Missing anchor {anchor} in README_de.md"


def test_personas_and_comparative_matrix_present():
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for p in ("[PERSONA-01]", "[PERSONA-02]", "[PERSONA-03]", "[PERSONA-04]"):
        assert p in en, f"Missing persona {p} in README.md"
        assert p in de, f"Missing persona {p} in README_de.md"

    assert "Comparative Matrix" in en
    assert "Vergleichsmatrix" in de


def test_security_sla_and_run_as_invoker():
    sec = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    assert "48 hours" in sec
    assert "RunAsInvoker" in sec
    assert "48 hours" in en or "48-hour" in en
    assert "48 Stunden" in de or "48-Stunden" in de


def test_mermaid_diagram_syntax_guardrails():
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for text, name in [(en, "README.md"), (de, "README_de.md")]:
        unquoted = re.search(r'^\s*[\w\-]+\[[^"\'\]\n]*\([^\)\]\n]+\)[^"\'\]\n]*\]', text, re.MULTILINE)
        assert not unquoted, f"Unquoted parenthesis in node label in {name}: {unquoted.group(0) if unquoted else ''}"
