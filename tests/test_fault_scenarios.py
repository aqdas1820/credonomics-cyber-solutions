# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, synthetic fault scenarios. No physical device or machine policy changes."""
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from threading import Event

import pytest
import pymupdf
from PIL import Image
from PySide6.QtCore import QCoreApplication,QEvent,QThread,Qt
from PySide6.QtGui import QPageSize
from PySide6.QtWidgets import QApplication,QFileDialog
from cyber import documents,images,devices
from cyber.catalog import TOOLS
from cyber.components import icon
from cyber.engine import execute
from cyber.storage import Store
from cyber.limits import raster_page
from test_debug_hardening import window,wait,settle


@pytest.mark.parametrize('payload',[b'',b'not a PDF',b'MZ'+b'\x00'*200,b'%PDF-1.7\ntruncated',b'PK\x03\x04bad archive'])
def test_invalid_document_bytes_fail_without_modifying_input(tmp_path,payload):
    path=tmp_path/'invalid.pdf';path.write_bytes(payload)
    with pytest.raises((ValueError,RuntimeError,OSError)):
        documents.as_pdf(path)
    assert path.read_bytes()==payload


def test_password_protected_pdf_explains_unlock_requirement(tmp_path):
    path=tmp_path/'protected.pdf'
    with pymupdf.open() as doc:
        doc.new_page();doc.save(path,encryption=pymupdf.PDF_ENCRYPT_AES_256,owner_pw='owner-test',user_pw='reader-test')
    original=path.read_bytes()
    with pytest.raises(ValueError,match='password'):documents.as_pdf(path)
    assert path.read_bytes()==original


@pytest.mark.parametrize('mode,format',[('L','PNG'),('CMYK','JPEG'),('RGBA','PNG'),('RGB','JPEG')])
def test_image_modes_and_tiny_inputs_decode_and_export(mode,format):
    image=Image.new(mode,(1,1));stream=io.BytesIO();image.save(stream,format)
    decoded=images.load_image(stream.getvalue())
    assert decoded.mode=='RGB' and decoded.size==(1,1)
    with pymupdf.open(stream=documents.as_pdf(images.image_bytes(decoded)),filetype='pdf') as doc:assert len(doc)==1


def test_exif_orientation_is_applied_once():
    image=Image.new('RGB',(90,40),'white');exif=image.getexif();exif[274]=6
    stream=io.BytesIO();image.save(stream,'JPEG',exif=exif)
    decoded=images.load_image(stream.getvalue());assert decoded.size==(40,90)
    assert images.load_image(images.image_bytes(decoded)).size==(40,90)


@pytest.mark.parametrize('payload',[b'\x89PNG\r\n\x1a\nbroken',b'\xff\xd8\xffinvalid',b'MZnot an image'])
def test_malformed_images_raise_a_controlled_error(payload):
    with pytest.raises((ValueError,OSError)):images.load_image(payload)


def test_huge_pdf_raster_is_rejected_before_allocating_native_bitmap():
    class Rect:width=100000;height=100000
    class Page:
        rect=Rect()
        def get_pixmap(self,**kwargs):raise AssertionError('Unsafe native allocation attempted')
    with pytest.raises(ValueError,match='too large'):raster_page(Page(),dpi=300)


def test_oversized_image_is_rejected_before_full_decode(monkeypatch):
    class Header:
        width=10000;height=10000
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def load(self):raise AssertionError('Oversized image decoded')
    monkeypatch.setattr(Image,'open',lambda *a:Header())
    with pytest.raises(ValueError,match='too large'):images.load_image(b'header')


