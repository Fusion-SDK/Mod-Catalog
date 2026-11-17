# Contributing to the Fusion Mod Catalog

Thank you for your interest in contributing to the **Fusion Mod Catalog**!

The Fusion Mod Catalog is a community-driven catalog of Geometry Dash mods supported by Fusion. We welcome mod developers, contributors, and community members who want to help improve the catalog.

Please read these guidelines before submitting a contribution.

---

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Registering a Mod](#registering-a-mod)
- [Submitting Mod Updates](#submitting-mod-updates)
- [Requesting Mod Removal](#requesting-mod-removal)
- [Contributing to the Catalog](#contributing-to-the-catalog)
- [Fusion and Geode Compatibility](#fusion-and-geode-compatibility)
- [Submission Requirements](#submission-requirements)
- [Review and Approval Process](#review-and-approval-process)
- [Security and Safety](#security-and-safety)
- [Questions and Support](#questions-and-support)

---

## Ways to Contribute

There are several ways to contribute to the Fusion Mod Catalog:

- **Mod Developers:** Register your Geometry Dash mods and maintain their catalog information.
- **Developers:** Help improve catalog scripts, validation systems, and automation.
- **Community Members:** Report incorrect information, broken download links, or other catalog issues.
- **Staff Members:** Review submissions, approve updates, and help maintain the catalog.

All contributions should help keep the catalog accurate, reliable, and useful.

---

## Registering a Mod

Mod developers can request that their mods be added to the catalog.

To register a mod:

1. Open the repository's **Issues** page.
2. Select the official **Mod Registration** issue template.
3. Complete all required fields.
4. Verify that the information and download links are correct.
5. Submit the issue.

Your submission will be reviewed by the catalog staff.

### Important

- Only submit mods that you have permission to distribute.
- Provide valid release and download links.
- Include the required SHA-256 checksum.
- Make sure your compatibility information is accurate.
- Do not submit malicious, misleading, or impersonating software.

Submitting a registration request does not guarantee approval.

---

## Submitting Mod Updates

Existing mod maintainers can request updates to their registered mods.

To request an update:

1. Open the repository's **Issues** page.
2. Select the official **Mod Update** issue template.
3. Provide the mod ID and updated version information.
4. Include the updated release and download information.
5. Submit the request.

Update submissions are validated before staff approval.

Approved updates will update the catalog entry and preserve the mod's update history.

Do not create a new registration request just to update an existing mod.

---

## Requesting Mod Removal

If you are an authorized maintainer or have a valid reason to request a mod's removal, use the official removal request process.

Removal requests should include:

- The mod's catalog ID.
- The reason for requesting removal.
- Confirmation that you are authorized to make the request, where applicable.

Removal requests are reviewed by catalog staff.

A mod may also be removed if it violates catalog requirements or is no longer suitable for distribution.

Removing a mod may affect other mods that depend on it. Dependency checks are performed to help prevent broken catalog entries.

---

## Contributing to the Catalog

We welcome contributions that improve the catalog's code, documentation, validation, and automation.

Examples include:

- Fixing bugs in catalog scripts.
- Improving validation and security checks.
- Fixing GitHub Actions workflows.
- Improving documentation.
- Improving compatibility handling.
- Adding automated tests.
- Improving error messages and reporting.

### Pull Request Guidelines

When submitting a code contribution:

1. Fork the repository.
2. Create a branch for your changes.
3. Make your changes.
4. Test your changes before submitting.
5. Open a pull request describing what you changed and why.

Keep pull requests focused. Large changes should be explained clearly so reviewers can understand their purpose.

### Code Quality

Contributions should:

- Follow the existing project structure and conventions.
- Avoid unnecessary dependencies.
- Handle invalid input safely.
- Provide useful error messages.
- Avoid exposing secrets, credentials, or private information.
- Preserve existing catalog functionality unless a change is intentional.

Changes to catalog schemas or validation rules should include appropriate tests or documentation updates.

---

## Fusion and Geode Compatibility

The Fusion Mod Catalog supports two mod runtimes:

- **Fusion:** Mods designed to run natively through Fusion.
- **Geode:** Mods designed to run through the Geode loader.

These runtimes are not interchangeable.

### Fusion Mods

Fusion-native mods should provide a compatible Fusion package.

### Geode Mods

Geode mods must provide a valid Geode package and declare their Geode compatibility requirements.

A Geode package does not automatically work without Geode.

### Dual-Runtime Mods

A Geode mod may also provide a separate Fusion-compatible package.

In that case, the catalog entry can include both:

- The original Geode package.
- A separate Fusion-compatible ZIP package.

The Fusion package must be independently valid and must actually support Fusion.

Do not claim Fusion compatibility simply because a mod supports Geode.

---

## Submission Requirements

All mod submissions and updates must meet the catalog's validation requirements.

Submissions should provide:

- A valid, unique mod ID.
- A mod name and description.
- Creator and maintainer information.
- A valid version number.
- The correct package type.
- Accurate runtime and compatibility information.
- Valid repository and release URLs.
- A valid download URL.
- A SHA-256 checksum.
- Correct dependency and conflict information, where applicable.

Download links must use HTTPS.

Submissions must not contain:

- Malware or intentionally harmful software.
- Unauthorized copies of other developers' work.
- Misleading compatibility claims.
- Fake download links or checksums.
- Impersonation or deceptive metadata.
- Content that violates applicable laws or the repository's policies.

The catalog's automated validation systems may reject submissions that do not meet these requirements.

---

## Review and Approval Process

The catalog uses automated validation and staff review to help maintain quality.

The general process is:

1. A contributor submits a registration, update, or removal request.
2. Automated checks validate the submitted information.
3. Staff review the request.
4. Staff may approve the request or request changes.
5. Approved changes are applied to the catalog.
6. Relevant automation updates catalog documentation where applicable.

Staff members may request additional information or reject submissions that do not meet the requirements.

Do not attempt to bypass the review process or modify approval information without authorization.

---

## Security and Safety

Security is important to the Fusion Mod Catalog.

Contributors must:

- Never commit API keys, tokens, passwords, or other secrets.
- Never intentionally weaken security validation.
- Never bypass permission checks.
- Never submit malicious code or packages.
- Never attempt to manipulate catalog approval workflows.
- Report security vulnerabilities responsibly.

Do not publish sensitive vulnerability details in a public issue. Use the repository's available private security reporting options or contact the repository maintainers.

---

## Questions and Support

If you have questions about contributing, mod registration, compatibility, or catalog maintenance, open an appropriate GitHub issue or contact the repository maintainers.

Please avoid opening duplicate issues for questions that have already been answered.

---

## Final Notes

By contributing to the Fusion Mod Catalog, you agree to follow these guidelines and respect the work of other developers.

We appreciate everyone who helps make the Fusion Mod Catalog better.

**Thank you for contributing to Fusion!**
