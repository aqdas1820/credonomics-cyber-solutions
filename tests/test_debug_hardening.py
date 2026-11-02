# SPDX-License-Identifier: AGPL-3.0-only
import io
import json
import time
from decimal import DecimalException
from pathlib import Path
from threading import Event

import pytest
import pymupdf
from PIL import Image
from PySide6.QtCore import Qt,QCoreApplication,QEvent,QTimer
from PySide6.QtWidgets import QApplication,QDialog,QFileDialog,QScrollArea
from cyber.ui import MainWindow
from cyber.storage import Store
from cyber.business import invoice_totals
from cyber.engine import rectangle,execute


@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    w=MainWindow(Store(tmp_path/'debug.db'));w.show();app.processEvents()
    yield w,app
    w.close();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


def settle(app):
    for _ in range(12):app.processEvents();time.sleep(.002)
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


def wait(w,app):
    until=time.monotonic()+8
    while w.busy or w.workers:
        settle(app);assert time.monotonic()<until


@pytest.mark.parametrize('key,raw',[('appearance','{broken'),('appearance','null'),('appearance','"wrong"'),('branding','[1,2]'),('business','false')])
def test_corrupt_settings_fall_back_without_losing_unrelated_values(tmp_path,key,raw):
    store=Store(tmp_path/'settings.db');store.set('unrelated',{'keep':42})
    with store.connect() as db:db.execute('INSERT INTO settings VALUES(?,?)',(key,raw))
    assert store.get(key,{})=={}
    assert store.get('unrelated')=={'keep':42}
    app=QApplication.instance() or QApplication([])
    w=MainWindow(store);w.show();app.processEvents();w.close();w.deleteLater()


def test_wrong_setting_field_types_do_not_crash_settings_or_startup(tmp_path):
    app=QApplication.instance() or QApplication([]);store=Store(tmp_path/'typed.db')
    store.set('branding',{'logo':123,'accent':{'invalid':True},'company_name':False})
    store.set('business',{'name':123,'logo':[],'upi':None})
    store.set('appearance',{'theme':['bad'],'compact_menu':'false','reduce_motion':{}})
    w=MainWindow(store);w.show();app.processEvents()
    d=w.create_settings_dialog();assert d.theme_select.currentText()=='Light';d.close()
    assert store.get('business',{}).get('name','')==''
    w.close();w.deleteLater()


def test_print_paper_labels_cannot_force_horizontal_overflow_after_theme_changes(window):
    w,app=window;w.resize(911,512)
    for mode in ('Light','Dark','High contrast','Light'):
        w.appearance['theme']=mode;w.apply_branding();w.select_tool('Print')
        w.paper_select.addItem('A driver paper name that is much longer than the available settings panel')
        settle(app)
        assert all(a.horizontalScrollBar().maximum()==0 for a in w.findChildren(QScrollArea) if a.isVisible())


def test_sidebar_animation_objects_are_bounded(window):
    from PySide6.QtCore import QVariantAnimation
    w,app=window;w.resize(1480,960);w.appearance['reduce_motion']=False
    before=len(w.findChildren(QVariantAnimation))
    for _ in range(30):w.toggle_sidebar();settle(app)
    assert len(w.findChildren(QVariantAnimation))<=before+1


def test_double_print_click_does_not_reenter_native_dialog(window,sample,monkeypatch):
    import cyber.ui as ui
    w,app=window;w.select_tool('Print');w.add_files([str(sample['pdf'])]);w.prepare();wait(w,app)
    calls=[]
    class Dialog:
        def __init__(self,*args):pass
        def deleteLater(self):pass
        def exec(self):
            calls.append(True)
            if len(calls)==1:w.print_result()
            return QDialog.Rejected
    monkeypatch.setattr(ui,'QPrintDialog',Dialog)
    w.print_result();assert len(calls)==1