def test_501_page_pdf_merge_print_and_nup_outputs_reopen(tmp_path):
    with pymupdf.open() as doc:
        for number in range(501):
            page=doc.new_page(width=600 if number%2 else 420,height=420 if number%2 else 600)
            page.insert_text((20,30),f'Page {number+1}')
            if number%3==0:page.set_rotation(90)
        data=doc.tobytes()
    merged=documents.merge_documents([data,data])
    with pymupdf.open(stream=merged,filetype='pdf') as doc:assert len(doc)==1002
    prepared=documents.extract_pages(data,'1,250,501',90)
    with pymupdf.open(stream=prepared,filetype='pdf') as doc:assert len(doc)==3 and 'Page 501' in doc[2].get_text()
    tiled=documents.n_up(data,16)
    with pymupdf.open(stream=tiled,filetype='pdf') as doc:assert len(doc)==32


def test_paper_selection_survives_print_preview_and_device_refresh(window,sample):
    from PySide6.QtPrintSupport import QPrinter
    w,app=window;w.select_tool('Print')
    class Printer:
        def supportedPageSizes(self):return [QPageSize(QPageSize.Letter),QPageSize(QPageSize.A4)]
        def defaultPageSize(self):return QPageSize(QPageSize.Letter)
        def supportedDuplexModes(self):return [QPrinter.DuplexNone]
        def supportedColorModes(self):return [QPrinter.Color,QPrinter.GrayScale]
        def isDefault(self):return True
        def state(self):return QPrinter.Idle
    w.printers={'Synthetic driver':Printer()};w.printer_select.clear();w.printer_select.addItem('Synthetic driver')
    w.paper_select.setCurrentIndex(1);assert w.paper_select.currentData().id()==QPageSize.A4
    w.add_files([str(sample['pdf'])]);w.prepare();wait(w,app)
    assert w.paper_select.currentData().id()==QPageSize.A4
    assert not w.fields['duplex'].isEnabled()


def test_no_printer_disables_submission_but_pdf_export_remains_available(window,sample):
    w,app=window;w.select_tool('Print');w.printers={};w.sync_printer()
    assert not w.run_button.isEnabled()
    w.add_files([str(sample['pdf'])]);w.prepare();wait(w,app)
    assert w.result and w.save_button.isEnabled() and not w.run_button.isEnabled()


@pytest.mark.parametrize('failure',[ValueError('Scanner disconnected'),TimeoutError('Scanner timed out')])
def test_scanner_failure_restores_ui_and_does_not_create_a_page(window,monkeypatch,failure):
    import cyber.ui as ui
    w,app=window;w.select_tool('Scan');w.scan_select.clear();w.scan_select.addItem('Synthetic scanner','test-device');errors=[];w.error=errors.append
    def acquire(*args):raise failure
    monkeypatch.setattr(ui,'scan_page',acquire);w.scan();wait(w,app)
    assert errors and w.files.count()==0 and not w.busy and w.settings_button.isEnabled()


@pytest.mark.parametrize('returncode,output',[(1,b'failure'),(0,b'not JSON')])
def test_scanner_subprocess_failure_is_not_treated_as_success(monkeypatch,returncode,output):
    monkeypatch.setattr(devices.subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a[0],returncode,output,b'failure code'))
    with pytest.raises((ValueError,json.JSONDecodeError)):devices.scanners()


def test_scanner_subprocess_timeout_propagates_to_worker_failure(monkeypatch):
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired(args[0],1)
    monkeypatch.setattr(devices.subprocess,'run',timeout)
    with pytest.raises(subprocess.TimeoutExpired):devices.scanners()


def test_settings_transaction_rolls_back_all_keys(tmp_path):
    store=Store(tmp_path/'transaction.db');store.set_many({'branding':{'company_name':'Before'},'business':{'name':'Before'}})
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_business BEFORE UPDATE ON settings WHEN NEW.key='business' BEGIN SELECT RAISE(ABORT,'fault injection'); END")
    with pytest.raises(sqlite3.IntegrityError):store.set_many({'branding':{'company_name':'After'},'business':{'name':'After'}})
    assert store.get('branding')['company_name']=='Before' and store.get('business')['name']=='Before'


