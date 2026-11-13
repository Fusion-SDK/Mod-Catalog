
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "index.json"
README = ROOT / "README.md"

START = "<!-- MOD_TABLE_START -->"
END = "<!-- MOD_TABLE_END -->"


def clean(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def generate_table(mods):
    lines = [
        "| Mod Name | Mod Description | Mod Creator | Mod Version | Mod Icon |",
        "|---|---|---|---|---|"
    ]

    approved = sorted(
        [mod for mod in mods if mod.get("approved") is True],
        key=lambda mod: mod.get("name", "").lower()
    )

    for mod in approved:
        name = clean(mod.get("name"))
        description = clean(mod.get("description"))
        creator = clean(mod.get("creator"))
        version = clean(mod.get("version"))
        icon = clean(mod.get("icon"))

        icon_cell = f"![{name}]({icon})" if icon else "No icon"

        lines.append(
            f"| {name} | {description} | {creator} | {version} | {icon_cell} |"
        )

    if not approved:
        lines.append("| No registered mods yet | - | - | - | - |")

    return "\n".join(lines)


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    readme = README.read_text(encoding="utf-8")

    if START not in readme or END not in readme:
        raise RuntimeError("README is missing the mod table markers.")

    table = generate_table(catalog.get("mods", []))

    before, remainder = readme.split(START, 1)
    _, after = remainder.split(END, 1)

    updated = f"{before}{START}\n{table}\n{END}{after}"
    README.write_text(updated, encoding="utf-8")

    print("README mod table updated.")


if __name__ == "__main__":
    main()
