# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import base64
import hashlib
import json
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization


def machine_id():
    identity=platform.node()+str(uuid.getnode())
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography') as key:
            identity=winreg.QueryValueEx(key,'MachineGuid')[0]
    except (ImportError,OSError):
        pass
    return hashlib.sha256(('CredoNomics:'+identity).encode()).hexdigest()[:24].upper()


def canonical(payload):
    return json.dumps(payload,sort_keys=True,separators=(',',':')).encode()


def verify_license(envelope,public_key,device=None):
    key=serialization.load_pem_public_key(Path(public_key).read_bytes())
    payload=envelope['payload']
    key.verify(base64.b64decode(envelope['signature'],validate=True),canonical(payload))
    if payload.get('product')!='CredoNomics Cyber Solutions':
        raise ValueError('This licence is for a different product.')
    if payload.get('machine_id')!=(device or machine_id()):
        raise ValueError('This licence was issued to another PC.')
    if payload.get('expires') and datetime.fromisoformat(payload['expires']).replace(tzinfo=timezone.utc)<datetime.now(timezone.utc):
        raise ValueError('This licence has expired.')
    return payload
