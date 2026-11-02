# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import os
from pathlib import Path

import pytest
import pymupdf as fitz
from PySide6.QtWidgets import QApplication,QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtPrintSupport import QPrinter
from cyber.ui import MainWindow
from cyber.storage import Store
from cyber.catalog import TOOLS
from cyber.engine import execute


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_navigation_preferences_and_solid_surfaces(app,sample):
    store=Store(sample['directory']/'appearance.db')
    store.set('appearance',{'reduce_motion':True})
    window=MainWindow(store)
    window.show()
    app.processEvents()
    window.toggle_sidebar()
    assert window.sidebar.width()==72
    assert window.nav_items['Print'].data(Qt.AccessibleTextRole)=='Print'
    assert store.get('appearance')['compact_menu'] is True
    window.toggle_sidebar()
    assert window.sidebar.width()==232
    dialog=window.create_settings_dialog()
    dialog.appearance_fields['reduce_transparency'].setChecked(True)
    dialog.save_settings()
    assert window.hero_surface.effects is False
    assert window.sidebar.effects is False
    window.resize(1000,760)
    app.processEvents()
    assert window.sidebar.width()==72
    assert not window.menu_toggle.isEnabled()
    window.resize(1480,960)
    app.processEvents()
    assert window.sidebar.width()==232
    window.close()
    reopened=MainWindow(store)
    assert reopened.appearance['reduce_motion'] is True
    assert reopened.sidebar.effects is False
    reopened.close()


def test_sidebar_animation_reaches_target(app,sample):
    window=MainWindow(Store(sample['directory']/'animated-menu.db'))
    window.show()
    app.processEvents()
    window.menu_toggle.click()
    QTest.qWait(280)
    assert window.sidebar.width()==72
    window.menu_toggle.click()
    QTest.qWait(280)
    assert window.sidebar.width()==232
    assert window.menu_toggle.accessibleName()=='Collapse navigation'
    window.close()


def test_all_twenty_workspaces_and_pdf_print(app,sample):
    window=MainWindow(Store(sample['directory']/'gui.db'))
    window.show()
    app.processEvents()
    assert len(TOOLS)==20
    for tool in TOOLS:
        window.select_tool(tool.name)
        app.processEvents()
        assert window.tool_title.text()==tool.name
        assert set(window.fields)=={field.key for field in tool.fields}
    window.select_tool('Print')
    window.add_files([str(sample['pdf'])])
    result=execute('Print',window.inputs(),window.options(),window.store)
    window.show_result(result)
    output=sample['directory']/'printed.pdf'
    printer=QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(output))
    window.paint_pdf(result.data,printer)
    with fitz.open(output) as document:
        assert len(document)==2
    window.close()


def test_file_order_and_restore_forms(app,sample):
    window=MainWindow(Store(sample['directory']/'restore.db'))
    window.select_tool('Merge Tool')
    window.add_files([str(sample['pdf']),str(sample['photo'])])
    window.files.setCurrentRow(1)
    window.move_file(-1)
    assert window.inputs()[0]==str(sample['photo'])
    window.select_tool('Resume Maker')
    window.restore_options({'name':'Test Applicant','design':3,'skills':'Typing'})
    assert window.options()['name']=='Test Applicant'
    assert window.options()['design']==3
    window.close()


def test_preview_pages_and_selection(app,sample):
    window=MainWindow(Store(sample['directory']/'preview.db'))
    window.select_tool('PDF Editor')
    window.add_files([str(sample['pdf'])])
    window.change_page(1)
    assert window.page==1
    window.on_selection([30,30,100,40])
    assert window.fields['box'].text()
    assert window.fields['page'].value()==2
    window.close()
