
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

CATALOG = Path("catalog/index.json")
STAFF_CONFIG = Path("config/staff.json")

VERSION_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"


def fail(message):
    print(f"VALIDATION_FAILED: {message}")
    sys.exit(1)


def normalize_username(username):
    return username.strip().casefold().lstrip("@") if isinstance(username, str) else ""


def valid_https(url):
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


def valid_github_release_asset(url, extension):
    if not valid_https(url):
        return False

    try:
        parsed = urlparse(url)
        path = unquote(parsed.path).lower()

        return (
            parsed.hostname == "github.com"
            and "/releases/download/" in path
            and path.endswith(extension.lower())
        )
    except ValueError:
        return False


def valid_sha256(value):
    return bool(re.fullmatch(SHA256_PATTERN, value))


def main():
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        staff = json.loads(STAFF_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("Catalog or staff configuration is missing or invalid.")

    if not isinstance(catalog, dict):
        fail("Catalog root must be a JSON object.")

    if not isinstance(staff, dict):
        fail("Staff configuration root must be a JSON object.")

    roles = staff.get("roles")

    if not isinstance(roles, dict):
        fail("Staff role configuration is invalid.")

    mod_id = os.getenv("MOD_ID", "").strip().lower()
    developer = normalize_username(os.getenv("DEVELOPER", ""))
    issue_author = normalize_username(os.getenv("ISSUE_AUTHOR", ""))

    current_version = os.getenv("CURRENT_VERSION", "").strip()
    new_version = os.getenv("NEW_VERSION", "").strip()
    download_url = os.getenv("DOWNLOAD_URL", "").strip()
    release_url = os.getenv("RELEASE_URL", "").strip()
    package_type = os.getenv("PACKAGE_TYPE", "").strip().upper()
    sha256 = os.getenv("SHA256", "").strip().lower()

    fusion_package_included = (
        os.getenv("FUSION_PACKAGE_INCLUDED", "").strip().lower()
    )
    fusion_download_url = os.getenv("FUSION_DOWNLOAD_URL", "").strip()
    fusion_sha256 = os.getenv("FUSION_SHA256", "").strip().lower()
    changelog = os.getenv("CHANGELOG", "").strip()

    if not mod_id:
        fail("Mod ID is required.")

    if not developer or developer != issue_author:
        fail("Developer username must match the GitHub issue author.")

    mods = catalog.get("mods", [])

    if not isinstance(mods, list):
        fail("Catalog mods must be a list.")

    matches = [
        item for item in mods
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item["id"].lower() == mod_id
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
        normalize_username(name)
        for name in maintainers
        if isinstance(name, str) and name.strip()
    ]

    administrators = roles.get("administrators", [])

    if not isinstance(administrators, list):
        fail("Staff administrator configuration is invalid.")

    administrators = [
        normalize_username(name)
        for name in administrators
        if isinstance(name, str) and name.strip()
    ]

    if developer not in maintainers and developer not in administrators:
        fail("This GitHub account is not authorized to update this mod.")

    if mod.get("version") != current_version:
        fail("Submitted current version does not match the catalog.")

    if not re.fullmatch(VERSION_PATTERN, current_version):
        fail("Current version must use MAJOR.MINOR.PATCH format.")

    if not re.fullmatch(VERSION_PATTERN, new_version):
        fail("New version must use MAJOR.MINOR.PATCH format.")

    if tuple(map(int, new_version.split("."))) <= tuple(
        map(int, current_version.split("."))
    ):
        fail("New version must be greater than the current version.")

    runtime = mod.get("runtime")

    if runtime not in {"fusion", "geode"}:
        fail("Catalog entry has an unsupported runtime.")

    expected_package_type = {
        "fusion": "ZIP",
        "geode": "GEODE"
    }[runtime]

    if package_type != expected_package_type:
        fail(
            f"{runtime} mods must use {expected_package_type} packages."
        )

    if runtime == "fusion":
        if not valid_github_release_asset(download_url, ".zip"):
            fail(
                "Fusion download URL must point to a GitHub release ZIP asset."
            )

    elif runtime == "geode":
        if not valid_github_release_asset(download_url, ".geode"):
            fail(
                "Geode download URL must point to a GitHub release GEODE asset."
            )

    if not valid_https(release_url):
        fail("Release URL must use HTTPS.")

    existing_package_type = str(mod.get("packageType", "")).upper()

    if package_type != existing_package_type:
        fail("Package type cannot be changed through a version update.")

    if not valid_sha256(sha256):
        fail("SHA-256 must contain exactly 64 hexadecimal characters.")

    if not changelog or changelog == "_No response_":
        fail("A changelog is required.")

    compatibility = mod.get("compatibility", {})

    if not isinstance(compatibility, dict):
        fail("Catalog compatibility configuration is invalid.")

    fusion_compatibility = compatibility.get("fusion", {})

    if not isinstance(fusion_compatibility, dict):
        fail("Catalog Fusion compatibility configuration is invalid.")

    currently_supports_fusion = (
        fusion_compatibility.get("supported") is True
    )

    existing_fusion_package = mod.get("fusionPackage")

    if existing_fusion_package is not None:
        if not isinstance(existing_fusion_package, dict):
            fail("Existing Fusion package configuration is invalid.")

        if existing_fusion_package.get("packageType") != "ZIP":
            fail("Existing Fusion package must use ZIP format.")

    if fusion_package_included not in {"yes", "no"}:
        fail("Select Yes or No for the separate Fusion ZIP option.")

    fusion_package = None

    if runtime == "fusion":
        if fusion_package_included == "yes":
            fail(
                "Fusion-native mods must select No for a separate Fusion ZIP."
            )

        if fusion_download_url or fusion_sha256:
            fail(
                "Fusion-native mods cannot submit a separate Fusion ZIP."
            )

    elif runtime == "geode":
        if fusion_package_included == "yes":
            if not fusion_download_url:
                fail("A Fusion ZIP download URL is required.")

            if not fusion_sha256:
                fail("A Fusion ZIP SHA-256 checksum is required.")

            if not valid_github_release_asset(
                fusion_download_url,
                ".zip"
            ):
                fail(
                    "Fusion ZIP URL must point to a GitHub release ZIP asset."
                )

            if not valid_sha256(fusion_sha256):
                fail(
                    "Fusion ZIP SHA-256 must contain exactly "
                    "64 hexadecimal characters."
                )

            fusion_package = {
                "packageType": "ZIP",
                "downloadUrl": fusion_download_url,
                "sha256": fusion_sha256
            }

        else:
            if fusion_download_url or fusion_sha256:
                fail(
                    "Fusion ZIP URL and checksum must be empty when "
                    "the separate Fusion ZIP option is No."
                )

            if currently_supports_fusion or existing_fusion_package:
                fail(
                    "This mod already supports Fusion. Provide an updated "
                    "Fusion ZIP or handle removal through a separate "
                    "catalog review process."
                )

    print("VALIDATION_PASSED")
    print(f"Mod: {mod.get('name', mod_id)}")
    print(f"Developer: {developer}")
    print(f"Version: {current_version} -> {new_version}")
    print(f"Runtime: {runtime}")
    print(
        "Separate Fusion ZIP: "
        + ("included" if fusion_package else "not included")
    )


if __name__ == "__main__":
    main()
