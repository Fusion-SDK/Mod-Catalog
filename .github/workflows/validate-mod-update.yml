
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

CATALOG = Path("catalog/index.json")

def fail(message):
    print(f"VALIDATION_FAILED: {message}")
    sys.exit(1)

def valid_https(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)

def main():
    if not CATALOG.exists():
        fail("Catalog file is missing.")

    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        fail("Catalog JSON is invalid.")

    mod_id = os.getenv("MOD_ID", "").strip()
    current_version = os.getenv("CURRENT_VERSION", "").strip()
    new_version = os.getenv("NEW_VERSION", "").strip()
    download_url = os.getenv("DOWNLOAD_URL", "").strip()
    release_url = os.getenv("RELEASE_URL", "").strip()
    package_type = os.getenv("PACKAGE_TYPE", "").strip().upper()
    sha256 = os.getenv("SHA256", "").strip().lower()

    mods = catalog.get("mods", [])

    mod = next(
        (item for item in mods if item.get("id") == mod_id),
        None
    )

    if not mod:
        fail("Mod ID does not exist in the catalog.")

    if mod.get("version") != current_version:
        fail("Submitted current version does not match the catalog.")

    version_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"

    if not re.fullmatch(version_pattern, current_version):
        fail("Current version must use MAJOR.MINOR.PATCH format.")

    if not re.fullmatch(version_pattern, new_version):
        fail("New version must use MAJOR.MINOR.PATCH format.")

    old = tuple(map(int, current_version.split(".")))
    new = tuple(map(int, new_version.split(".")))

    if new <= old:
        fail("New version must be greater than the current version.")

    if not valid_https(download_url):
        fail("Download URL must use HTTPS.")

    if not valid_https(release_url):
        fail("Release URL must use HTTPS.")

    if package_type not in {"ZIP", "GEODE", "EXE"}:
        fail("Unsupported package type.")

    if not re.fullmatch(r"[a-f0-9]{64}", sha256):
        fail("SHA-256 must contain exactly 64 hexadecimal characters.")

    print("VALIDATION_PASSED")
    print(f"Mod: {mod.get('name', mod_id)}")
    print(f"Version: {current_version} -> {new_version}")

if __name__ == "__main__":
    main()
