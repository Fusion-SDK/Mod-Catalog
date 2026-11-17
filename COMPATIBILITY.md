## Fusion and Geode Compatibility

The Fusion Mod Catalog supports two different mod runtimes:

- **Fusion:** Mods designed to run natively through Fusion.
- **Geode:** Mods designed to run through the Geode mod loader.

Although both runtimes support Geometry Dash mods, they are separate environments. A mod built for one runtime does not automatically work on the other.

### Understanding Geode Compatibility

Geode is a mod loader for Geometry Dash. Geode mods are developed to use Geode's APIs and functionality.

A Geode mod generally requires:
- A compatible version of Geometry Dash.
- The Geode loader installed.
- A compatible Geode loader version.
- Any required mod dependencies.

**Listing a mod in the Fusion Mod Catalog does not remove its Geode requirements.** A Geode package still needs Geode to run.

### Geode Version Requirements

Geode mods must declare their Geode compatibility requirements accurately.

Depending on the mod, these can include:

- Whether Geode is required.
- The minimum supported Geode version.
- The maximum supported Geode version, if applicable.

Contributors must not claim compatibility with Geode versions that have not been tested or supported.

### Fusion Compatibility

Fusion-native mods are designed to run through Fusion without requiring Geode.

A Geode mod is not automatically Fusion-compatible. To support Fusion, it must have a separate package specifically built or adapted for Fusion.

A Geode mod that only provides a `.geode` package must remain classified as a Geode mod.

### Dual-Runtime Mods

Some developers may choose to support both runtimes.

A dual-runtime mod can provide:

1. Its original Geode package (`.geode`).
2. A separate Fusion-compatible package (`.zip`).

The catalog supports this through the optional `fusionPackage` information.

The Fusion package must:
- Be a separate, valid download.
- Be compatible with Fusion.
- Have its own valid SHA-256 checksum.
- Be maintained by the mod's developer.
- Be validated before approval.

Providing a Geode package alone is not enough to qualify as dual-runtime support.

### Mod Dependencies and Runtime Compatibility

Dependencies must respect runtime compatibility.

- Fusion mods can depend on other Fusion-compatible mods.
- Fusion mods may depend on a Geode mod only when that mod also provides a valid Fusion-compatible package.
- Geode mods can depend on Geode-compatible mods.
- A Geode-only mod cannot be used as a Fusion dependency.

The catalog checks compatibility information to help prevent invalid dependency relationships.

### Important Compatibility Rules

| Package | Requires Geode? | Runs through Fusion? |
|---|---|---|
| Geode `.geode` package | Yes | No, not by itself |
| Fusion-native package | No | Yes |
| Dual-runtime mod | Only for its Geode package | Yes, using its separate Fusion package |

**Remember:** Runtime compatibility must reflect what the actual package supports. Do not advertise a mod as Fusion-compatible simply because it works with Geode, or advertise Geode compatibility without meeting Geode's requirements.
