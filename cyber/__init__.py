# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import json
import sys
from pathlib import Path

_root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
BRAND_CONFIG=json.loads((_root/'brand/brand.json').read_text(encoding='utf-8'))
__version__=BRAND_CONFIG['version']
FILE_VERSION=BRAND_CONFIG['file_version']
BRAND=BRAND_CONFIG['product_name']
PUBLISHER=BRAND_CONFIG['publisher_name']
COPYRIGHT=BRAND_CONFIG['copyright']
COPYRIGHT_SHORT=COPYRIGHT.removeprefix('Copyright ').removesuffix('. All rights reserved.')
WEBSITE=BRAND_CONFIG['website']
SUPPORT_EMAIL=BRAND_CONFIG['support_email']
SUPPORT_PHONE=BRAND_CONFIG['support_phone']
