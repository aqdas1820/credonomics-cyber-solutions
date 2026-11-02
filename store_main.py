# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Production desktop entry point; no development capture/test modes."""
if __name__=='__main__':
    from cyber.ui import main
    raise SystemExit(main())
