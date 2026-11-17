
import json
import os
import re
import sys
from pathlib import Path

STAFF_FILE = Path("config/staff.json")

ROLE_MAP = {
    "reviewer": "reviewers",
    "moderator": "moderators",
    "administrator": "administrators"
}


def main():
    action = os.environ["STAFF_ACTION"].strip()
    username = os.environ["STAFF_USERNAME"].strip()
    role = os.environ["STAFF_ROLE"].strip().lower()
    reason = os.environ.get("STAFF_REASON", "").strip()

    if not reason:
        raise ValueError("A reason is required for staff changes.")

    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", username):
        raise ValueError("Invalid GitHub username.")

    if role not in ROLE_MAP:
        raise ValueError("Invalid staff role.")

    data = json.loads(STAFF_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise ValueError("Unsupported or invalid staff configuration.")

    roles = data.get("roles")

    if not isinstance(roles, dict):
        raise ValueError("Staff roles configuration is invalid.")

    for role_name in ("administrators", "moderators", "reviewers"):
        if not isinstance(roles.get(role_name), list):
            raise ValueError(f"Staff role '{role_name}' must be a list.")

    if action == "Add staff member":
        for members in roles.values():
            members[:] = [
                member for member in members
                if member.casefold() != username.casefold()
            ]

        roles[ROLE_MAP[role]].append(username)

    elif action == "Remove staff member":
        found = False

        for members in roles.values():
            original_length = len(members)
            members[:] = [
                member for member in members
                if member.casefold() != username.casefold()
            ]

            if len(members) < original_length:
                found = True

        if not found:
            raise ValueError("This user is not currently Fusion staff.")

    else:
        raise ValueError("Invalid staff action.")

    if not roles["administrators"]:
        raise ValueError("Cannot remove the last administrator.")

    temporary = STAFF_FILE.with_suffix(".json.tmp")

    temporary.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8"
    )
    temporary.replace(STAFF_FILE)

    print(f"Successfully updated staff roles for {username}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Staff management failed: {error}", file=sys.stderr)
        sys.exit(1)
