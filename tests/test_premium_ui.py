# SPDX-License-Identifier: AGPL-3.0-only
import io
import time
from threading import Event
import pytest
import pymupdf
from PIL import Image
from PySide6.QtCore import Qt,QRect
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from cyber.ui import MainWindow
from cyber.storage import Store
from cyber.theme import tokens
from cyber.components import fit_dialog
from cyber.legal import about_dialog


@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    w=MainWindow(Store(tmp_path/'premium.db'));w.show();app.processEvents()
    yield w,app
    w.close();app.processEvents()


def wait(w,app):
    deadline=time.monotonic()+8
    while (w.busy or w.workers) and time.monotonic()<deadline:
        app.processEvents();time.sleep(.005)
    assert not w.busy and not w.workers


@pytest.mark.parametrize('mode',['Light','Dark','High contrast'])
def test_readable_semantic_text_and_feedback(mode):
    def lum(c):
        rgb=[int(c[i:i+2],16)/255 for i in (1,3,5)]
        return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip((.2126,.7152,.0722),rgb))
    palette=tokens(mode=mode)
    for foreground,background in [('text','surface'),('secondary','surface'),('sidebar_muted','sidebar'),('success','success_soft'),('warning','warning_soft'),('error','error_soft')]:
        a,b=sorted((lum(palette[foreground]),lum(palette[background])))
        assert (b+.05)/(a+.05)>=4.5,(mode,foreground,background)


def test_search_is_stable_and_supports_existing_tool_aliases(window):
    w,app=window
    before=[card.geometry() for _,card in w.cards]
    w.search.setFocus();QTest.keyClicks(w.search,'e sign');app.processEvents()
    assert [card.geometry() for _,card in w.cards]==before
    assert all(card.isVisible() for _,card in w.cards)
    assert w.command_results.currentItem().data(Qt.UserRole)=='Signature Check'
    QTest.keyClick(w.search,Qt.Key_Escape)
    assert not w.command_results.isVisible() and w.search.text()==''
    w.search.setFocus();QTest.keyClicks(w.search,'Scan');app.processEvents()
    assert w.command_results.currentItem().data(Qt.UserRole)=='Scan'
    QTest.keyClick(w.search,Qt.Key_Return);app.processEvents()
    assert w.current.name=='Scan'


def test_current_page_print_preserves_input_page_after_result(window,sample,monkeypatch):
    w,app=window;w.select_tool('Print');w.add_files([str(sample['pdf'])]);w.change_page(1)
    w.page_scope.setCurrentText('Current page')
    assert w.options()['pages']=='2'
    opened=[];monkeypatch.setattr(w,'print_result',lambda:opened.append(True))
    w.primary_action();wait(w,app)
    assert opened and w.options()['pages']=='2'
    with pymupdf.open(stream=w.result.data,filetype='pdf') as doc:
        assert len(doc)==1 and 'Beta' in doc[0].get_text()
    w.fields['copies'].setValue(2)
    w.primary_action();wait(w,app)
    with pymupdf.open(stream=w.result.data,filetype='pdf') as doc:assert 'Beta' in doc[0].get_text()


def test_discard_waits_safely_and_never_applies_background_result(window):
    w,app=window;w.select_tool('QR Generator');release=Event();callbacks=[]
    w.work(lambda:release.wait(2) or 'done',callbacks.append)
    assert w.busy and w.cancel_button.isVisible()
    w.discard_work();assert w.busy
    release.set();wait(w,app)
    assert callbacks==[] and w.result_message.title.text()=='Result discarded'
    assert not w.cancel_button.isVisible()


def test_scan_rotation_is_in_memory_and_keeps_original(window,sample):
    w,app=window;w.select_tool('Scan');original=sample['photo'].read_bytes()
    w.add_files([str(sample['photo'])]);w.rotate_scan_page()
    rotated=w.inputs()[0];assert isinstance(rotated,bytes)
    before=Image.open(io.BytesIO(original));after=Image.open(io.BytesIO(rotated))
    assert after.size==before.size[::-1] and sample['photo'].read_bytes()==original
    assert w.run_button.isEnabled()


def test_qr_copy_uses_the_actual_generated_image(window,monkeypatch):
    from cyber.engine import execute
    w,app=window;w.select_tool('QR Generator')
    result=execute('QR Generator',[],w.options(),w.store);w.show_result(result)
    copied=[]
    class Clipboard:
        def setImage(self,image):copied.append(image.size())
    monkeypatch.setattr(QApplication,'clipboard',lambda:Clipboard())
    w.copy_button.click()
    assert copied and copied[0].width()==w.options()['size']
    assert w.result.data==result.data and w.result_message.title.text()=='QR image copied'


def test_large_image_preview_is_bounded_and_keeps_original_crop_coordinates(window,tmp_path):
    w,app=window;path=tmp_path/'large.png';Image.new('RGB',(3000,2000),'#e3ece9').save(path)
    original=path.read_bytes();w.select_tool('Photo & Sign');w.add_files([str(path)])
    assert w.busy
    wait(w,app)
    assert w.preview_data==original and max(w.canvas.image.width(),w.canvas.image.height())<=2048
    w.on_selection([100,100,200,200])
    box=[float(x) for x in w.fields['box'].text().split(',')]
    assert abs(box[0]-100*3000/w.canvas.image.width())<.1
    assert abs(box[1]-100*2000/w.canvas.image.height())<.1
    assert path.read_bytes()==original


def test_theme_preference_survives_restart_without_changing_content(window):
    w,app=window;w.select_tool('QR Generator');w.fields['text'].setPlainText('Local customer content')
    dialog=w.create_settings_dialog();dialog.theme_select.setCurrentText('Dark');dialog.save_settings()
    assert w.theme['dark'] and w.fields['text'].toPlainText()=='Local customer content'
    reopened=MainWindow(w.store)
    assert reopened.theme['dark'] and reopened.appearance['theme']=='Dark'
    reopened.close()


def test_about_can_scroll_inside_a_small_high_dpi_work_area(window):
    w,app=window;dialog=about_dialog(w)
    fit_dialog(dialog,scroll_content=True,available=QRect(0,0,911,512));dialog.show();app.processEvents()
    assert dialog.width()<=879 and dialog.height()<=472
    assert any(button.text()=='Close' for button in dialog.findChildren(QPushButton))
    dialog.close()
