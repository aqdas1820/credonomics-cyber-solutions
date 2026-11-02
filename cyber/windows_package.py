# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Read Windows package identity without adding a Windows runtime dependency."""
import sys


def package_family_name():
    if sys.platform!='win32':
        return None
    import ctypes
    function=ctypes.WinDLL('kernel32').GetCurrentPackageFamilyName
    function.argtypes=[ctypes.POINTER(ctypes.c_uint),ctypes.c_wchar_p]
    function.restype=ctypes.c_long
    length=ctypes.c_uint(0)
    result=function(ctypes.byref(length),None)
    if result!=122: # ERROR_INSUFFICIENT_BUFFER; unpackaged returns 15700.
        return None
    buffer=ctypes.create_unicode_buffer(length.value)
    return buffer.value if function(ctypes.byref(length),buffer)==0 else None
