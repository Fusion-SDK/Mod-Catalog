
import json
import os
import sys
from pathlib import Path

STAFF_FILE = Path("config/staff.json")

ROLE_LEVELS = {
    "reviewers": 1,
    "moderators": 2,
    "administrators": 3
}


def load_staff():
    if not STAFF_FILE.exists():
        raise RuntimeError("config/staff.json is missing")

    with STAFF_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("schemaVersion") != 1:
        raise RuntimeError("Unsupported staff configuration version")

    roles = data.get("roles")

    if not isinstance(roles, dict):
        raise RuntimeError("Invalid staff roles configuration")

    for role in ROLE_LEVELS:
        members = roles.get(role)

        if not isinstance(members, list):
            raise RuntimeError(f"Invalid member list: {role}")

        if any(not isinstance(member, str) or not member.strip()
               for member in members):
            raise RuntimeError(f"Invalid username in role: {role}")

    return roles


def main():
    username = os.environ.get("GITHUB_ACTOR", "").strip().casefold()
    required_role = os.environ.get("REQUIRED_ROLE", "").strip().lower()
    github_permission = os.environ.get(
        "GITHUB_PERMISSION", ""
    ).strip().lower()

    if not username:
        print("Missing GitHub actor.")
        return 1

    if required_role not in ROLE_LEVELS:
        print("Invalid required role.")
        return 1

    roles = load_staff()

    member_role = None

    for role, level in ROLE_LEVELS.items():
        members = {
            member.strip().casefold()
            for member in roles[role]
        }

        if username in members:
            if member_role is None or level > ROLE_LEVELS[member_role]:
                member_role = role

    if member_role is None:
        print(f"DENIED: {username} is not Fusion staff.")
        return 1

    if ROLE_LEVELS[member_role] < ROLE_LEVELS[required_role]:
        print(f"DENIED: {username} lacks the required role.")
        return 1

    if github_permission not in ("admin", "maintain", "write"):
        print("DENIED: Insufficient GitHub repository permission.")
        return 1

    print(f"AUTHORIZED: {username} has the {member_role} role.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Permission check failed: {error}")
        sys.exit(1)
