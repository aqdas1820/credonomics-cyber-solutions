# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import subprocess
from unittest.mock import Mock
import pytest
from cyber import documents


def test_converter_timeout_terminates_owned_tree(monkeypatch,tmp_path):
    monkeypatch.setenv('CREDONOMICS_OFFICE_BINARY',str(tmp_path/'soffice.exe'))
    fake=Mock()
    fake.pid=98765
    fake.communicate.side_effect=[subprocess.TimeoutExpired('soffice',60),(b'',b'')]
    monkeypatch.setattr(documents.subprocess,'Popen',Mock(return_value=fake))
    terminate=Mock()
    monkeypatch.setattr(documents.subprocess,'run',terminate)
    with pytest.raises(ValueError,match='timed out'):
        documents.office_pdf(tmp_path/'document.docx')
    if __import__('sys').platform=='win32':
        assert terminate.call_args.args[0]==['taskkill','/PID','98765','/T','/F']