def test_cancelled_or_failed_reprepare_cannot_export_an_old_result(window,sample):
    w,app=window;w.select_tool('Print');w.add_files([str(sample['pdf'])]);w.prepare();wait(w,app)
    assert w.result and w.save_button.isEnabled()
    errors=[];w.error=errors.append;w.page_scope.setCurrentText('Custom range');w.fields['pages'].setText('9999')
    w.prepare();wait(w,app)
    assert errors and w.result is None and not w.save_button.isEnabled()


@pytest.mark.parametrize('text',['nan,0,2,2','0,0,inf,2','0,0,2,nan','1e309,0,2,2'])
def test_nonfinite_rectangle_is_rejected_before_native_processing(text):
    with pytest.raises(ValueError,match='Rectangle'):rectangle(text)


def test_invoice_extreme_numbers_report_validation_instead_of_decimal_exception():
    with pytest.raises(ValueError,match='large'):
        invoice_totals([{'description':'Service','qty':'1e100','rate':'1e100','tax':'5'}])


def test_busy_shortcuts_cannot_save_or_open_a_second_job(window,monkeypatch):
    w,app=window;w.select_tool('QR Generator');w.show_result(execute('QR Generator',[],w.options(),w.store))
    picked=[];monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:picked.append(True) or ('',''))
    gate=Event();w.work(lambda:gate.wait(1),lambda x:None)
    try:w.save();assert not picked
    finally:gate.set();wait(w,app)


def test_native_file_picker_is_not_reentrant(window,monkeypatch):
    w,app=window;w.select_tool('Print');calls=[]
    def choose(*args,**kwargs):
        calls.append(True)
        if len(calls)==1:w.open_files()
        return [],''
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',choose)
    w.open_files();assert len(calls)==1


def test_deleted_input_file_does_not_leave_old_preview_or_page_state(window,sample):
    w,app=window;w.select_tool('Print');w.add_files([str(sample['pdf'])]);assert w.preview_data
    sample['pdf'].unlink();w.preview_input()
    assert w.preview_data is None and w.page_count==0 and not w.preview_toolbar.isVisible()


def test_recording_stop_failure_restores_controls_and_releases_timer(window,monkeypatch):
    w,app=window;w.select_tool('Screen Recording');errors=[];w.error=errors.append
    class Recorder:
        running=True
        def stop(self):self.running=False;raise ValueError('Capture device became unavailable.')
    w.recorder=Recorder();w.nav.setEnabled(False);w.form_scroll.setEnabled(False);w.reset_button.setEnabled(False)
    w.record_timer=QTimer(w);w.record_timer.start(500);w.toggle_recording();settle(app)
    assert errors and w.nav.isEnabled() and w.form_scroll.isEnabled() and w.reset_button.isEnabled()
    assert w.record_timer is None


def test_huge_pdf_thumbnail_is_bounded_without_rasterising_the_page_at_full_scale(window,tmp_path):
    w,app=window;doc=pymupdf.open();doc.new_page(width=10000,height=10000)
    data=doc.tobytes();doc.close();w.select_tool('Print');w.show_data(data,'large dimensions.pdf')
    assert w.thumbnails.count()==1
    size=w.thumbnails.item(0).icon().availableSizes()[0]
    assert max(size.width(),size.height())<=100


def test_failed_output_write_keeps_existing_file_and_does_not_report_success(window,tmp_path,monkeypatch):
    import cyber.ui as ui
    w,app=window;w.select_tool('QR Generator');w.show_result(execute('QR Generator',[],w.options(),w.store))
    target=tmp_path/'existing.png';target.write_bytes(b'keep previous output');errors=[];w.error=errors.append
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(target),''))
    class FullDisk:
        def __init__(self,*args):pass
        def open(self,*args):return True
        def write(self,*args):return 1
        def cancelWriting(self):pass
        def errorString(self):return 'Disk full'
    monkeypatch.setattr(ui,'QSaveFile',FullDisk);w.save()
    assert errors and target.read_bytes()==b'keep previous output'
    assert w.result_message.title.text()!='Saved successfully'
