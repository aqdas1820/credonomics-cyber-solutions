# SPDX-License-Identifier: AGPL-3.0-only
"""Owned temporary workspaces; never clean arbitrary OS temp or customer output."""
import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from .storage import data_directory
from .diagnostics import record

MAGIC='CredoNomics temporary workspace v1'


def workspace_root():
    root=data_directory()/'temporary-work';root.mkdir(parents=True,exist_ok=True)
    return root.resolve()


@contextmanager
def temporary_workspace():
    with tempfile.TemporaryDirectory(prefix='job-',dir=workspace_root()) as directory:
        (Path(directory)/'OWNER.json').write_text(json.dumps({'magic':MAGIC,'pid':os.getpid()}),encoding='utf-8')
        yield directory


def process_alive(pid):
    if pid<=0:return True
    if sys.platform=='win32':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_uint,ctypes.c_bool,ctypes.c_uint];kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if handle:
            code=ctypes.c_uint(259)
            queried=kernel.GetExitCodeProcess(handle,ctypes.byref(code))
            kernel.CloseHandle(handle)
            return not queried or code.value==259
        return ctypes.get_last_error()!=87
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True


def cleanup_stale_workspaces():
    root=workspace_root();removed=0
    for folder in list(root.iterdir())[:128]:
        try:
            if not folder.name.startswith('job-') or not folder.is_dir() or folder.is_symlink() or getattr(folder,'is_junction',lambda:False)():continue
            resolved=folder.resolve()
            if not resolved.is_relative_to(root) or resolved==root:continue
            marker=folder/'OWNER.json'
            if not marker.is_file() or marker.stat().st_size>512:continue
            owner=json.loads(marker.read_text(encoding='utf-8'))
            if not isinstance(owner,dict) or owner.get('magic')!=MAGIC or type(owner.get('pid')) is not int:continue
            if process_alive(owner['pid']):continue
            shutil.rmtree(resolved);removed+=1
        except (OSError,ValueError):record('temporary_cleanup_deferred')
    if removed:record('stale_temporary_workspaces_removed')
    return removed
