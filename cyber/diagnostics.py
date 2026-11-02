# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded local diagnostics containing event codes, never document data."""
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime,timezone

_logger=None


def directory():
    if _logger and _logger.handlers:return Path(_logger.handlers[0].baseFilename).parent
    return None


def configure(directory):
    global _logger
    logger=logging.getLogger('credonomics.local')
    logger.setLevel(logging.INFO);logger.propagate=False
    for handler in list(logger.handlers):handler.close();logger.removeHandler(handler)
    try:
        folder=Path(directory)/'diagnostics';folder.mkdir(parents=True,exist_ok=True)
        handler=RotatingFileHandler(folder/'events.jsonl',maxBytes=512*1024,backupCount=2,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'));logger.addHandler(handler)
    except OSError:
        _logger=None;return None
    _logger=logger
    return folder


def record(event,*,tool=None,error=None):
    if _logger is None:return
    from . import __version__,FILE_VERSION
    row={'utc':datetime.now(timezone.utc).isoformat(),'event':event,'version':__version__,'build':FILE_VERSION}
    if tool:
        from .catalog import BY_NAME
        if tool in BY_NAME:row['tool']=tool
    if error is not None:
        row['error_type']=type(error).__name__
        trace=[];tb=error.__traceback__
        while tb and len(trace)<12:
            filename=Path(tb.tb_frame.f_code.co_filename).name
            trace.append({'module':filename,'function':tb.tb_frame.f_code.co_name,'line':tb.tb_lineno})
            tb=tb.tb_next
        if trace:row['frames']=trace
    # No exception message, paths, field values, OCR, previews or traceback locals.
    _logger.info(json.dumps(row,ensure_ascii=True))