def test_offscreen_saved_window_recovers_to_available_monitor(window):
    from PySide6.QtGui import QGuiApplication
    w,app=window;w.store.set('window',{'x':90000,'y':-90000,'width':40000,'height':40000,'maximized':False})
    w.restore_window();settle(app)
    available=QGuiApplication.primaryScreen().availableGeometry()
    assert available.intersects(w.geometry()) and w.width()<=max(760,available.width()) and w.height()<=max(480,available.height())


def test_diagnostics_omit_document_contents_and_exception_messages(tmp_path):
    from cyber import diagnostics
    folder=diagnostics.configure(tmp_path)
    try:
        raise ValueError('Secret customer name, OCR and C:/private/customer.pdf')
    except ValueError as error:diagnostics.record('fault_probe',tool='PDF Editor',error=error)
    text=(folder/'events.jsonl').read_text()
    assert 'ValueError' in text and 'PDF Editor' in text
    assert 'Secret' not in text and 'customer.pdf' not in text and 'C:/private' not in text
    diagnostics._logger=None


def test_missing_optional_icon_falls_back_without_startup_exception():
    app=QApplication.instance() or QApplication([])
    assert icon('missing-optional-test-icon').isNull()


@pytest.mark.parametrize('query,expected',[('Scan','Scan'),('SCAN','Scan'),('pdf merge','Merge Tool'),('passport','Photo Print'),('e sign','Signature Check'),('jharsewa','Portal PDF Pack')])
def test_operator_search_tokens_and_aliases(window,query,expected):
    w,app=window;w.search.setFocus();w.search.setText(query);settle(app)
    assert w.command_results.currentItem().data(Qt.UserRole)==expected


@pytest.mark.parametrize('query',['','; & ../../','हिन्दी खोज','😀'*100,'x'*10000])
def test_search_fuzz_is_bounded_and_does_not_open_a_tool(window,query):
    w,app=window;w.search.setFocus();w.search.setText(query);settle(app)
    assert w.current is None and w.stack.currentIndex()==0 and w.command_results.count()<=20


def test_worker_callbacks_run_on_gui_thread_and_do_not_accumulate(window):
    w,app=window;w.select_tool('QR Generator');threads=[]
    for _ in range(30):
        w.work(lambda:42,lambda value:threads.append(QThread.currentThread()));wait(w,app)
    assert len(threads)==30 and all(t==app.thread() for t in threads) and not w.workers


def test_output_in_unicode_metacharacter_path_is_real_and_originals_are_unchanged(window,tmp_path,monkeypatch):
    w,app=window;w.select_tool('QR Generator');result=execute('QR Generator',[],w.options(),w.store);w.show_result(result)
    directory=tmp_path/"हिन्दी & files (copy) [1] '";directory.mkdir();path=directory/'QR 😀.png'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),''));w.save()
    assert path.read_bytes()==result.data
    with Image.open(path) as image:assert image.width>0
    assert w.store.get('folders')['export']==str(directory)


def test_destination_removed_after_picker_does_not_report_success(window,tmp_path,monkeypatch):
    w,app=window;w.select_tool('QR Generator');w.show_result(execute('QR Generator',[],w.options(),w.store));errors=[];w.error=errors.append
    directory=tmp_path/'removed';directory.mkdir()
    def choose(*args,**kwargs):directory.rmdir();return str(directory/'output.png'),''
    monkeypatch.setattr(QFileDialog,'getSaveFileName',choose);w.save()
    assert errors and not directory.exists() and w.result_message.title.text()!='Saved successfully'


def test_convert_archive_uses_safe_fixed_member_names(sample):
    import zipfile
    defaults={f.key:f.default for f in next(t for t in TOOLS if t.name=='Convert').fields};defaults['format']='PNG'
    result=execute('Convert',[str(sample['pdf'])],defaults,Store(sample['directory']/'zip.db'))
    with zipfile.ZipFile(io.BytesIO(result.data)) as z:
        assert z.testzip() is None and z.namelist()==['page-001.png','page-002.png']
        for name in z.namelist():
            with Image.open(io.BytesIO(z.read(name))) as image:assert image.width>0


