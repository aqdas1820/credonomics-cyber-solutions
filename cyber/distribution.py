# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Distribution availability policy, separate from operator branding.

Frozen packages fail closed if the build marker is missing or malformed.
The commercial investigation build has no approved background model.
"""
import json
import sys
from pathlib import Path

MODEL_UNAVAILABLE='AI background removal is unavailable in this candidate: no model with verified redistribution rights is included. Original-background photo layouts remain available.'


def build_profile():
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    marker=root/'COMMERCIAL-PROFILE.json'
    if not marker.exists():
        return 'restricted' if getattr(sys,'frozen',False) else 'development'
    try:
        value=json.loads(marker.read_text(encoding='utf-8'))['profile']
    except (ValueError,KeyError,TypeError,OSError):
        return 'restricted'
    return value if value in ('development','commercial-clearance','store-submission') else 'restricted'


def is_commercial_build():
    return build_profile()!='development'


def is_store_build():
    return build_profile()=='store-submission'
