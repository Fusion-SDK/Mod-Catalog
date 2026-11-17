
import hashlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import PurePosixPath

MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024
MAX_ARCHIVE_FILES = 10000
MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
DOWNLOAD_TIMEOUT = 30

ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}

SUPPORTED_RUNTIMES = {"fusion", "geode"}
SUPPORTED_PLATFORMS = {
    "windows", "macos", "linux", "android", "ios"
}

PACKAGE_EXTENSIONS = {
    "ZIP": ".zip",
    "GEODE": ".geode",
}

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


class SubmissionError(Exception):
    pass


def parse_fields(body):
    fields = {}
    sections = re.split(r"(?m)^###\s+", body)

    for section in sections[1:]:
        lines = section.splitlines()

        if lines:
            fields[lines[0].strip()] = "\n".join(lines[1:]).strip()

    return fields


def get_field(fields, *names):
    for name in names:
        value = fields.get(name, "").strip()

        if value and value != "_No response_":
            return value

    return ""


def parse_list(value):
    if not value or value == "_No response_":
        return []

    return [
        item.strip()
        for item in re.split(r"[,\n]", value)
        if item.strip()
    ]


def valid_https_url(value):
    if not value or any(char.isspace() for char in value):
        return False

    try:
        parsed = urllib.parse.urlparse(value)

        return (
            parsed.scheme.lower() == "https"
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


def version_tuple(version):
    match = VERSION_PATTERN.fullmatch(version)

    if not match:
        raise SubmissionError(f"Invalid version: {version}")

    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def validate_version(value, field_name):
    try:
        version_tuple(value)
    except SubmissionError:
        raise SubmissionError(
            f"{field_name} must use a valid semantic version, such as 1.0.0."
        )


def validate_github_repository_url(value, field_name, allow_subpaths=False):
    if not valid_https_url(value):
        raise SubmissionError(f"{field_name} must be a valid HTTPS URL.")

    parsed = urllib.parse.urlparse(value)

    if parsed.hostname.lower() != "github.com":
        raise SubmissionError(f"{field_name} must use github.com.")

    if parsed.query or parsed.fragment:
        raise SubmissionError(
            f"{field_name} must not contain a query string or fragment."
        )

    parts = [part for part in parsed.path.split("/") if part]

    if len(parts) < 2 or (not allow_subpaths and len(parts) != 2):
        raise SubmissionError(
            f"{field_name} must point to a GitHub owner/repository."
        )

    if any(part in {".", ".."} for part in parts):
        raise SubmissionError(f"{field_name} contains an invalid path.")

    if parts[1].lower().endswith(".git"):
        raise SubmissionError(
            f"{field_name} must not use a .git repository suffix."
        )


def validate_release_asset_url(value, expected_extension, field_name):
    if not valid_https_url(value):
        raise SubmissionError(f"{field_name} must be a valid HTTPS URL.")

    parsed = urllib.parse.urlparse(value)

    if parsed.hostname.lower() != "github.com":
        raise SubmissionError(
            f"{field_name} must be a direct GitHub Release asset URL."
        )

    if parsed.query or parsed.fragment:
        raise SubmissionError(
            f"{field_name} must not contain a query string or fragment."
        )

    if "/releases/download/" not in parsed.path:
        raise SubmissionError(
            f"{field_name} must point directly to a GitHub Release asset."
        )

    if not parsed.path.lower().endswith(expected_extension):
        raise SubmissionError(
            f"{field_name} must point to a {expected_extension} file."
        )


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, request, response, code, message, headers, new_url
    ):
        if not valid_https_url(new_url):
            raise SubmissionError(
                "The download redirected to an invalid or non-HTTPS URL."
            )

        hostname = urllib.parse.urlparse(new_url).hostname.lower()

        if hostname not in ALLOWED_DOWNLOAD_HOSTS:
            raise SubmissionError(
                "The download redirected to an untrusted host."
            )

        return super().redirect_request(
            request, response, code, message, headers, new_url
        )