def test_pdf_text_is_never_turned_into_an_excel_formula(tmp_path):
    from openpyxl import load_workbook
    with pymupdf.open() as doc:
        page=doc.new_page();page.insert_text((40,50),'=2+3');data=doc.tobytes()
    defaults={f.key:f.default for f in next(t for t in TOOLS if t.name=='Convert').fields};defaults['format']='Excel'
    result=execute('Convert',[data],defaults,Store(tmp_path/'excel.db'))
    workbook=load_workbook(io.BytesIO(result.data));cell=workbook.active.cell(1,2)
    assert cell.value=='=2+3' and cell.data_type=='s'


def test_owned_temp_cleanup_survives_forced_child_exit_and_keeps_live_work(tmp_path,monkeypatch):
    from cyber.tempfiles import temporary_workspace,cleanup_stale_workspaces,workspace_root
    monkeypatch.setenv('CREDONOMICS_DATA_DIR',str(tmp_path/'state'))
    code="from cyber.tempfiles import temporary_workspace;import os;\nwith temporary_workspace() as d:\n open(d+'/synthetic.tmp','w').write('temporary test');os._exit(0)"
    subprocess.run([sys.executable,'-c',code],check=True,env=os.environ.copy(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert len(list(workspace_root().iterdir()))==1
    output=tmp_path/'customer-output.pdf';output.write_bytes(b'keep output')
    with temporary_workspace() as live:
        assert cleanup_stale_workspaces()==1
        assert Path(live).exists() and output.read_bytes()==b'keep output'
    assert not list(workspace_root().iterdir())


def test_temp_cleanup_ignores_unowned_or_malformed_directories(tmp_path,monkeypatch):
    from cyber.tempfiles import cleanup_stale_workspaces,workspace_root
    monkeypatch.setenv('CREDONOMICS_DATA_DIR',str(tmp_path/'state'))
    root=workspace_root()
    for name,body in [('customer-outputs',{}),('job-bad-marker',{'magic':'other','pid':999999}),('job-invalid-json',None)]:
        folder=root/name;folder.mkdir();(folder/'OWNER.json').write_text(json.dumps(body))
    assert cleanup_stale_workspaces()==0 and len(list(root.iterdir()))==3


def test_input_rejection_does_not_discard_previous_valid_result(window,sample):
    w,app=window;w.select_tool('Photo Print');w.add_files([str(sample['photo'])]);w.prepare();wait(w,app)
    before=w.result;errors=[];w.error=errors.append;w.add_files([str(sample['pdf'])])
    assert errors and w.result is before and len(w.inputs())==1


def test_documents_dropped_on_a_form_tool_are_rejected_clearly(window,sample):
    w,app=window;w.select_tool('QR Generator');errors=[];w.error=errors.append;w.add_files([str(sample['pdf'])])
    assert errors and w.files.count()==0


def test_close_during_work_waits_and_does_not_destroy_worker(window,monkeypatch):
    import cyber.ui as ui
    from PySide6.QtGui import QCloseEvent
    w,app=window;w.select_tool('QR Generator');gate=Event()
    class Notice:
        def __init__(self,*args,**kwargs):pass
        def exec(self):return 0
    monkeypatch.setattr(ui,'Modal',Notice)
    w.work(lambda:gate.wait(1),lambda result:None)
    event=QCloseEvent();w.closeEvent(event)
    assert not event.isAccepted() and w.busy
    gate.set();wait(w,app);assert not w.workers


def test_multiple_rapid_primary_actions_start_one_background_job(window,monkeypatch):
    import cyber.ui as ui
    w,app=window;w.select_tool('QR Generator');gate=Event();calls=[]
    original=ui.execute
    def delayed(*args,**kwargs):calls.append(True);gate.wait(2);return original(*args,**kwargs)
    monkeypatch.setattr(ui,'execute',delayed)
    for _ in range(10):w.primary_action()
    gate.set();wait(w,app)
    assert len(calls)==1 and w.result


@pytest.mark.skipif(sys.platform!='win32',reason='Windows exclusive file-sharing semantics')
def test_locked_output_fails_atomically_and_preserves_existing_bytes(window,tmp_path,monkeypatch):
    import ctypes
    w,app=window;w.select_tool('QR Generator');w.show_result(execute('QR Generator',[],w.options(),w.store))
    path=tmp_path/'locked.png';path.write_bytes(b'previous output');errors=[];w.error=errors.append
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.CreateFileW(str(path),0x80000000,0,None,3,0,None)
    assert handle not in (None,ctypes.c_void_p(-1).value)
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),''))
    try:w.save();assert errors
    finally:kernel.CloseHandle(handle)
    assert path.read_bytes()==b'previous output' and w.result_message.title.text()!='Saved successfully'


