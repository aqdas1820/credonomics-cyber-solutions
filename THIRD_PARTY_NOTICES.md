# Third-party software and assets

First-party CredoNomics code is AGPL-3.0-only. CredoNomics Investment Solutions
does not claim ownership of the components below. Their original copyrights,
licenses, disclaimers and notices remain in effect.

This is a **source-only repository**: it includes first-party Python, fonts,
icons, OCR data and preserved license texts. Python wheels, native libraries,
Windows components and build tools are installed separately. No EXE, DLL,
installer or dependency implementation is distributed here. Merely retaining
a supplier notice does not mean that supplier's implementation is bundled.

## Material dependencies

| Component | Tested version | Role and license |
| --- | --- | --- |
| Python | 3.14.7 | Interpreter installed separately; PSF and standard-library third-party terms |
| PySide6 Essentials / Addons, Shiboken6 / Qt | 6.12.0 | Desktop UI, printing and SVG; module-specific LGPL-3.0/GPL alternatives or separately acquired commercial terms |
| PyMuPDF / MuPDF | 2.0 / 1.28.5 | PDF processing and embedded OCR; upstream AGPL route used by this open-source application |
| Pillow | 13.0.0 | Image processing; MIT-CMU and included vendor notices |
| OpenCV headless | 5.0.0.93 | Image operations and recording; Apache-2.0 plus native third-party terms |
| NumPy | 2.5.4 | Numeric arrays; BSD-3-Clause and bundled permissive component terms |
| qrcode | 8.2 | QR generation; BSD |
| python-docx | 1.2.0 | Word documents; MIT |
| openpyxl | 3.1.5 | Excel documents; MIT |
| ReportLab | 5.1.0 | Document layouts; BSD and included font/component terms |
| mss | 10.2.0 | Screen capture; MIT |
| pyHanko / pyhanko-certvalidator | 0.38.0 / 0.33.0 | Signature inspection; MIT and preserved component notices |
| cryptography | 50.0.2 | Cryptographic primitives; Apache-2.0 OR BSD-3-Clause plus supplier terms |
| ONNX Runtime | 1.31.1 | Optional inference code path; MIT and included third-party terms; no model weights are supplied or enabled |
| PyInstaller | 6.22.3 | Build tool; GPL with upstream bootloader distribution exception |
| PyInstaller hooks | 2026.9 | Build hooks; Apache/GPL terms as documented upstream |
| pytest / Ruff / mypy | 9.2.0 / 0.17.3 / 2.4.1 | Development tools; MIT and their included notices |

The complete tested Windows environment is pinned in `requirements.lock`.
Its transitive dependencies retain their own licenses, including MIT, BSD,
Apache, PSF and MPL components. A reviewed, versioned inventory is in
[docs/DEPENDENCIES.md](docs/DEPENDENCIES.md). The tiny `pymupdf_layout` and
`pymupdf4llm` 2.0 compatibility distributions installed transitively contain
metadata rather than implementation code; no separate implementation from
them is copied into this repository. PyMuPDF's upstream projects document
their AGPL/commercial licensing at https://pymupdf.io/licensing and
https://github.com/pymupdf.

## Included fonts, icons and OCR data

| Material | Redistribution scope | Attribution and terms |
| --- | --- | --- |
| Lato Regular and Bold | Unmodified font files in `assets/fonts/` | Lato authors; SIL OFL-1.1, including reserved-name terms, in `assets/fonts/OFL.txt`; https://github.com/google/fonts/tree/main/ofl/lato |
| Lucide / Feather-derived icons | SVG source in `assets/icons/`; some color variants modified | Lucide Icons and Contributors, Cole Bemis; original ISC/MIT texts in `assets/icons/LICENSE`; https://github.com/lucide-icons/lucide |
| Tesseract fast English and Hindi | Unmodified `tessdata/*.traineddata` data | Tesseract project/data contributors; Apache-2.0, full text in `third-party-licenses/complete-texts/Tessdata-Apache-2.0.txt`; https://github.com/tesseract-ocr/tessdata_fast |

OCR source revisions and expected hashes are pinned in `setup-model.ps1`.
English: `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
Hindi: `4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825`.
These data files are needed by local OCR and its regression tests. They are
not a claim of ownership over upstream training data. No background-removal
model is included.

## Complete texts and binary distribution

Full available upstream texts are retained unmodified in
`third-party-licenses/`. Some vendor texts discuss optional components absent
from this source distribution. Preserve those texts rather than editing
upstream authorship or licensing statements. The original font/icon notices
are also alongside the assets.

When assembling a binary distribution, review the **actual** wheel/native
payload and fulfill applicable source, attribution, notice and library
replacement obligations. Qt module terms and embedded PDF/image/crypto/font
components cannot be replaced by a top-level package license summary.
The PyInstaller exception applies as upstream defines it; it does not change
other libraries' licenses. This source publication supplies no commercial
dependency license or Microsoft component redistribution grant.

Qt licensing: https://doc.qt.io/qt-6/licensing.html and
https://www.qt.io/development/open-source-lgpl-obligations.

Windows APIs, installed fonts, printer/scanner drivers and optional installed
LibreOffice are external software, not CredoNomics-owned or bundled source.