def download_package(url):
    opener = urllib.request.build_opener(SafeRedirectHandler())

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Fusion-Mod-Catalog-Submission-Scanner/1.0",
            "Accept": "application/octet-stream",
        },
    )

    try:
        with opener.open(request, timeout=DOWNLOAD_TIMEOUT) as response:
            final_url = response.geturl()
            parsed = urllib.parse.urlparse(final_url)

            if (
                parsed.scheme.lower() != "https"
                or not parsed.hostname
                or parsed.hostname.lower() not in ALLOWED_DOWNLOAD_HOSTS
            ):
                raise SubmissionError(
                    "The final download URL uses an untrusted host."
                )

            content_length = response.headers.get("Content-Length")

            if content_length:
                try:
                    if int(content_length) > MAX_DOWNLOAD_SIZE:
                        raise SubmissionError(
                            "The package exceeds the 500 MB download limit."
                        )
                except ValueError:
                    raise SubmissionError(
                        "The download returned an invalid Content-Length."
                    )

            data = bytearray()

            while True:
                chunk = response.read(1024 * 1024)

                if not chunk:
                    break

                data.extend(chunk)

                if len(data) > MAX_DOWNLOAD_SIZE:
                    raise SubmissionError(
                        "The package exceeds the 500 MB download limit."
                    )

            if not data:
                raise SubmissionError("The downloaded package is empty.")

            return bytes(data)

    except SubmissionError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SubmissionError(
            f"Could not download the package: {error}"
        )


def validate_archive(data, package_type, expected_id=None, expected_version=None):
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise SubmissionError(
            f"The downloaded {package_type} package is not a valid ZIP archive."
        )

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()

            if not entries:
                raise SubmissionError("The package archive is empty.")

            if len(entries) > MAX_ARCHIVE_FILES:
                raise SubmissionError(
                    "The package contains too many archive entries."
                )

            total_uncompressed = 0
            file_count = 0

            for entry in entries:
                name = entry.filename
                path = PurePosixPath(name)

                if (
                    not name
                    or "\\" in name
                    or path.is_absolute()
                    or ".." in path.parts
                    or ":" in name
                ):
                    raise SubmissionError(
                        "The package contains an unsafe archive path."
                    )

                if entry.flag_bits & 0x1:
                    raise SubmissionError(
                        "Encrypted archive entries are not supported."
                    )

                unix_mode = (entry.external_attr >> 16) & 0xFFFF

                if (unix_mode & 0o170000) == 0o120000:
                    raise SubmissionError(
                        "The package contains a symbolic link."
                    )

                if entry.is_dir():
                    continue

                file_count += 1
                total_uncompressed += entry.file_size

                if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
                    raise SubmissionError(
                        "The package exceeds the 500 MB uncompressed limit."
                    )

                if entry.file_size > 0:
                    if entry.compress_size == 0:
                        raise SubmissionError(
                            "The package contains a suspicious compressed file."
                        )

                    ratio = entry.file_size / entry.compress_size

                    if ratio > MAX_COMPRESSION_RATIO:
                        raise SubmissionError(
                            "The package exceeds the allowed compression ratio."
                        )

            if file_count == 0:
                raise SubmissionError(
                    "The package does not contain any files."
                )

            if package_type == "GEODE":
                manifest_names = [
                    entry.filename
                    for entry in entries
                    if entry.filename == "mod.json"
                ]

                if not manifest_names:
                    raise SubmissionError(
                        "The Geode package is missing its root mod.json manifest."
                    )

                try:
                    manifest_data = archive.read("mod.json")
                    manifest = json.loads(manifest_data)
                except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
                    raise SubmissionError(
                        "The Geode package has an invalid mod.json manifest."
                    )

                if not isinstance(manifest, dict):
                    raise SubmissionError(
                        "The Geode mod.json manifest must contain a JSON object."
                    )

                manifest_id = manifest.get("id")
                manifest_version = manifest.get("version")

                if not isinstance(manifest_id, str) or not ID_PATTERN.fullmatch(
                    manifest_id
                ):
                    raise SubmissionError(
                        "The Geode manifest contains an invalid mod ID."
                    )

                if expected_id and manifest_id != expected_id:
                    raise SubmissionError(
                        "The Geode manifest mod ID does not match the submitted Mod ID."
                    )

                if not isinstance(manifest_version, str):
                    raise SubmissionError(
                        "The Geode manifest is missing its version."
                    )

                validate_version(
                    manifest_version,
                    "Geode manifest version",
                )

                if expected_version and manifest_version != expected_version:
                    raise SubmissionError(
                        "The Geode manifest version does not match the submitted version."
                    )

    except zipfile.BadZipFile:
        raise SubmissionError("The package archive is damaged or invalid.")
    except OSError as error:
        raise SubmissionError(f"Could not inspect the package archive: {error}")


