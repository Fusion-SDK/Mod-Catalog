
import json
import os
import re
import sys
from pathlib import Path

CATALOG = Path("catalog/index.json")


def parse_fields(body):
    fields = {}
    sections = re.split(r"(?m)^###\s+", body)

    for section in sections[1:]:
        lines = section.splitlines()
        if lines:
            fields[lines[0].strip()] = "\n".join(lines[1:]).strip()

    return fields


def get_field(fields, name):
    value = fields.get(name, "").strip()

    if not value or value == "_No response_":
        return ""

    return value


def checked_labels(fields, section_name):
    section = fields.get(section_name, "")
    return {
        match.group(1).strip().casefold()
        for match in re.finditer(
            r"(?im)^\s*-\s*\[x\]\s*(.+?)\s*$",
            section
        )
    }


def main():
    body = os.environ.get("ISSUE_BODY", "")
    fields = parse_fields(body)

    mod_id = get_field(fields, "Mod ID")
    mod_name = get_field(fields, "Mod Name")
    creator = get_field(fields, "Mod Creator")
    requester = get_field(fields, "Requester GitHub Username")
    issue_author = os.environ.get("ISSUE_AUTHOR", "").strip()

    problems = []

    if not mod_id:
        problems.append("Mod ID is missing.")

    if not mod_name:
        problems.append("Mod Name is missing.")

    if not creator:
        problems.append("Mod Creator is missing.")

    if not requester:
        problems.append("Requester GitHub Username is missing.")

    if not issue_author:
        problems.append("GitHub issue author is missing.")

    if requester and issue_author and requester.lstrip("@").casefold() != issue_author.lstrip("@").casefold():
        problems.append("Requester GitHub Username must match the issue author.")

    required_confirmations = {
        "i confirm that the information provided is accurate.",
        "i understand that removal requires fusion staff authorization.",
    }
    missing_confirmations = required_confirmations - checked_labels(
        fields,
        "Confirmation"
    )

    if missing_confirmations:
        problems.append("Both removal confirmations must be checked.")

    if problems:
        print("\n".join(problems))
        return 1

    if not CATALOG.exists():
        print("Catalog file is missing.")
        return 1

    with CATALOG.open("r", encoding="utf-8") as file:
        catalog = json.load(file)

    mods = catalog.get("mods", [])

    if not isinstance(mods, list):
        print("Catalog structure is invalid.")
        return 1

    matches = [
        mod for mod in mods
        if isinstance(mod, dict)
        and str(mod.get("id", "")).casefold() == mod_id.casefold()
    ]

    if not matches:
        print(f"Mod ID '{mod_id}' does not exist in the catalog.")
        return 1

    if len(matches) != 1:
        print("Multiple catalog entries match this Mod ID.")
        return 2

    mod = matches[0]

    if str(mod.get("name", "")).casefold() != mod_name.casefold():
        print("Mod Name does not match the catalog.")
        return 1

    if str(mod.get("creator", "")).casefold() != creator.casefold():
        print("Mod Creator does not match the catalog.")
        return 1

    print("REMOVAL_REQUEST_VALID")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Validation error: {error}")
        sys.exit(1)
