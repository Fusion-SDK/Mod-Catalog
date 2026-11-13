
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog" / "index.json"

SUPPORTED_RUNTIMES = {"fusion", "geode"}
SUPPORTED_PLATFORMS = {
    "windows",
    "macos",
    "linux",
    "android",
    "ios",
}

PACKAGE_TYPES = {
    "fusion": "ZIP",
    "geode": "GEODE",
}

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)

SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


class CatalogValidationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CatalogValidationError(message)


def validate_version(value, field_name):
    require(
        isinstance(value, str) and VERSION_PATTERN.fullmatch(value),
        f"{field_name} must use MAJOR.MINOR.PATCH version formatting."
    )


def validate_https_url(value, field_name):
    require(
        isinstance(value, str) and value.strip(),
        f"{field_name} is required."
    )

    parsed = urlparse(value)

    require(
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and not parsed.username
        and not parsed.password,
        f"{field_name} must be a valid HTTPS URL."
    )


def validate_id_list(values, field_name, mod_id):
    require(
        isinstance(values, list),
        f"{field_name} for '{mod_id}' must be a list."
    )

    seen = set()

    for value in values:
        require(
            isinstance(value, str) and ID_PATTERN.fullmatch(value),
            f"Invalid ID in {field_name} for '{mod_id}': {value!r}"
        )

        require(
            value not in seen,
            f"Duplicate ID '{value}' in {field_name} for '{mod_id}'."
        )

        require(
            value != mod_id,
            f"Mod '{mod_id}' cannot reference itself in {field_name}."
        )

        seen.add(value)

    return set(values)


def validate_mod(mod, known_ids):
    require(isinstance(mod, dict), "Every mod entry must be an object.")

    required_fields = [
        "id",
        "name",
        "description",
        "creator",
        "maintainers",
        "version",
        "packageType",
        "runtime",
        "compatibility",
        "dependencies",
        "conflicts",
        "icon",
        "repository",
        "releaseUrl",
        "downloadUrl",
        "sha256",
        "approved",
        "latestChangelog",
        "updateHistory",
    ]

    for field in required_fields:
        require(field in mod, f"Mod is missing required field '{field}'.")

    mod_id = mod["id"]

    require(
        isinstance(mod_id, str) and ID_PATTERN.fullmatch(mod_id),
        f"Invalid mod ID: {mod_id!r}"
    )

    require(
        isinstance(mod["name"], str) and mod["name"].strip(),
        f"Mod '{mod_id}' has an invalid name."
    )

    require(
        isinstance(mod["description"], str) and mod["description"].strip(),
        f"Mod '{mod_id}' has an invalid description."
    )

    require(
        isinstance(mod["creator"], str) and mod["creator"].strip(),
        f"Mod '{mod_id}' has an invalid creator."
    )

    require(
        isinstance(mod["maintainers"], list)
        and all(
            isinstance(item, str) and item.strip()
            for item in mod["maintainers"]
        ),
        f"Mod '{mod_id}' must have a valid maintainers list."
    )

    validate_version(mod["version"], f"Version for '{mod_id}'")

    runtime = mod["runtime"]
    package_type = mod["packageType"]

    require(
        runtime in SUPPORTED_RUNTIMES,
        f"Mod '{mod_id}' has unsupported runtime '{runtime}'."
    )

    require(
        package_type == PACKAGE_TYPES[runtime],
        f"Mod '{mod_id}' has an incompatible package type for runtime '{runtime}'."
    )

    compatibility = mod["compatibility"]

    require(
        isinstance(compatibility, dict),
        f"Compatibility for '{mod_id}' must be an object."
    )

    require(
        compatibility.get("game") == "Geometry Dash",
        f"Mod '{mod_id}' must target Geometry Dash."
    )

    platforms = compatibility.get("platforms")

    require(
        isinstance(platforms, list) and len(platforms) > 0,
        f"Mod '{mod_id}' must specify at least one platform."
    )

    require(
        all(
            isinstance(platform, str)
            and platform in SUPPORTED_PLATFORMS
            for platform in platforms
        ),
        f"Mod '{mod_id}' contains an unsupported platform."
    )

    require(
        len(platforms) == len(set(platforms)),
        f"Mod '{mod_id}' contains duplicate platforms."
    )

    geode = compatibility.get("geode")
    fusion = compatibility.get("fusion")

    require(
        isinstance(geode, dict) and isinstance(fusion, dict),
        f"Mod '{mod_id}' must define both geode and fusion compatibility."
    )

    require(
        isinstance(geode.get("required"), bool),
        f"Mod '{mod_id}' must define geode.required as a boolean."
    )

    require(
        isinstance(fusion.get("supported"), bool),
        f"Mod '{mod_id}' must define fusion.supported as a boolean."
    )

    if runtime == "geode":
        require(
            geode["required"] is True,
            f"Geode mod '{mod_id}' must require Geode."
        )

        require(
            fusion["supported"] is False,
            f"Geode mod '{mod_id}' cannot claim native Fusion support."
        )

        minimum = geode.get("minimumVersion")
        maximum = geode.get("maximumVersion")

        validate_version(
            minimum,
            f"Minimum Geode version for '{mod_id}'"
        )

        if maximum is not None:
            validate_version(
                maximum,
                f"Maximum Geode version for '{mod_id}'"
            )

            min_core = tuple(
                int(part) for part in minimum.split("-", 1)[0].split("+", 1)[0].split(".")
            )
            max_core = tuple(
                int(part) for part in maximum.split("-", 1)[0].split("+", 1)[0].split(".")
            )

            require(
                min_core <= max_core,
                f"Mod '{mod_id}' has a maximum Geode version below its minimum."
            )

    else:
        require(
            geode["required"] is False,
            f"Fusion mod '{mod_id}' cannot require Geode."
        )

        require(
            fusion["supported"] is True,
            f"Fusion mod '{mod_id}' must declare Fusion support."
        )

    dependencies = validate_id_list(
        mod["dependencies"],
        "dependencies",
        mod_id
    )

    conflicts = validate_id_list(
        mod["conflicts"],
        "conflicts",
        mod_id
    )

    require(
        not dependencies.intersection(conflicts),
        f"Mod '{mod_id}' cannot both depend on and conflict with the same mod."
    )

    for dependency in dependencies:
        require(
            dependency in known_ids,
            f"Mod '{mod_id}' references unknown dependency '{dependency}'."
        )

    for conflict in conflicts:
        require(
            conflict in known_ids,
            f"Mod '{mod_id}' references unknown conflict '{conflict}'."
        )

    validate_https_url(mod["icon"], f"Icon URL for '{mod_id}'")
    validate_https_url(mod["repository"], f"Repository URL for '{mod_id}'")
    validate_https_url(mod["releaseUrl"], f"Release URL for '{mod_id}'")
    validate_https_url(mod["downloadUrl"], f"Download URL for '{mod_id}'")

    parsed_repository = urlparse(mod["repository"])

    require(
        parsed_repository.hostname == "github.com"
        and len(parsed_repository.path.strip("/").split("/")) == 2,
        f"Repository URL for '{mod_id}' must point to a GitHub owner/repository."
    )

    require(
        parsed_repository.path.strip("/").endswith(".git") is False,
        f"Repository URL for '{mod_id}' must not end in .git."
    )

    require(
        isinstance(mod["sha256"], str)
        and SHA256_PATTERN.fullmatch(mod["sha256"]),
        f"Mod '{mod_id}' must have a valid SHA-256 checksum."
    )

    require(
        isinstance(mod["approved"], bool),
        f"Mod '{mod_id}' must have a boolean approved field."
    )

    require(
        isinstance(mod["latestChangelog"], str),
        f"Mod '{mod_id}' has an invalid changelog."
    )

    require(
        isinstance(mod["updateHistory"], list),
        f"Mod '{mod_id}' must have an update history list."
    )


