# CredoNomics Cyber Solutions

Open-source Windows document productivity and utility suite.

Developed by **CredoNomics Investment Solutions**. Product version **1.2.0**;
Windows build **1.2.0.5**.

[Website](https://credonomics.in) · [Support](mailto:support@credonomics.in) · Phone: 02562455327

## Overview

A Python/PySide6 desktop workspace for local document preparation, printing,
photo layouts and small-business utilities. This repository contains source,
tests and build instructions. It does not distribute executable packages.

## Features

- Print preparation, page selection, rotation, duplex options and multiple pages per sheet.
- Windows WIA scanning, scan imports, automatic edge detection and multi-page PDFs.
- PDF text replacement, annotation, redaction, rotation and local English/Hindi OCR.
- Merge, compress and convert PDF, image, text, Word and Excel documents.
- ID/PVC card layouts, photo sheets, photo/signature sizing and form attachment preparation.
- Image region edits and screen recording with rectangular privacy masks.
- QR generation, ten resume layouts, invoices and UPI request QR codes.
- Existing PDF signature inspection using local trust inputs.

Background-removal weights are not distributed or enabled in the supplied
profile. Original-background photo workflows remain available. PDF compression
can rasterise pages and remove searchable text, links and signatures. Document
edits can invalidate signatures. Review outputs before use.

## Screenshots

Current Windows build; the document shown is synthetic demonstration content.

![Workspace](docs/screenshots/workspace.png)
![PDF editing workflow](docs/screenshots/pdf-editor.png)
![Product and publisher](docs/screenshots/about.png)

The screenshots show the Windows build. The source distribution's first-party
license is AGPL-3.0-only; see [LICENSE](LICENSE).

## Requirements

- Windows 10/11, 64-bit; **Python 3.14**, 64-bit, for the tested setup.
- Internet access to install dependencies; OCR data and licensed UI assets are included.
- A Windows printer/scanner driver for physical-device workflows. Scanner integration uses WIA.
- Optional installed LibreOffice for legacy Office conversions; basic DOCX/XLSX paths are local.

Physical printer/scanner behavior depends on installed drivers and hardware.
Tests use synthetic documents and do not certify physical devices. Windows is
the supported desktop platform; other platforms are not verified.

## Running from Source

In PowerShell at the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\setup-model.ps1 -OcrOnly
.\.venv\Scripts\python.exe main.py
```

The setup script verifies included OCR data against fixed SHA-256 hashes and
downloads missing files from pinned upstream revisions. It does not provision
background-removal weights. `launch.cmd` starts the local source environment.

## Development Setup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Direct dependencies are pinned; [requirements.lock](requirements.lock) records
the tested Windows dependency closure. To reproduce that closure, install it
before `requirements-dev.txt`. No company account, API key or private settings
file is needed. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Tests

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers document/image operations, exports, UI behavior, retention,
failure handling, branding and package policy. CI runs the tests as a blocking
Windows job. Existing lint/type findings are reported separately and are
informational. See [PUBLICATION_MANIFEST.md](PUBLICATION_MANIFEST.md) for the
verified source-export result.

## Windows Build

```powershell
.\build.ps1
```

This runs tests and packages the public source with PyInstaller. The output is
`dist/CredoNomics Cyber Solutions/`. Keep the complete folder together.
It is a new local, unsigned build; bit-for-bit reproduction of another package
is not promised. CI does not automatically publish or sign executables.

See [docs/BUILDING.md](docs/BUILDING.md) for the spec, dependency notices and
optional Microsoft Store packaging. A placeholder package identity is not a
reserved Microsoft Store identity or a certification claim.

## Project Structure

| Path | Purpose |
| --- | --- |
| `main.py`, `store_main.py` | Desktop entry points |
| `cyber/` | Qt UI, processing engines, storage and device integrations |
| `assets/`, `brand/` | Licensed UI assets and product identity |
| `tessdata/` | Unmodified, hash-verified English/Hindi OCR data |
| `tests/` | Synthetic automated regression suite |
| `scripts/`, `packaging/` | Device checks and Windows packaging tools |
| `CredoNomics.spec` | PyInstaller configuration |
| `third-party-licenses/` | Preserved upstream license and notice texts |
| `docs/` | Architecture, build, privacy and screenshot documentation |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component responsibilities.

## Privacy and Offline Operation

Document processing normally uses local libraries. The application stores
settings, counters and saved business records locally and creates temporary
processing files and bounded diagnostics. It does not automatically upload
documents. Website/email controls open external applications. Drivers, network
printers, remote folders and optional converters have their own behavior.
Offline signature inspection cannot establish current revocation status.

See [data handling](docs/legal/DATA-HANDLING.md) for storage, logs and cleanup.
The `CREDONOMICS_DATA_DIR` environment variable selects a different local data
directory. Keep records and backups private.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Use focused pull requests with tests and reproducible verification steps.

## Security

Report vulnerabilities privately to [support@credonomics.in](mailto:support@credonomics.in).
See [SECURITY.md](SECURITY.md). Do not attach private documents or credentials
to public issues.

## License

First-party source is licensed under **GNU Affero General Public License v3.0
only (AGPL-3.0-only)**. See [LICENSE](LICENSE) and
[COPYRIGHT.txt](COPYRIGHT.txt). Third-party components keep their own licenses.
See [TRADEMARKS.md](TRADEMARKS.md) for product identity guidance.

## Third-Party Software

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) identifies material dependencies,
assets, licenses and redistribution scope. The software license does not claim
ownership of supplier libraries, fonts, icons or OCR data.

## Support

**CredoNomics Investment Solutions**

- Website: https://credonomics.in
- Email: [support@credonomics.in](mailto:support@credonomics.in)
- Phone: 02562455327

Copyright © 2026 CredoNomics Investment Solutions.
