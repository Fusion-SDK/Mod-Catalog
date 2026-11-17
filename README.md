[README.md](https://github.com/user-attachments/files/34975160/README.md)
# Fusion Mod Catalog

The official directory of Geometry Dash mods supported by Fusion. The catalog supports Fusion-native mods and Geode mods. A Geode mod requires the Geode loader; it is compatible with Fusion only when it also publishes a separate Fusion-compatible ZIP package.

## Registered Mods

<!-- MOD_TABLE_START -->
| Mod Name | Mod Description | Mod Creator | Mod Version | Mod Icon |
|---|---|---|---|---|
| No registered mods yet | - | - | - | - |
<!-- MOD_TABLE_END -->

The table is generated from `catalog/index.json`. Approved registration, update, and removal workflows regenerate it.

## Submit a Mod

1. Open **Issues** and choose **Register Fusion Mod**.
2. Complete the form and confirm both permission checkboxes.
3. The automated review checks the package download, SHA-256 checksum, archive safety, and (for Geode packages) the root `mod.json` ID and version.
4. A Fusion moderator reviews the submission and applies the `Approved` label.
5. Only submissions that pass the scanner are added to the catalog.

Fusion-native mods use a ZIP package. Geode mods use a `.geode` package. A Geode mod that also supports Fusion must provide a separate Fusion ZIP and its own SHA-256 checksum.

## Submit an Update

Use the **Mod Update Submission** issue form for an existing catalog entry. The developer account must be a listed maintainer or a Fusion administrator. The workflow checks the current catalog version, requires a higher version, validates and downloads the new package, verifies its SHA-256 checksum, and records the previous release in update history.

A moderator must apply the `approved-update` label before the update is committed.

## Request Removal

Use the **Mod Removal Request** issue form. The request is checked against the catalog and must include both confirmation checkboxes. A Fusion moderator must apply `Removal Approved`. Removal is blocked while another catalog entry depends on or conflicts with the mod being removed.

## Request a Staff Change

Use the **Fusion Staff Management** issue form. Only a Fusion administrator can approve a request by applying `Staff Approved`. The workflow prevents removal of the final administrator.

## Required GitHub Labels

Create these labels in the repository (spelling and capitalization matter):

| Label | Purpose |
|---|---|
| `Mod Submission` | Registration issue label |
| `Approved` | Moderator approval for a registration |
| `Needs Changes` | Registration needs corrections |
| `Rejected` | Reject a registration |
| `mod-update` | Update issue label |
| `approved-update` | Moderator approval for an update |
| `removal-request` | Removal request issue label |
| `Removal Approved` | Moderator approval for removal |
| `Invalid Request` | Invalid removal request |
| `staff-request` | Staff request issue label |
| `Staff Approved` | Administrator approval for a staff change |

## Repository Setup

- Add the initial Fusion administrator to `config/staff.json`.
- Ensure the administrator and moderators have the appropriate repository write access.
- In **Settings → Actions → General**, allow GitHub Actions to use a read-and-write `GITHUB_TOKEN`.
- Keep workflow files and issue templates enabled.
- The workflows use explicit least-privilege permissions and check the acting staff member against both `config/staff.json` and their GitHub repository permission.

## Validation

Run the catalog validator locally before merging catalog changes:

```bash
python scripts/validate_catalog.py
```

Compile the Python scripts with:

```bash
python -m compileall -q scripts
```

## About Fusion

Fusion is an independent Geometry Dash modding platform with its own mod loader, installer, and mod catalog.