def validate_catalog():
    require(CATALOG_PATH.is_file(), f"Catalog not found: {CATALOG_PATH}")

    try:
        with CATALOG_PATH.open("r", encoding="utf-8") as file:
            catalog = json.load(file)
    except json.JSONDecodeError as error:
        raise CatalogValidationError(
            f"Catalog JSON is invalid: {error}"
        )

    require(isinstance(catalog, dict), "Catalog root must be an object.")

    require(
        catalog.get("schemaVersion") == 2,
        "Catalog schemaVersion must be 2."
    )

    require(
        isinstance(catalog.get("catalogName"), str)
        and catalog["catalogName"].strip(),
        "Catalog must have a valid catalogName."
    )

    require(
        isinstance(catalog.get("catalogDescription"), str),
        "Catalog must have a valid catalogDescription."
    )

    require(
        catalog.get("supportedRuntimes") == ["fusion", "geode"],
        "Catalog supportedRuntimes must contain fusion and geode."
    )

    mods = catalog.get("mods")

    require(isinstance(mods, list), "Catalog mods must be a list.")

    mod_ids = []

    for mod in mods:
        require(isinstance(mod, dict), "Every mod entry must be an object.")
        mod_ids.append(mod.get("id"))

    require(
        all(isinstance(mod_id, str) for mod_id in mod_ids),
        "Every mod must have a string ID."
    )

    require(
        len(mod_ids) == len(set(mod_ids)),
        "Catalog contains duplicate mod IDs."
    )

    known_ids = set(mod_ids)

    for mod in mods:
        validate_mod(mod, known_ids)

    print(
        f"Catalog validation passed: {len(mods)} mod(s) checked."
    )


def main():
    try:
        validate_catalog()
    except CatalogValidationError as error:
        print(f"CATALOG VALIDATION FAILED: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