def test_core_processing_does_not_need_network_access(sample,monkeypatch):
    import socket
    attempts=[]
    def blocked(*args,**kwargs):attempts.append(True);raise OSError('Network disabled for test')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    store=Store(sample['directory']/'offline.db')
    for name in ('Print','Merge Tool','Compress','Convert','Mini Print','QR Generator','Resume Maker','Bill Maker'):
        tool=next(t for t in TOOLS if t.name==name);options={f.key:f.default for f in tool.fields}
        if name=='Resume Maker':options['name']='Sample Applicant'
        if name=='Bill Maker':options['items']=[{'description':'Service','qty':'1','rate':'5','tax':'0'}]
        if 'design' in options:options['design']=0
        result=execute(name,[] if name in ('QR Generator','Resume Maker','Bill Maker') else [str(sample['pdf'])],options,store)
        assert result.data
    assert not attempts


def test_print_driver_rejection_does_not_report_a_submitted_job(window,sample,monkeypatch):
    import cyber.ui as ui
    from PySide6.QtPrintSupport import QPrinter
    w,app=window
    class Painter:
        def begin(self,*args):return False
    monkeypatch.setattr(ui,'QPainter',Painter)
    printer=QPrinter();printer.setOutputFormat(QPrinter.PdfFormat)
    with pytest.raises(ValueError,match='Could not open'):w.paint_pdf(sample['pdf'].read_bytes(),printer)


def test_qr_extreme_dimensions_and_content_fail_before_large_allocation():
    with pytest.raises(ValueError,match='too large'):images.qr_bytes('hello',size=20000)
    with pytest.raises(ValueError,match='too long'):images.qr_bytes('x'*100000)


def test_print_copies_reject_zero_and_bound_extreme_input(window):
    w,app=window;w.select_tool('Print');w.fields['copies'].setValue(0);assert w.fields['copies'].value()==1
    w.fields['copies'].setValue(20000);assert w.fields['copies'].value()==999
    w.select_tool('Screen Recording');w.fields['fps'].setValue(20000);assert w.fields['fps'].value()==30


def test_output_file_is_saved_even_when_local_history_cannot_be_written(window,tmp_path,monkeypatch):
    w,app=window;w.select_tool('Resume Maker');w.fields['name'].setText('Sample Applicant');w.prepare();wait(w,app)
    path=tmp_path/'resume.pdf';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),''))
    def reject(*args):raise sqlite3.OperationalError('readonly database')
    monkeypatch.setattr(w.store,'save_record',reject);w.save()
    with pymupdf.open(path) as doc:assert 'Sample Applicant' in doc[0].get_text()
    assert w.result_message.title.text()=='File saved; history unavailable'


def test_settings_save_to_readonly_database_preserves_previous_values(window,monkeypatch):
    import cyber.views as views
    w,app=window;w.store.set('branding',{'company_name':'Before'})
    d=w.create_settings_dialog();d.brand_fields['company_name'].setText('After');messages=[]
    class Notice:
        def __init__(self,*args,**kwargs):messages.append(args[1])
        def exec(self):return 0
    monkeypatch.setattr(views,'Modal',Notice)
    original=w.store.connect
    w.store.connect=lambda:sqlite3.connect(w.store.path.as_uri()+'?mode=ro',uri=True)
    try:d.save_settings();assert messages and w.store.get('branding')['company_name']=='Before'
    finally:w.store.connect=original;d.close()


