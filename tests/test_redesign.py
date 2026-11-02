# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import pytest
import time
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QScrollArea
from cyber.ui import MainWindow
from cyber.catalog import TOOLS
from cyber.storage import Store
from cyber.engine import execute
from cyber.components import FileDropZone


@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    w=MainWindow(Store(tmp_path/'redesign.db'))
    w.show()
    app.processEvents()
    yield w,app
    w.close()
    app.processEvents()


def test_search_keyboard_launch_and_grouped_navigation(window):
    w,app=window
    assert len(w.nav_items)==20
    assert len(w.nav_groups)==4
    assert all(item.data(Qt.AccessibleTextRole)==name for name,item in w.nav_items.items())
    w.search.setFocus()
    QTest.keyClicks(w.search,'photo')
    app.processEvents()
    assert w.command_results.count()>=2
    QTest.keyClick(w.search,Qt.Key_Down)
    selected=w.command_results.currentItem().data(Qt.UserRole)
    QTest.keyClick(w.search,Qt.Key_Return)
    assert w.current.name==selected
    assert not w.command_results.isVisible()


@pytest.mark.parametrize('size',[(1480,960),(1280,800),(1024,768),(860,620)])
def test_every_tool_resizes_without_horizontal_scroll(window,size):
    w,app=window
    w.resize(*size)
    app.processEvents()
    for tool in TOOLS:
        w.select_tool(tool.name)
        app.processEvents()
        assert w.width()==size[0]
        assert w.run_button.geometry().right()<=w.work_page.width()
        for area in (w.home_page,w.form_scroll):
            assert area.horizontalScrollBar().maximum()==0,(size,tool.name)
        assert w.preview_card.width()>=240,(size,tool.name)


def test_file_order_and_removal_invalidate_old_results(window,sample):
    w,app=window
    w.select_tool('Merge Tool')
    w.add_files([str(sample['pdf']),str(sample['photo'])])
    w.show_result(execute('Merge Tool',w.inputs(),w.options(),w.store))
    assert w.save_button.isEnabled()
    w.files.setCurrentRow(1)
    w.move_file(-1)
    assert w.result is None
    assert not w.save_button.isEnabled()
    w.files.selectAll()
    w.remove_files()
    assert w.inputs()==[]
    assert w.preview_data is None
    assert not w.canvas.isVisible()


def test_branding_save_preserves_business_configuration(window):
    w,app=window
    w.store.set('business',{'name':'Existing shop','upi':'shop@upi','custom_rate':5})
    dialog=w.create_settings_dialog()
    dialog.brand_fields['product_name'].setText('CreDo Suite')
    dialog.brand_fields['company_name'].setText('CredoNomics')
    dialog.brand_fields['accent'].setText('#1c607d')
    dialog.save_settings()
    from cyber.distribution import is_store_build
    from cyber import BRAND
    assert w.windowTitle()==BRAND
    assert w.store.get('business')['upi']=='shop@upi'
    assert w.store.get('business')['custom_rate']==5
    assert w.store.get('branding')['accent']=='#1c607d'


def test_printer_capabilities_are_from_driver(window):
    w,app=window
    w.select_tool('Print')
    info=w.printers.get(w.printer_select.currentText())
    if info:
        reported={size.name() for size in info.supportedPageSizes()}
        assert {w.paper_select.itemText(i) for i in range(w.paper_select.count())}==reported if reported else not w.paper_select.isEnabled()
    else:
        assert not w.run_button.isEnabled()
    w.select_tool('Scan')
    assert not w.scan_button.isEnabled()
    assert w.scan_select.currentData() is None


def test_compact_file_manager_is_expandable(window,sample):
    w,app=window
    w.resize(860,620)
    w.select_tool('Print')
    app.processEvents()
    w.add_files([str(sample['pdf'])])
    assert not w.file_panel.isVisible()
    assert '1 document' in w.compact_files_button.text()
    w.compact_files_button.click()
    assert w.file_panel.isVisible()
    assert w.inputs()==[str(sample['pdf'])]


def test_file_drop_keeps_local_file_handling(window,sample):
    from PySide6.QtCore import QMimeData,QUrl,QPointF
    from PySide6.QtGui import QDropEvent
    w,app=window
    w.select_tool('Merge Tool')
    mime=QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(sample['pdf'])),QUrl('https://example.com/remote.pdf')])
    event=QDropEvent(QPointF(20,20),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
    w.file_panel.findChild(FileDropZone).dropEvent(event)
    assert [Path(value).resolve() for value in w.inputs()]==[sample['pdf'].resolve()]


def test_disconnected_scan_feedback_and_busy_cleanup(window,monkeypatch):
    w,app=window
    monkeypatch.setattr('cyber.ui.scanners',lambda:[])
    w.select_tool('Scan')
    w.find_scanners()
    deadline=time.monotonic()+5
    while (w.busy or w.workers) and time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.01)
    assert not w.busy
    assert not w.scan_button.isEnabled()
    assert w.result_message.state=='warning'
    assert 'Ready' in w.statusBar().currentMessage()


def test_primary_print_prepares_before_opening_driver_dialog(window,sample,monkeypatch):
    w,app=window
    w.select_tool('Print')
    w.add_files([str(sample['pdf'])])
    opened=[]
    monkeypatch.setattr(w,'print_result',lambda:opened.append(w.result.data.startswith(b'%PDF')))
    w.primary_action()
    deadline=time.monotonic()+5
    while (w.busy or w.workers) and time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.01)
    assert opened==[True]
    assert w.result is not None
    # Changing the page selection after preview must not print the cached two-page result.
    w.fields['pages'].setText('2')
    page_counts=[]
    import pymupdf
    def inspect_print():
        with pymupdf.open(stream=w.result.data,filetype='pdf') as document:
            page_counts.append(len(document))
    monkeypatch.setattr(w,'print_result',inspect_print)
    w.primary_action()
    deadline=time.monotonic()+5
    while (w.busy or w.workers) and time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.01)
    assert page_counts==[1]
