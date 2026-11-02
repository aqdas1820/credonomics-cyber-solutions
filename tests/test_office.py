# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
from pathlib import Path
import pymupdf as fitz
from docx import Document
from openpyxl import Workbook
from cyber.documents import office_pdf


def test_office_word_and_excel_conversion(tmp_path):
    document=Document()
    document.add_heading('CredoNomics Word conversion',0)
    document.add_paragraph('Offline conversion test.')
    source=tmp_path/'sample.docx'
    document.save(source)
    result=office_pdf(source)
    with fitz.open(stream=result,filetype='pdf') as pdf:
        assert 'CredoNomics Word conversion' in pdf[0].get_text()
    workbook=Workbook()
    workbook.active.append(['CredoNomics Excel conversion','Amount'])
    workbook.active.append(['Print',25])
    source=tmp_path/'sample.xlsx'
    workbook.save(source)
    result=office_pdf(source)
    with fitz.open(stream=result,filetype='pdf') as pdf:
        assert 'CredoNomics Excel conversion' in pdf[0].get_text()
