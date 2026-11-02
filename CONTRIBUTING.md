# Contributing

Use Windows 10/11 x64 with Python 3.14 x64 for the supported environment.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\setup-model.ps1 -OcrOnly
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest -q
```

Create a topic branch and keep each pull request focused on one change. Explain
the problem, resulting behavior and validation. Add meaningful regression
coverage for bugs; use synthetic inputs and temporary directories. Include
screenshots for visible UI changes, with no private documents or local paths.
Never commit generated packages, credentials, signing keys or user databases.

Follow nearby Python/Qt conventions, preserve accessibility labels, handle
failures without overwriting originals, and avoid unrequested network traffic.
Keep version/contact values in the existing brand configuration. Preserve
upstream notices and document added dependencies and asset rights.

Run `python -m ruff check .`, `python -m ruff format --check .` and
`python -m mypy cyber tests scripts` from the development environment to review
static findings. These checks currently report existing debt; CI treats them
as informational. Automated tests remain blocking. Avoid unrelated formatting
changes in a functional fix.

By submitting original contributions, you agree to license them under this
project's AGPL-3.0-only license. Only submit material you have permission to
contribute; identify third-party code and its original license. No copyright
assignment is required by this contribution guide.

Report security issues privately to support@credonomics.in as described in
[SECURITY.md](SECURITY.md). Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