def test_damaged_saved_record_does_not_hide_unrelated_valid_records(tmp_path):
    store=Store(tmp_path/'history.db');store.save_record('resume','123','Valid',{'name':'Sample Applicant'})
    bad=store.save_record('resume','456','Damaged',{})
    with store.connect() as db:db.execute('UPDATE records SET body=? WHERE id=?',('{broken',bad))
    rows=store.records('resume')
    assert len(rows)==2 and next(r for r in rows if r['title']=='Valid')['body']['name']=='Sample Applicant'
    assert next(r for r in rows if r['id']==bad)['corrupt'] is True


def test_malformed_history_field_values_are_not_applied_to_widgets(window):
    w,app=window;w.select_tool('Resume Maker')
    assert w.restore_options({'name':'Keep valid text','design':{'bad':True}}) is False
    assert w.fields['design'].currentIndex()==0


@pytest.mark.parametrize('payload',['null','[]','false'])
def test_malformed_build_marker_fails_closed_without_a_type_error(tmp_path,monkeypatch,payload):
    from cyber import distribution
    (tmp_path/'COMMERCIAL-PROFILE.json').write_text(payload)
    monkeypatch.setattr(distribution.sys,'_MEIPASS',str(tmp_path),raising=False)
    assert distribution.build_profile()=='restricted'


@pytest.mark.parametrize('kind',['about','support','settings','legal','notice'])
def test_closed_transient_dialogs_release_their_owned_widgets(window,kind):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog
    from cyber.legal import about_dialog,support_dialog,document_dialog
    from cyber.components import Modal
    w,app=window
    for _ in range(5):
        factories={'about':lambda:about_dialog(w),'support':lambda:support_dialog(w),'settings':w.create_settings_dialog,'legal':lambda:document_dialog(w,'Privacy','docs/legal/DATA-HANDLING.md'),'notice':lambda:Modal(w,'Test notice','Synthetic diagnostic message')}
        d=factories[kind]()
        QTimer.singleShot(10,lambda:app.activeModalWidget().reject())
        d.exec();settle(app)
    assert not w.findChildren(QDialog)


@pytest.mark.parametrize('tool',['Photo Print','PDF Editor','Signature Check'])
def test_single_document_tools_cannot_silently_ignore_a_second_input(window,sample,tool):
    w,app=window;w.select_tool(tool);path=str(sample['photo'] if tool=='Photo Print' else sample['pdf']);w.add_files([path])
    errors=[];w.error=errors.append;w.add_files([path])
    assert errors and len(w.inputs())==1


def test_database_transaction_closes_its_file_handle_without_waiting_for_gc(tmp_path):
    store=Store(tmp_path/'connections.db')
    with store.connect() as db:db.execute('SELECT 1').fetchone()
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):
        db.execute('SELECT 1')


def test_sidebar_resize_after_animation_never_reuses_a_deleted_animation(window):
    w,app=window;w.resize(1480,960);w.appearance['reduce_motion']=False
    w._sidebar_collapsed=True;w.update_sidebar(animated=True);settle(app)
    w._sidebar_collapsed=False;w.update_sidebar(animated=False);settle(app)
    w._sidebar_collapsed=True;w.update_sidebar(animated=False);settle(app)
    assert w.sidebar.width()==72


def test_current_page_print_uses_selected_document_in_a_multi_file_queue(request, sample, tmp_path):
    second = tmp_path / "second.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 50), "Second document selected")
        doc.save(second)
    w, app = request.getfixturevalue("window")
    w.select_tool("Print")
    w.add_files([str(sample["pdf"]), str(second)])
    w.files.setCurrentRow(1)
    w.page_scope.setCurrentText("Current page")
    w.prepare()
    wait(w, app)
    with pymupdf.open(stream=w.result.data, filetype="pdf") as output:
        assert len(output) == 1 and "Second document selected" in output[0].get_text()
