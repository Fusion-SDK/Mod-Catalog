
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "index.json"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")

SUPPORTED_RUNTIMES = {"fusion", "geode"}
SUPPORTED_PLATFORMS = {"windows", "macos", "linux", "android", "ios"}


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


def optional(fields, name):
    value = fields.get(name, "").strip()

    if value == "_No response_":
        return ""

    return value


def normalize_username(value):
    return value.strip().casefold().lstrip("@")


def validate_https_url(value, name, allowed_hosts=None):
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        raise ValueError(f"{name} must be a valid HTTPS URL.")

    if (
        parsed.scheme.casefold() != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"{name} must be a valid HTTPS URL.")

    if allowed_hosts:
        allowed = {host.casefold() for host in allowed_hosts}

        if hostname.casefold() not in allowed:
            raise ValueError(
                f"{name} must use one of these hosts: "
                + ", ".join(sorted(allowed))
            )

    return value


def validate_release_asset_url(value, name, extension):
    validate_https_url(value, name, {"github.com"})

    parsed = urlparse(value)
    path = unquote(parsed.path).casefold()

    if (
        parsed.hostname.casefold() != "github.com"
        or "/releases/download/" not in path
        or not path.endswith(extension.casefold())
    ):
        raise ValueError(
            f"{name} must point to a GitHub Release "
            f"{extension} asset."
        )


def parse_list(value):
    if not value or value == "_No response_":
        return []

    return [
        item.strip()
        for item in re.split(r"[,\n]", value)
        if item.strip()
    ]


def parse_version(value, name):
    match = VERSION_PATTERN.fullmatch(value)

    if not match:
        raise ValueError(
            f"{name} must use MAJOR.MINOR.PATCH format."
        )

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3))
    )


def validate_repository_url(value):
    parsed = urlparse(value)
    parts = parsed.path.strip("/").split("/")

    if (
        parsed.hostname.casefold() != "github.com"
        or len(parts) != 2
        or not all(parts)
        or parts[1].endswith(".git")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Source repository must point to a GitHub owner/repository."
        )


def validate_release_url(value):
    parsed = urlparse(value)

    if parsed.hostname.casefold() != "github.com":
        raise ValueError(
            "Upstream release URL must point to github.com."
        )


def validate_sha256(value, name):
    value = value.lower()

    if not SHA_PATTERN.fullmatch(value):
        raise ValueError(
            f"{name} must contain exactly 64 hexadecimal characters."
        )

    return value


def validate_catalog_structure(catalog):
    if not isinstance(catalog, dict):
        raise ValueError("Catalog root must be a JSON object.")

    if catalog.get("schemaVersion") != 2:
        raise ValueError("Catalog must use schema version 2.")

    supported_runtimes = catalog.get("supportedRuntimes")

    if (
        not isinstance(supported_runtimes, list)
        or not all(
            isinstance(runtime, str)
            for runtime in supported_runtimes
        )
    ):
        raise ValueError(
            "Catalog supportedRuntimes must be a list of strings."
        )

    mods = catalog.get("mods")

    if not isinstance(mods, list):
        raise ValueError("Catalog mods must be a JSON array.")

    for index, existing in enumerate(mods):
        if not isinstance(existing, dict):
            raise ValueError(
                f"Catalog mod at index {index} must be a JSON object."
            )

        existing_id = existing.get("id")

        if not isinstance(existing_id, str) or not existing_id:
            raise ValueError(
                f"Catalog mod at index {index} has an invalid ID."
            )