def validate_package(url, expected_sha, package_type, expected_id=None, expected_version=None):
    expected_extension = PACKAGE_EXTENSIONS[package_type]

    validate_release_asset_url(
        url,
        expected_extension,
        f"{package_type} download URL",
    )

    if not SHA_PATTERN.fullmatch(expected_sha):
        raise SubmissionError(
            f"The {package_type} SHA-256 must contain exactly 64 hexadecimal characters."
        )

    data = download_package(url)
    actual_sha = hashlib.sha256(data).hexdigest()

    if actual_sha.lower() != expected_sha.lower():
        raise SubmissionError(
            f"The {package_type} package SHA-256 does not match the submitted checksum."
        )

    validate_archive(
        data,
        package_type,
        expected_id=expected_id,
        expected_version=expected_version,
    )


def load_catalog():
    catalog_path = os.path.join("catalog", "index.json")

    try:
        with open(catalog_path, "r", encoding="utf-8") as file:
            catalog = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise SubmissionError(f"Could not read the mod catalog: {error}")

    if not isinstance(catalog, dict):
        raise SubmissionError("The catalog root must be a JSON object.")

    if catalog.get("schemaVersion") != 2:
        raise SubmissionError("The catalog must use schema version 2.")

    mods = catalog.get("mods")

    if not isinstance(mods, list):
        raise SubmissionError("The catalog mods field must be a list.")

    for mod in mods:
        if not isinstance(mod, dict):
            raise SubmissionError(
                "The catalog contains an invalid mod entry."
            )

    return catalog


