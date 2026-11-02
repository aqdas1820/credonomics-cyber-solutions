# Building on Windows

Use Windows x64 and Python 3.14 x64. Create `.venv` and install
`requirements.lock` followed by `requirements-dev.txt` as shown in the
contribution guide. Run `setup-model.ps1 -OcrOnly` to verify OCR assets.

Run `build.ps1` at the source root. It runs the test suite and invokes
PyInstaller with `CredoNomics.spec`. Outputs go to `dist/` and `build/`.
The default profile uses `store_main.py` and bundles source assets, local
legal documents and dependency notices. Ship the entire output folder,
including `_internal`, when distributing a Windows build.

Changing Python, dependency versions or the build environment can change
output bytes. No reproducible-binary guarantee or code-signing certificate
is supplied. The first-party version configuration is in `brand/brand.json`
and Windows resource metadata is in `assets/version-info.txt`.

## License material

Before distributing a build, preserve full supplier notices and meet the
licenses of the exact dependencies and native libraries included. The
application uses the AGPL route for PyMuPDF/MuPDF. PySide/Qt have their own
module-specific licensing and source/replacement obligations. Source-only
publication does not certify compliance of a separately assembled binary.
Do not remove upstream licenses or restrict the modification/debugging rights
their licenses grant. See `THIRD_PARTY_NOTICES.md`.

## Optional Microsoft Store packaging

`scripts/build_store_msix.py` stages an existing application folder and uses
the Windows SDK `makepri` and `makeappx` tools. Run it with `--help` for
required input paths. `packaging/windows/AppxManifest.template.xml` is the
manifest template; `identity.json` supplies an explicit placeholder identity.

Supply the actual reserved identity and publisher values from your own
Partner Center account in a separate identity file. Never commit account
credentials or signing keys. A package that passes schema validation is not
automatically signed, installable, submitted or certified. This repository's
CI neither signs packages nor publishes binary releases.