def main():
    body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    issue_url = os.environ["ISSUE_URL"]
    issue_author = normalize_username(
        os.environ["ISSUE_AUTHOR"]
    )

    if not issue_author:
        raise ValueError("GitHub issue author is missing.")

    fields = parse_fields(body)

    mod_id = required(fields, "Mod ID").lower()
    name = required(fields, "Mod Name")
    description = required(fields, "Mod Description")
    creator = required(fields, "Mod Creator")
    version = required(fields, "Mod Version")

    runtime = required(fields, "Mod Runtime").lower()
    package_type = required(fields, "Package Type").upper()

    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError("Runtime must be Fusion or Geode.")

    expected_package = {
        "fusion": "ZIP",
        "geode": "GEODE"
    }

    if package_type != expected_package[runtime]:
        raise ValueError(
            f"Runtime '{runtime}' requires package type "
            f"'{expected_package[runtime]}'."
        )

    download_url = validate_https_url(
        required(fields, "GitHub Release Download URL"),
        "Download URL",
        {"github.com"}
    )

    validate_release_asset_url(
        download_url,
        "Download URL",
        ".zip" if runtime == "fusion" else ".geode"
    )

    repository = validate_https_url(
        required(fields, "Source Repository"),
        "Source repository",
        {"github.com"}
    )
    validate_repository_url(repository)

    release_url = validate_https_url(
        required(fields, "Upstream Release URL"),
        "Upstream release URL",
        {"github.com"}
    )
    validate_release_url(release_url)

    icon = validate_https_url(
        required(fields, "Mod Icon URL"),
        "Mod icon URL"
    )

    sha256 = validate_sha256(
        required(fields, "Package SHA-256"),
        "Package SHA-256"
    )

    if not ID_PATTERN.fullmatch(mod_id):
        raise ValueError("Mod ID contains invalid characters.")

    parse_version(version, "Mod Version")

    platforms = [
        platform.lower()
        for platform in parse_list(
            required(fields, "Supported Platforms")
        )
    ]

    if not platforms:
        raise ValueError(
            "At least one supported platform is required."
        )

    if len(platforms) != len(set(platforms)):
        raise ValueError("Duplicate platforms are not allowed.")

    invalid_platforms = set(platforms) - SUPPORTED_PLATFORMS

    if invalid_platforms:
        raise ValueError(
            "Unsupported platforms: "
            + ", ".join(sorted(invalid_platforms))
        )

    dependencies = parse_list(optional(fields, "Dependencies"))
    conflicts = parse_list(optional(fields, "Conflicts"))

    for label, identifiers in (
        ("Dependencies", dependencies),
        ("Conflicts", conflicts)
    ):
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                f"Duplicate {label.lower()} are not allowed."
            )

        for identifier in identifiers:
            if not ID_PATTERN.fullmatch(identifier):
                raise ValueError(
                    f"Invalid {label.lower()} mod ID: {identifier}"
                )

            if identifier == mod_id:
                raise ValueError(
                    "A mod cannot depend on or conflict with itself."
                )

    if set(dependencies) & set(conflicts):
        raise ValueError(
            "A mod cannot both depend on and conflict with "
            "the same mod."
        )

    geode_minimum = None
    geode_maximum = None

    if runtime == "geode":
        geode_minimum = required(
            fields,
            "Minimum Geode Version"
        )
        minimum_tuple = parse_version(
            geode_minimum,
            "Minimum Geode Version"
        )

        geode_maximum = (
            optional(fields, "Maximum Geode Version") or None
        )

        if geode_maximum:
            maximum_tuple = parse_version(
                geode_maximum,
                "Maximum Geode Version"
            )

            if maximum_tuple < minimum_tuple:
                raise ValueError(
                    "Maximum Geode Version cannot be lower than "
                    "Minimum Geode Version."
                )

    fusion_supported_answer = required(
        fields,
        "Does this mod also support Fusion?"
    ).strip().casefold()

    if fusion_supported_answer not in {"yes", "no"}:
        raise ValueError(
            "Fusion compatibility must be answered Yes or No."
        )

    fusion_supported = fusion_supported_answer == "yes"
    fusion_package = None

    fusion_download = optional(
        fields,
        "Fusion Package Download URL"
    )
    fusion_sha = optional(
        fields,
        "Fusion Package SHA-256"
    )

    if runtime == "fusion":
        if fusion_supported:
            raise ValueError(
                "Fusion-primary mods must select No for additional "
                "Fusion compatibility."
            )

        if fusion_download or fusion_sha:
            raise ValueError(
                "Fusion-primary mods cannot submit an additional "
                "Fusion package."
            )

    elif runtime == "geode":
        if fusion_supported:
            if not fusion_download:
                raise ValueError(
                    "Fusion Package Download URL is required when "
                    "Fusion compatibility is Yes."
                )

            if not fusion_sha:
                raise ValueError(
                    "Fusion Package SHA-256 is required when "
                    "Fusion compatibility is Yes."
                )

            fusion_download = validate_https_url(
                fusion_download,
                "Fusion Package Download URL",
                {"github.com"}
            )

            validate_release_asset_url(
                fusion_download,
                "Fusion Package Download URL",
                ".zip"
            )

            fusion_sha = validate_sha256(
                fusion_sha,
                "Fusion Package SHA-256"
            )

            fusion_package = {
                "packageType": "ZIP",
                "downloadUrl": fusion_download,
                "sha256": fusion_sha
            }

        elif fusion_download or fusion_sha:
            raise ValueError(
                "Fusion package details must be blank when Fusion "
                "compatibility is No."
            )

    try:
        catalog = json.loads(
            CATALOG.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Catalog contains invalid JSON: {error}"
        ) from error

    validate_catalog_structure(catalog)

    if runtime not in catalog["supportedRuntimes"]:
        raise ValueError(
            f"Catalog does not support runtime: {runtime}"
        )

    for existing in catalog["mods"]:
        if existing["id"].casefold() == mod_id:
            raise ValueError(f"Mod ID already exists: {mod_id}")

    mod = {
        "id": mod_id,
        "name": name,
        "description": description,
        "creator": creator,
        "maintainers": [issue_author],
        "version": version,
        "packageType": package_type,
        "runtime": runtime,
        "compatibility": {
            "game": "Geometry Dash",
            "platforms": platforms,
            "geode": {
                "required": runtime == "geode",
                "minimumVersion": geode_minimum,
                "maximumVersion": geode_maximum
            },
            "fusion": {
                "supported": (
                    runtime == "fusion" or fusion_supported
                )
            }
        },
        "dependencies": dependencies,
        "conflicts": conflicts,
        "icon": icon,
        "repository": repository,
        "releaseUrl": release_url,
        "downloadUrl": download_url,
        "sha256": sha256,
        "approved": True,
        "registrationIssue": issue_url,
        "latestChangelog": "",
        "updateHistory": []
    }

    if fusion_package is not None:
        mod["fusionPackage"] = fusion_package

    catalog["mods"].append(mod)

    temporary_catalog = CATALOG.with_suffix(".json.tmp")

    temporary_catalog.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    temporary_catalog.replace(CATALOG)

    print(f"Registered mod: {name}")
    print(f"Mod ID: {mod_id}")
    print(f"Runtime: {runtime}")
    print(f"Package type: {package_type}")
    print(
        "Fusion supported: "
        f"{mod['compatibility']['fusion']['supported']}"
    )

    if fusion_package:
        print("Separate Fusion ZIP package: registered")

    print(f"Maintainer: {issue_author}")
    print(f"Registration issue: #{issue_number}")


if __name__ == "__main__":
    main()
