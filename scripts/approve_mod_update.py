
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "index.json"

VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
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
    try:
        parsed = urlparse(value)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError

    except ValueError:
        raise ValueError(f"{name} must be a valid HTTPS URL.")

    return value


def validate_github_release_asset(value, extension, name):
    validate_url(value, name)

    parsed = urlparse(value)
    path = unquote(parsed.path).lower()

    if (
        parsed.hostname != "github.com"
        or "/releases/download/" not in path
        or not path.endswith(extension.lower())
    ):
        raise ValueError(
            f"{name} must point to a GitHub release "
            f"{extension.upper()} asset."
        )

    return value


def version_tuple(version):
    match = VERSION_PATTERN.fullmatch(version)

    if not match:
        raise ValueError(
            f"Invalid version: {version}. Use MAJOR.MINOR.PATCH."
        )

    return tuple(map(int, match.groups()))


def validate_sha256(value, name):
    if not SHA_PATTERN.fullmatch(value):
        raise ValueError(
            f"{name} must contain exactly 64 hexadecimal characters."
        )


def main():
    body = os.environ["ISSUE_BODY"]
    issue_url = os.environ["ISSUE_URL"]

    fields = parse_fields(body)

    mod_id = required(fields, "Mod ID").lower()
    developer = (
        required(fields, "Developer GitHub Username")
        .strip()
        .lstrip("@")
        .lower()
    )
    issue_author = os.environ.get("ISSUE_AUTHOR", "").strip().lower()

    if not developer or developer != issue_author:
        raise ValueError(
            "Developer username must match the GitHub issue author."
        )

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
    changelog = required(fields, "Changelog")

    if changelog == "_No response_":
        raise ValueError("A changelog is required.")

    if package_type not in {"ZIP", "GEODE", "EXE"}:
        raise ValueError("Unsupported package type.")

    validate_sha256(sha256, "SHA-256 checksum")

    old_version = version_tuple(submitted_current)
    new_version_tuple = version_tuple(new_version)

    if new_version_tuple <= old_version:
        raise ValueError(
            "New version must be greater than current version."
        )

    fusion_choice = required(
        fields,
        "Separate Fusion ZIP included?"
    ).lower()

    fusion_download_url = fields.get(
        "Updated Fusion ZIP Download URL", ""
    ).strip()

    fusion_sha256 = fields.get(
        "Fusion ZIP SHA-256 Checksum", ""
    ).strip().lower()

    if fusion_choice not in {"yes", "no"}:
        raise ValueError(
            "Separate Fusion ZIP included? must be Yes or No."
        )

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    mods = catalog.get("mods")

    if not isinstance(mods, list):
        raise ValueError("Catalog mods must be a JSON array.")

    matches = [
        mod for mod in mods
        if isinstance(mod, dict)
        and isinstance(mod.get("id"), str)
        and mod["id"].lower() == mod_id
    ]

    if len(matches) != 1:
        raise ValueError(
            "Mod ID must match exactly one catalog entry."
        )

    mod = matches[0]

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

    administrators = staff.get("roles", {}).get(
        "administrators", []
    )

    if not isinstance(administrators, list):
        raise ValueError("Staff administrator list is invalid.")

    administrators = [
        username.lower()
        for username in administrators
        if isinstance(username, str)
    ]

    if developer not in maintainers and developer not in administrators:
        raise ValueError(
            "Developer is not authorized to update this mod."
        )

    if mod.get("approved") is not True:
        raise ValueError("This mod is not approved.")

    if mod.get("version") != submitted_current:
        raise ValueError(
            "Catalog version changed since submission. "
            "The update must be submitted again."
        )

    runtime = mod.get("runtime")

    if runtime not in {"fusion", "geode"}:
        raise ValueError("Catalog entry has an unsupported runtime.")

    expected_package_type = {
        "fusion": "ZIP",
        "geode": "GEODE"
    }[runtime]

    if package_type != expected_package_type:
        raise ValueError(
            f"{runtime} mods must use {expected_package_type} packages."
        )

    compatibility = mod.get("compatibility", {})

    if not isinstance(compatibility, dict):
        raise ValueError("Catalog compatibility configuration is invalid.")

    fusion_compatibility = compatibility.get("fusion", {})

    if not isinstance(fusion_compatibility, dict):
        raise ValueError(
            "Catalog Fusion compatibility configuration is invalid."
        )

    currently_supports_fusion = (
        fusion_compatibility.get("supported") is True
    )

    existing_fusion_package = mod.get("fusionPackage")

    if existing_fusion_package is not None:
        if not isinstance(existing_fusion_package, dict):
            raise ValueError(
                "Existing Fusion package configuration is invalid."
            )

        if existing_fusion_package.get("packageType") != "ZIP":
            raise ValueError(
                "Existing Fusion package must use ZIP format."
            )

    fusion_package = None

    if runtime == "fusion":
        if fusion_choice != "no":
            raise ValueError(
                "Fusion-native mods must select No for a separate Fusion ZIP."
            )

        if fusion_download_url or fusion_sha256:
            raise ValueError(
                "Fusion-native mods cannot submit a separate Fusion ZIP."
            )

    elif runtime == "geode":
        if fusion_choice == "yes":
            if not fusion_download_url or not fusion_sha256:
                raise ValueError(
                    "Fusion ZIP URL and checksum are both required."
                )

            validate_github_release_asset(
                fusion_download_url,
                ".zip",
                "Fusion ZIP download URL"
            )

            validate_sha256(
                fusion_sha256,
                "Fusion ZIP SHA-256 checksum"
            )

            fusion_package = {
                "packageType": "ZIP",
                "downloadUrl": fusion_download_url,
                "sha256": fusion_sha256
            }

        else:
            if fusion_download_url or fusion_sha256:
                raise ValueError(
                    "Fusion ZIP URL and checksum must be empty "
                    "when the separate Fusion ZIP option is No."
                )

            if currently_supports_fusion or existing_fusion_package:
                raise ValueError(
                    "This mod already supports Fusion. An updated "
                    "Fusion ZIP is required to preserve that support."
                )

    previous_version = mod["version"]

    history = mod.setdefault("updateHistory", [])

    if not isinstance(history, list):
        raise ValueError("Mod updateHistory must be a JSON array.")

    if any(
        isinstance(entry, dict)
        and entry.get("version") == new_version
        for entry in history
    ):
        raise ValueError(
            "This version already exists in update history."
        )

    previous_entry = {
        "version": previous_version,
        "downloadUrl": mod.get("downloadUrl", ""),
        "releaseUrl": mod.get("releaseUrl", ""),
        "sha256": mod.get("sha256", ""),
        "packageType": mod.get("packageType", ""),
        "changelog": changelog,
        "approvedUpdateIssue": mod.get("lastUpdateIssue", "")
    }

    if existing_fusion_package is not None:
        previous_entry["fusionPackage"] = existing_fusion_package.copy()

    history.append(previous_entry)

    mod["latestChangelog"] = changelog
    mod["lastUpdateBy"] = developer
    mod["version"] = new_version
    mod["downloadUrl"] = download_url
    mod["releaseUrl"] = release_url
    mod["sha256"] = sha256
    mod["packageType"] = package_type
    mod["lastUpdateIssue"] = issue_url

    if fusion_package is not None:
        mod["fusionPackage"] = fusion_package

    CATALOG.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"Updated mod: {mod.get('name', mod_id)}")
    print(f"Version: {previous_version} -> {new_version}")
    print(f"Runtime: {runtime}")
    print(
        "Separate Fusion ZIP: "
        + ("updated" if fusion_package else "not included")
    )


if __name__ == "__main__":
    main()
