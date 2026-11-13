
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import zipfile
from pathlib import PurePosixPath

MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024
MAX_ARCHIVE_FILES = 10000
MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200

ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}


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


def valid_https_url(value):
    try:
        parsed = urllib.parse.urlparse(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)

        if (
            parsed.scheme != "https"
            or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS
        ):
            raise ValueError("Download redirected to an untrusted host.")

        return super().redirect_request(
            req, fp, code, msg, headers, newurl
        )


def download_package(url):
    parsed = urllib.parse.urlparse(url)

    if (
        not valid_https_url(url)
        or parsed.hostname != "github.com"
        or "/releases/download/" not in parsed.path
    ):
        raise ValueError(
            "Use a public GitHub Release asset download URL."
        )

    opener = urllib.request.build_opener(SafeRedirectHandler())

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Fusion-Submission-Guard/1.0"}
    )

    with opener.open(request, timeout=30) as response:
        final_host = urllib.parse.urlparse(response.geturl()).hostname

        if final_host not in ALLOWED_DOWNLOAD_HOSTS:
            raise ValueError("Package came from an untrusted host.")

        content_length = response.headers.get("Content-Length")

        if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
            raise ValueError("Package exceeds the 100 MB download limit.")

        data = response.read(MAX_DOWNLOAD_SIZE + 1)

    if len(data) > MAX_DOWNLOAD_SIZE:
        raise ValueError("Package exceeds the 100 MB download limit.")

    if not data:
        raise ValueError("The downloaded package is empty.")

    return data


def inspect_archive(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()

            if not entries:
                raise ValueError("The package archive is empty.")

            if len(entries) > MAX_ARCHIVE_FILES:
                raise ValueError("The archive contains too many files.")

            total_size = 0

            for entry in entries:
                path = entry.filename.replace("\\", "/")
                parsed = PurePosixPath(path)

                if (
                    parsed.is_absolute()
                    or ".." in parsed.parts
                    or (parsed.parts and ":" in parsed.parts[0])
                ):
                    raise ValueError(
                        f"Unsafe archive path detected: {entry.filename}"
                    )

                total_size += entry.file_size

                if total_size > MAX_UNCOMPRESSED_SIZE:
                    raise ValueError(
                        "Archive expands beyond the 500 MB limit."
                    )

                if entry.file_size > 0:
                    ratio = entry.file_size / max(entry.compress_size, 1)

                    if ratio > MAX_COMPRESSION_RATIO:
                        raise ValueError(
                            f"Suspicious compression ratio: {entry.filename}"
                        )

            broken_file = archive.testzip()

            if broken_file:
                raise ValueError(
                    f"Corrupted archive entry: {broken_file}"
                )

    except zipfile.BadZipFile:
        raise ValueError(
            "The submitted package is not a valid ZIP-based archive."
        )


def run_scan():
    body = sys.stdin.read()
    fields = parse_fields(body)
    problems = []

    required_fields = [
        "Mod Name",
        "Mod ID",
        "Mod Description",
        "Mod Creator",
        "Mod Version",
        "GitHub Release Download URL",
        "Source Repository",
        "Mod Icon URL",
    ]

    for field in required_fields:
        if not get_field(fields, field):
            problems.append(f"**{field}:** This field is required.")

    sha = get_field(fields, "SHA-256", "Package SHA-256")

    if not sha:
        problems.append("**SHA-256:** This field is required.")
    elif not re.fullmatch(r"[a-fA-F0-9]{64}", sha):
        problems.append(
            "**SHA-256:** Provide exactly 64 hexadecimal characters."
        )

    mod_id = get_field(fields, "Mod ID")

    if mod_id and not re.fullmatch(
        r"[a-z0-9][a-z0-9._-]{0,127}", mod_id
    ):
        problems.append(
            "**Mod ID:** Use lowercase letters, numbers, dots, "
            "hyphens, or underscores."
        )

    version = get_field(fields, "Mod Version")

    if version and not re.fullmatch(
        r"v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version
    ):
        problems.append(
            "**Mod Version:** Use a version such as `1.0.0` or `v1.0.0`."
        )

    download_url = get_field(fields, "GitHub Release Download URL")
    source_url = get_field(fields, "Source Repository")
    icon_url = get_field(fields, "Mod Icon URL")

    if download_url and not valid_https_url(download_url):
        problems.append("**Download URL:** Provide a valid HTTPS URL.")

    if source_url:
        parsed = urllib.parse.urlparse(source_url)

        if (
            not valid_https_url(source_url)
            or parsed.hostname != "github.com"
            or len(parsed.path.strip("/").split("/")) != 2
        ):
            problems.append(
                "**Source Repository:** Provide a GitHub repository URL."
            )

    if icon_url and not valid_https_url(icon_url):
        problems.append("**Mod Icon URL:** Provide a valid HTTPS URL.")

    permissions = get_field(fields, "Permissions")

    if "I own this mod or have permission to submit it." not in permissions:
        problems.append(
            "**Ownership permission:** Confirm that you own the mod "
            "or have permission to submit it."
        )

    if "I have permission to distribute this downloadable package." not in permissions:
        problems.append(
            "**Distribution permission:** Confirm permission to distribute."
        )

    if not problems:
        try:
            package = download_package(download_url)
            actual_sha = hashlib.sha256(package).hexdigest()

            if actual_sha.lower() != sha.lower():
                raise ValueError(
                    "SHA-256 does not match the downloaded package."
                )

            inspect_archive(package)

        except Exception as error:
            problems.append(f"**Package validation:** {error}")

    if problems:
        return False, (
            "## Fusion Submission Guard: Changes required\n\n"
            + "\n".join(f"- {problem}" for problem in problems)
        )

    return True, (
        "## Fusion Submission Guard: Passed\n\n"
        "Automated checks passed. Manual review is still required."
    )


def main():
    try:
        passed, report = run_scan()

    except Exception as error:
        passed = False
        report = (
            "## Fusion Submission Guard: Scanner error\n\n"
            f"The scanner encountered an unexpected error: `{error}`"
        )

    print(report, flush=True)

    output_path = os.environ.get("GITHUB_OUTPUT")

    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"passed={'true' if passed else 'false'}\n")
            output.write("report<<FUSION_REPORT\n")
            output.write(report + "\n")
            output.write("FUSION_REPORT\n")

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
