
import hashlib
import io
import json
import os
import re
import struct
import sys
import urllib.request
import urllib.parse
import zipfile
from pathlib import PurePosixPath

MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024
MAX_ARCHIVE_FILES = 10000
MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200

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
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


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


def version_tuple(version):
    match = VERSION_PATTERN.fullmatch(version)

    if not match:
        raise ValueError(f"Invalid version: {version}")

    return (