def validate_submission(fields):
    errors = []

    def require_field(label):
        value = get_field(fields, label)

        if not value:
            errors.append(f"Missing required field: {label}")

        return value

    name = require_field("Mod Name")
    mod_id = require_field("Mod ID")
    description = require_field("Mod Description")
    creator = require_field("Mod Creator")
    version = require_field("Mod Version")
    runtime_value = require_field("Mod Runtime")
    package_type = require_field("Package Type")
    download = require_field("GitHub Release Download URL")
    release = require_field("Upstream Release URL")
    source = require_field("Source Repository")
    icon = require_field("Mod Icon URL")
    sha256 = require_field("Package SHA-256")
    platforms_value = require_field("Supported Platforms")
    fusion_supported_value = require_field(
        "Does this mod also support Fusion?"
    )

    if errors:
        raise SubmissionError("\n".join(errors))

    if not ID_PATTERN.fullmatch(mod_id):
        raise SubmissionError(
            "Mod ID must use lowercase letters, numbers, periods, hyphens, "
            "or underscores, and be no longer than 128 characters."
        )

    if not name or len(name) > 128:
        raise SubmissionError("Mod Name must be between 1 and 128 characters.")

    if len(description) > 5000:
        raise SubmissionError("Mod Description must not exceed 5000 characters.")

    if not creator or len(creator) > 128:
        raise SubmissionError(
            "Mod Creator must be between 1 and 128 characters."
        )

    validate_version(version, "Mod Version")

    runtime = runtime_value.strip().lower()
    package_type = package_type.strip().upper()

    if runtime not in SUPPORTED_RUNTIMES:
        raise SubmissionError("Mod Runtime must be Fusion or Geode.")

    expected_package = "ZIP" if runtime == "fusion" else "GEODE"

    if package_type != expected_package:
        raise SubmissionError(
            f"{runtime.title()} mods must use the {expected_package} package type."
        )

    validate_github_repository_url(source, "Source Repository")
    validate_github_repository_url(
        release,
        "Upstream Release URL",
        allow_subpaths=True
    )

    if not valid_https_url(icon):
        raise SubmissionError("Mod Icon URL must be a valid HTTPS URL.")

    platforms = [item.lower() for item in parse_list(platforms_value)]

    if not platforms:
        raise SubmissionError("At least one supported platform is required.")

    invalid_platforms = sorted(set(platforms) - SUPPORTED_PLATFORMS)

    if invalid_platforms:
        raise SubmissionError(
            "Unsupported platform(s): " + ", ".join(invalid_platforms)
        )

    if len(platforms) != len(set(platforms)):
        raise SubmissionError("Supported Platforms contains duplicates.")

    geode_minimum = get_field(fields, "Minimum Geode Version")
    geode_maximum = get_field(fields, "Maximum Geode Version")

    if runtime == "geode":
        if not geode_minimum:
            raise SubmissionError(
                "Geode mods must provide a Minimum Geode Version."
            )

        validate_version(geode_minimum, "Minimum Geode Version")

        if geode_maximum:
            validate_version(geode_maximum, "Maximum Geode Version")

            if version_tuple(geode_minimum) > version_tuple(geode_maximum):
                raise SubmissionError(
                    "Maximum Geode Version cannot be lower than Minimum Geode Version."
                )
    elif geode_minimum or geode_maximum:
        raise SubmissionError(
            "Fusion-native mods must leave Geode version fields blank."
        )

    fusion_supported_value = fusion_supported_value.strip().lower()

    if fusion_supported_value not in {"yes", "no"}:
        raise SubmissionError(
            "Does this mod also support Fusion? must be Yes or No."
        )

    fusion_download = get_field(fields, "Fusion Package Download URL")
    fusion_sha = get_field(fields, "Fusion Package SHA-256")

    if runtime == "fusion":
        if fusion_supported_value != "no":
            raise SubmissionError(
                "Fusion-native mods must select No for additional Fusion compatibility."
            )

        if fusion_download or fusion_sha:
            raise SubmissionError(
                "Fusion-native mods must leave the additional Fusion package fields blank."
            )

    if runtime == "geode" and fusion_supported_value == "yes":
        if not fusion_download or not fusion_sha:
            raise SubmissionError(
                "Geode mods supporting Fusion must provide both a Fusion ZIP URL and SHA-256."
            )

    if runtime == "geode" and fusion_supported_value == "no":
        if fusion_download or fusion_sha:
            raise SubmissionError(
                "Select Yes if you provide a separate Fusion ZIP package."
            )

    dependencies = parse_list(get_field(fields, "Dependencies"))
    conflicts = parse_list(get_field(fields, "Conflicts"))

    for label, values in (
        ("Dependencies", dependencies),
        ("Conflicts", conflicts),
    ):
        if len(values) != len(set(values)):
            raise SubmissionError(f"{label} contains duplicate IDs.")

        for value in values:
            if not ID_PATTERN.fullmatch(value):
                raise SubmissionError(
                    f"{label} contains an invalid mod ID: {value}"
                )

    if mod_id in dependencies:
        raise SubmissionError("A mod cannot depend on itself.")

    if mod_id in conflicts:
        raise SubmissionError("A mod cannot conflict with itself.")

    if set(dependencies) & set(conflicts):
        raise SubmissionError(
            "A mod cannot both depend on and conflict with the same mod."
        )

    permission_field = fields.get("Permissions", "")
    checked_permissions = {
        match.group(1).strip().casefold()
        for match in re.finditer(
            r"(?im)^\s*-\s*\[x\]\s*(.+?)\s*$",
            permission_field
        )
    }

    required_permissions = {
        "i own this mod or have permission to submit it.",
        "i have permission to distribute this downloadable package.",
    }

    missing_permissions = required_permissions - checked_permissions

    if missing_permissions:
        raise SubmissionError(
            "Both permission confirmations must be checked. Missing: "
            + "; ".join(sorted(missing_permissions))
        )

    catalog = load_catalog()
    existing_mods = catalog["mods"]
    existing_ids = {
        mod.get("id")
        for mod in existing_mods
        if isinstance(mod.get("id"), str)
    }

    if mod_id in existing_ids:
        raise SubmissionError(
            f"The Mod ID '{mod_id}' is already registered."
        )

    for dependency in dependencies:
        if dependency not in existing_ids:
            raise SubmissionError(
                f"Dependency '{dependency}' is not registered in the catalog."
            )

    for conflict in conflicts:
        if conflict not in existing_ids:
            raise SubmissionError(
                f"Conflict '{conflict}' is not registered in the catalog."
            )

    existing_by_id = {
        mod["id"]: mod
        for mod in existing_mods
        if isinstance(mod.get("id"), str)
    }

    for dependency in dependencies:
        dependency_mod = existing_by_id[dependency]
        dependency_runtime = dependency_mod.get("runtime")

        if runtime == "fusion" and dependency_runtime == "geode":
            fusion_package = dependency_mod.get("fusionPackage")
            compatibility = dependency_mod.get("compatibility", {})
            fusion_compatibility = (
                compatibility.get("fusion", {})
                if isinstance(compatibility, dict)
                else {}
            )

            if (
                not isinstance(fusion_package, dict)
                or fusion_compatibility.get("supported") is not True
            ):
                raise SubmissionError(
                    f"Fusion mod dependency '{dependency}' does not provide a compatible Fusion package."
                )

        elif runtime == "geode" and dependency_runtime != "geode":
            raise SubmissionError(
                f"Geode mods cannot depend on Fusion-only mod '{dependency}'."
            )

    validate_package(
        download,
        sha256,
        package_type,
        expected_id=mod_id if runtime == "geode" else None,
        expected_version=version if runtime == "geode" else None,
    )

    if runtime == "geode" and fusion_supported_value == "yes":
        validate_package(
            fusion_download,
            fusion_sha,
            "ZIP",
        )

    return (
        f"## Fusion Submission Guard: Passed\n\n"
        f"- **Mod:** {name}\n"
        f"- **Mod ID:** `{mod_id}`\n"
        f"- **Version:** `{version}`\n"
        f"- **Runtime:** {runtime.title()}\n"
        f"- **Package:** {package_type}\n"
        f"- **Platforms:** {', '.join(platforms)}\n"
        f"- **Dependencies:** {len(dependencies)}\n"
        f"- **Conflicts:** {len(conflicts)}\n"
        f"- **Separate Fusion package:** "
        f"{'Yes' if runtime == 'geode' and fusion_supported_value == 'yes' else 'No'}\n\n"
        f"Both package checks, checksums, and submission validations passed."
    )


def write_github_output(passed, report):
    output_path = os.environ.get("GITHUB_OUTPUT")

    if not output_path:
        return

    delimiter = "FUSION_REPORT_" + hashlib.sha256(
        report.encode("utf-8")
    ).hexdigest()[:24]

    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"passed={'true' if passed else 'false'}\n")
        output.write(f"report<<{delimiter}\n")
        output.write(report)
        output.write(f"\n{delimiter}\n")


def main():
    body = sys.stdin.read()

    try:
        if not body.strip():
            raise SubmissionError("The issue body is empty.")

        fields = parse_fields(body)
        report = validate_submission(fields)
        passed = True

    except SubmissionError as error:
        report = (
            "## Fusion Submission Guard: Validation Failed\n\n"
            + "\n".join(f"- {line}" for line in str(error).splitlines())
        )
        passed = False

    except Exception as error:
        report = (
            "## Fusion Submission Guard: Unexpected Scanner Error\n\n"
            "The scanner encountered an unexpected error. "
            "Check the Actions logs.\n\n"
            f"```text\n{type(error).__name__}: {error}\n```"
        )
        passed = False

    print(report)
    write_github_output(passed, report)

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
