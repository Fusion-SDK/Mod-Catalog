
import re
import sys
from urllib.parse import urlparse

def parse_fields(body):
    fields = {}
    sections = re.split(r"(?m)^###\s+", body)

    for section in sections[1:]:
        lines = section.splitlines()
        if lines:
            fields[lines[0].strip()] = "\n".join(lines[1:]).strip()

    return fields


def main():
    body = sys.stdin.read()
    fields = parse_fields(body)
    problems = []

    def get(name):
        value = fields.get(name, "").strip()
        if not value or value == "_No response_":
            return ""
        return value

    def check_url(field, label, required_host=None):
        value = get(field)

        if not value:
            problems.append(f"- **{label}:** This field is missing.")
            return

        parsed = urlparse(value)

        if parsed.scheme != "https" or not parsed.hostname:
            problems.append(
                f"- **{label}:** Provide a valid HTTPS URL."
            )
        elif required_host and parsed.hostname.lower() != required_host:
            problems.append(
                f"- **{label}:** The URL must use {required_host}."
            )

    for field in [
        "Mod Name",
        "Mod ID",
        "Mod Description",
        "Mod Creator",
        "Mod Version",
        "Package SHA-256"
    ]:
        if not get(field):
            problems.append(f"- **{field}:** This field is required.")

    mod_id = get("Mod ID")
    if mod_id and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", mod_id):
        problems.append(
            "- **Mod ID:** Use lowercase letters, numbers, dots, "
            "hyphens, or underscores."
        )

    version = get("Mod Version")
    if version and not re.fullmatch(
        r"v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",
        version
    ):
        problems.append(
            "- **Mod Version:** Use a version such as `1.0.0` or `v1.0.0`."
        )

    sha = get("Package SHA-256")
    if sha and not re.fullmatch(r"[a-fA-F0-9]{64}", sha):
        problems.append(
            "- **Package SHA-256:** Provide exactly 64 hexadecimal characters "
            "calculated from the submitted ZIP file."
        )

    check_url(
        "GitHub Release Download URL",
        "GitHub Release Download URL",
        "github.com"
    )
    check_url(
        "Source Repository",
        "Source Repository",
        "github.com"
    )
    check_url("Mod Icon URL", "Mod Icon URL")

    permissions = get("Permissions")

    if "I own this mod or have permission to submit it." not in permissions:
        problems.append(
            "- **Ownership permission:** Confirm that you own the mod "
            "or have permission to submit it."
        )

    if "I have permission to distribute this downloadable package." not in permissions:
        problems.append(
            "- **Distribution permission:** Confirm that you have "
            "permission to distribute the package."
        )

    if problems:
        print("NEEDS_CHANGES")
        print("\n".join(problems))
    else:
        print("READY_FOR_REVIEW")
        print("Automated field checks passed. Manual review is still required.")


if __name__ == "__main__":
    main()
