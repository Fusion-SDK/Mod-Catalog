
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "index.json"

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
VERSION_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$"
)
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def parse_fields(body):
    fields = {}
    sections = re.split(r"(?m)^###\s+", body)

    for section in sections[1:]:
        lines = section.splitlines()
        if not lines:
            continue

        heading = lines[0].strip()
        value = "\n".join(lines[1:]).strip()

        fields[heading] = value

    return fields


def required(fields, name):
    value = fields.get(name, "").strip()

    if not value or value == "_No response_":
        raise ValueError(f"Missing required field: {name}")

    return value


def validate_https_url(value, name):
    parsed = urlparse(value)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{name} must be a valid HTTPS URL.")

    return value


def main():
    body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    issue_url = os.environ["ISSUE_URL"]

    fields = parse_fields(body)

    mod_id = required(fields, "Mod ID").lower()
    name = required(fields, "Mod Name")
    description = required(fields, "Mod Description")
    creator = required(fields, "Mod Creator")
    version = required(fields, "Mod Version")

    download_url = validate_https_url(
        required(fields, "GitHub Release Download URL"),
        "Download URL"
    )

    repository = validate_https_url(
        required(fields, "Source Repository"),
        "Source repository"
    )

    icon = validate_https_url(
        required(fields, "Mod Icon URL"),
        "Mod icon URL"
    )

    sha256 = required(fields, "Package SHA-256").lower()

    if not ID_PATTERN.fullmatch(mod_id):
        raise ValueError("Mod ID contains invalid characters.")

    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("Version must use a valid three-part version.")

    if not SHA_PATTERN.fullmatch(sha256):
        raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters.")

    if urlparse(download_url).hostname != "github.com":
        raise ValueError("Download URL must point to github.com.")

    if urlparse(repository).hostname != "github.com":
        raise ValueError("Source repository must point to github.com.")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    if not isinstance(catalog.get("mods"), list):
        raise ValueError("Catalog mods must be a JSON array.")

    for existing in catalog["mods"]:
        if existing.get("id", "").lower() == mod_id:
            raise ValueError(f"Mod ID already exists: {mod_id}")

    mod = {
        "id": mod_id,
        "name": name,
        "description": description,
        "creator": creator,
        "version": version,
        "icon": icon,
        "repository": repository,
        "releaseUrl": "",
        "downloadUrl": download_url,
        "sha256": sha256,
        "approved": True,
        "registrationIssue": issue_url
    }

    catalog["mods"].append(mod)

    CATALOG.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"Registered mod: {name}")
    print(f"Mod ID: {mod_id}")
    print(f"Registration issue: #{issue_number}")


if __name__ == "__main__":
    main()
