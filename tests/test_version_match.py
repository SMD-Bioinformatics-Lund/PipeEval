import re
from pathlib import Path


def test_version_matches_changelog():
    """Ensure version in main.py matches latest entry in CHANGELOG.md."""
    main_text = Path("main.py").read_text()
    match = re.search(r"__version_info__\s*=\s*\(([^)]*)\)", main_text)
    assert match, "__version_info__ not found in main.py"
    parts = [p.strip().strip('"').strip("'") for p in match.group(1).split(",")]
    code_version = ".".join(parts)

    changelog_lines = Path("CHANGELOG.md").read_text().splitlines()
    latest = next((line for line in changelog_lines if line.startswith("# ")), None)
    assert latest, "No version found in CHANGELOG.md"
    changelog_version = latest.lstrip("# ").strip()

    assert (
        code_version == changelog_version
    ), f"main.py version {code_version} does not match changelog version {changelog_version}"
