
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "index.json"

VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$"
)
SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def parse_fields(body):
    fields = {}
    sections = re.split(r"(?m)^###\s+", body)

    for section in sections[1:]:
        lines = section.splitlines()
        if lines:
            fields[lines[0].strip()] = "\n".join(lines[1:]).strip()

    return fields


def required(fields, name):
    value = fields.get(name, "").strip()

    if not value or value == "_No response_":
        raise ValueError(f"Missing required field: {name}")

    return value


def validate_url(value, name):
    parsed = urlparse(value)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{name} must be a valid HTTPS URL.")

    return value


def version_tuple(version):
    match = VERSION_PATTERN.fullmatch(version)

    if not match:
        raise ValueError(
            f"Invalid version: {version}. Use MAJOR.MINOR.PATCH."
        )

    return tuple(map(int, match.groups()))


def main():
    body = os.environ["ISSUE_BODY"]
    issue_url = os.environ["ISSUE_URL"]

    fields = parse_fields(body)

    mod_id = required(fields, "Mod ID").lower()
    submitted_current = required(fields, "Current Catalog Version")
    new_version = required(fields, "Proposed New Version")

    download_url = validate_url(
        required(fields, "Updated Package Download URL"),
        "Download URL"
    )

    release_url = validate_url(
        required(fields, "Upstream Release URL"),
        "Release URL"
    )

    package_type = required(fields, "Package Type").upper()
    sha256 = required(fields, "SHA-256 Checksum").lower()

    if package_type not in {"ZIP", "GEODE", "EXE"}:
        raise ValueError("Unsupported package type.")

    if not SHA_PATTERN.fullmatch(sha256):
        raise ValueError("Invalid SHA-256 checksum.")

    old_version = version_tuple(submitted_current)
    new_version_tuple = version_tuple(new_version)

    if new_version_tuple <= old_version:
        raise ValueError("New version must be greater than current version.")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    mods = catalog.get("mods")

    if not isinstance(mods, list):
        raise ValueError("Catalog mods must be a JSON array.")

    matches = [
        mod for mod in mods
        if mod.get("id", "").lower() == mod_id
    ]

    if len(matches) != 1:
        raise ValueError("Mod ID must match exactly one catalog entry.")

    mod = matches[0]

developer = required(fields, "Developer GitHub Username").strip().lstrip("@").lower()
issue_author = os.environ.get("ISSUE_AUTHOR", "").strip().lower()

if not developer or developer != issue_author:
    raise ValueError(
        "Developer username must match the GitHub issue author."
    )

maintainers = mod.get("maintainers", [])

if not isinstance(maintainers, list):
    raise ValueError("Mod maintainer list must be a JSON array.")

maintainers = [
    username.lower()
    for username in maintainers
    if isinstance(username, str)
]

staff_path = ROOT / "config" / "staff.json"
staff = json.loads(staff_path.read_text(encoding="utf-8"))
administrators = staff.get("roles", {}).get("administrators", [])

if not isinstance(administrators, list):
    raise ValueError("Staff administrator list is invalid.")

administrators = [
    username.lower()
    for username in administrators
    if isinstance(username, str)
]

if developer not in maintainers and developer not in administrators:
    raise ValueError("Developer is not authorized to update this mod.")

if mod.get("approved") is not True:
        raise ValueError("This mod is not approved.")

    if mod.get("version") != submitted_current:
        raise ValueError(
            "Catalog version changed since submission. "
            "The update must be submitted again."
        )

    previous_version = mod["version"]

    history = mod.setdefault("updateHistory", [])

    if not isinstance(history, list):
        raise ValueError("Mod updateHistory must be a JSON array.")

    if any(
        isinstance(entry, dict) and entry.get("version") == new_version
        for entry in history
    ):
        raise ValueError("This version already exists in update history.")

    history.append({
        "version": previous_version,
        "downloadUrl": mod.get("downloadUrl", ""),
        "sha256": mod.get("sha256", ""),
        "approvedUpdateIssue": issue_url
    })

    mod["latestChangelog"] = required(fields, "Changelog")
    mod["lastUpdateBy"] = developer
    mod["version"] = new_version
    mod["downloadUrl"] = download_url
    mod["releaseUrl"] = release_url
    mod["sha256"] = sha256
    mod["packageType"] = package_type
    mod["lastUpdateIssue"] = issue_url

    CATALOG.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"Updated mod: {mod.get('name', mod_id)}")
    print(f"Version: {previous_version} -> {new_version}")


if __name__ == "__main__":
    main()
