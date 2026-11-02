# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cyber.devices import scanners
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinterInfo
app=QApplication([])
result={'printers':[p.printerName() for p in QPrinterInfo.availablePrinters()]}
try:
    result['scanners']=scanners()
except Exception as error:
    result['scanner_diagnostic']=str(error)
path=Path(__file__).resolve().parents[1]/'artifacts/device-check.json'
path.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
