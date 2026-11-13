
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


def main():
    if os.environ.get("CONFIRM_REMOVAL") != "YES":
        raise RuntimeError("Removal confirmation is missing.")

    body = os.environ.get("ISSUE_BODY", "")
    fields = parse_fields(body)

    mod_id = get_field(fields, "Mod ID")
    mod_name = get_field(fields, "Mod Name")
    creator = get_field(fields, "Mod Creator")

    if not all([mod_id, mod_name, creator]):
        raise ValueError("Removal request is missing required information.")

    if not CATALOG.exists():
        raise FileNotFoundError("Catalog file does not exist.")

    with CATALOG.open("r", encoding="utf-8") as file:
        catalog = json.load(file)

    if not isinstance(catalog, dict):
        raise ValueError("Invalid catalog structure.")

    mods = catalog.get("mods")

    if not isinstance(mods, list):
        raise ValueError("Catalog mods must be a list.")

    matches = [
        (index, mod)
        for index, mod in enumerate(mods)
        if isinstance(mod, dict)
        and mod.get("id", "").casefold() == mod_id.casefold()
    ]

    if len(matches) == 0:
        raise ValueError("No catalog entry matches this Mod ID.")

    if len(matches) > 1:
        raise ValueError("Multiple entries match. Manual review required.")

    index, mod = matches[0]

    if not isinstance(mod.get("name"), str):
        raise ValueError("Catalog mod name is invalid.")

    if not isinstance(mod.get("creator"), str):
        raise ValueError("Catalog creator is invalid.")

    if mod["name"].casefold() != mod_name.casefold():
        raise ValueError("Mod name does not match the catalog.")

    if mod["creator"].casefold() != creator.casefold():
        raise ValueError("Mod creator does not match the catalog.")

    # Remove only the exact verified entry.
    removed = mods.pop(index)

    temporary = CATALOG.with_suffix(".json.tmp")

    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(catalog, file, indent=2, ensure_ascii=False)
            file.write("\n")

        os.replace(temporary, CATALOG)

    finally:
        if temporary.exists():
            temporary.unlink()

    print("REMOVAL_SUCCESS")
    print(f"Removed Mod ID: {removed['id']}")
    print(f"Removed Mod Name: {removed['name']}")
    print(f"Removed Creator: {removed['creator']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"REMOVAL_FAILED: {error}", file=sys.stderr)
        sys.exit(1)
