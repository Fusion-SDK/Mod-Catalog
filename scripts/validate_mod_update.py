
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

CATALOG = Path("catalog/index.json")
STAFF_CONFIG = Path("config/staff.json")


def fail(message):
    print(f"VALIDATION_FAILED: {message}")
    sys.exit(1)


def valid_https(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def main():
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        staff = json.loads(STAFF_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("Catalog or staff configuration is missing or invalid.")

    mod_id = os.getenv("MOD_ID", "").strip().lower()
    developer = os.getenv("DEVELOPER", "").strip().lstrip("@").lower()
    issue_author = os.getenv("ISSUE_AUTHOR", "").strip().lower()
    current_version = os.getenv("CURRENT_VERSION", "").strip()
    new_version = os.getenv("NEW_VERSION", "").strip()
    download_url = os.getenv("DOWNLOAD_URL", "").strip()
    release_url = os.getenv("RELEASE_URL", "").strip()
    package_type = os.getenv("PACKAGE_TYPE", "").strip().upper()
    sha256 = os.getenv("SHA256", "").strip().lower()
    changelog = os.getenv("CHANGELOG", "").strip()

    if not developer or developer != issue_author:
        fail("Developer username must match the GitHub issue author.")

    mods = catalog.get("mods", [])

    if not isinstance(mods, list):
        fail("Catalog mods must be a list.")

    matches = [
        item for item in mods
        if isinstance(item, dict)
        and item.get("id", "").lower() == mod_id
    ]

    if len(matches) != 1:
        fail("Mod ID must match exactly one catalog entry.")

    mod = matches[0]

    if mod.get("approved") is not True:
        fail("This mod is not approved for updates.")

    maintainers = mod.get("maintainers", [])

    if not isinstance(maintainers, list):
        fail("The mod maintainer list is invalid.")

    maintainers = [
        name.lower() for name in maintainers
        if isinstance(name, str)
    ]

    roles = staff.get("roles", {})
    administrators = roles.get("administrators", [])

    if not isinstance(administrators, list):
        fail("Staff administrator configuration is invalid.")

    administrators = [
        name.lower() for name in administrators
        if isinstance(name, str)
    ]

    if developer not in maintainers and developer not in administrators:
        fail("This GitHub account is not authorized to update this mod.")

    if mod.get("version") != current_version:
        fail("Submitted current version does not match the catalog.")

    version_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"

    if not re.fullmatch(version_pattern, current_version):
        fail("Current version must use MAJOR.MINOR.PATCH format.")

    if not re.fullmatch(version_pattern, new_version):
        fail("New version must use MAJOR.MINOR.PATCH format.")

    if tuple(map(int, new_version.split("."))) <= tuple(
        map(int, current_version.split("."))
    ):
        fail("New version must be greater than the current version.")

    if not valid_https(download_url):
        fail("Download URL must use HTTPS.")

    if not valid_https(release_url):
        fail("Release URL must use HTTPS.")

    if package_type not in {"ZIP", "GEODE", "EXE"}:
        fail("Unsupported package type.")

    if not re.fullmatch(r"[a-f0-9]{64}", sha256):
        fail("SHA-256 must contain exactly 64 hexadecimal characters.")

    if not changelog or changelog == "_No response_":
        fail("A changelog is required.")

    print("VALIDATION_PASSED")
    print(f"Mod: {mod.get('name', mod_id)}")
    print(f"Developer: {developer}")
    print(f"Version: {current_version} -> {new_version}")


if __name__ == "__main__":
    main()
