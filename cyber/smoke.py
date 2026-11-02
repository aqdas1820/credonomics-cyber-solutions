# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Exercise the built executable without opening a visible window or using devices."""
import io
import json
from pathlib import Path

import pymupdf as fitz
from PIL import Image,ImageDraw
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter

from .ui import MainWindow
from .catalog import TOOLS
from .engine import execute
from .storage import Store
from .images import image_bytes,remove_background,qr_bytes
from .documents import ocr_pdf,signature_report


def run(directory):
    import socket
    def deny_network(*args,**kwargs):
        raise RuntimeError('Processing smoke test attempted a network connection.')
    socket.socket.connect=deny_network
    socket.create_connection=deny_network
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([])
    window=MainWindow(Store(directory/'smoke.sqlite3'))
    window.resize(1440,950)
    window.show()
    app.processEvents()
    window.grab().save(str(directory/'workspace.png'))
    names=[]
    for tool in TOOLS:
        window.select_tool(tool.name)
        app.processEvents()
        names.append(window.tool_title.text())
    window.select_tool('Bill Maker')
    window.fields['customer'].setText('Synthetic test customer')
    result=execute('Bill Maker',[],window.options(),window.store)
    window.show_result(result)
    window.grab().save(str(directory/'bill-maker.png'))
    (directory/'invoice.pdf').write_bytes(result.data)
    printer=QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(directory/'printed.pdf'))
    window.paint_pdf(result.data,printer)
    report=signature_report(directory/'invoice.pdf')
    assert report['signatures']==[]
    image=Image.new('RGB',(400,500),'#e9e3dc')
    ImageDraw.Draw(image).ellipse((100,50,300,250),fill='#b78769')
    ImageDraw.Draw(image).rectangle((75,250,325,499),fill='#254b64')
    from .distribution import is_commercial_build,build_profile,MODEL_UNAVAILABLE
    commercial=is_commercial_build()
    if commercial:
        try:
            remove_background(image,'transparent')
        except ValueError as error:
            assert str(error)==MODEL_UNAVAILABLE
        else:
            raise AssertionError('Unapproved model inference was available.')
    else:
        rgba=remove_background(image,'transparent')
        rgba.save(directory/'background-test.png')
    from .devices import mjpeg_writer
    import cv2,numpy as np
    writer=mjpeg_writer(directory/'synthetic-recording.avi',10,(160,120))
    backend=writer.getBackendName()
    for index in range(3):writer.write(np.full((120,160,3),index*80,dtype=np.uint8))
    writer.release()
    capture=cv2.VideoCapture(str(directory/'synthetic-recording.avi'),cv2.CAP_OPENCV_MJPEG)
    success,frame=capture.read()
    capture.release()
    assert success and frame.shape[:2]==(120,160)
    document=fitz.open()
    page=document.new_page(width=400,height=500)
    page.insert_image(page.rect,stream=image_bytes(image))
    data=document.tobytes()
    document.close()
    ocr=ocr_pdf(data)
    assert ocr.startswith(b'%PDF')
    qr_bytes('CredoNomics packaged test','SVG')
    window.close()
    qt_libraries={}
    import sys
    if sys.platform=='win32':
        import ctypes,hashlib
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p]
        kernel.GetModuleHandleW.restype=ctypes.c_void_p
        kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint]
        for name in ('Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','Qt6Svg.dll','Qt6PrintSupport.dll'):
            handle=kernel.GetModuleHandleW(name)
            buffer=ctypes.create_unicode_buffer(32768)
            assert handle and kernel.GetModuleFileNameW(handle,buffer,len(buffer))
            path=Path(buffer.value)
            base=Path(sys.executable).parent
            relative=path.relative_to(base).as_posix() if path.is_relative_to(base) else path.name
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            qt_libraries[name]={'path':relative,'sha256':digest}
    import hashlib
    exe_sha=None
    if getattr(sys,'frozen',False):
        with Path(sys.executable).open('rb') as stream:exe_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    (directory/'result.json').write_text(json.dumps({'success':True,'exe_sha256':exe_sha,'profile':build_profile(),'workspaces':names,'ai_inference':not commercial,'ai_unavailable_expected':commercial,'recording_backend':backend,'recording_decode':success,'qt_loaded_libraries':qt_libraries,'ocr':True,'pdf_print':True,'signature_inspection':True,'qr_svg':True},indent=2),encoding='utf-8')
