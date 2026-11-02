# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Repeatable visual review using synthetic documents, never desktop capture."""
import json
import time
from pathlib import Path
import pymupdf as fitz
from PIL import Image,ImageDraw
from PySide6.QtWidgets import QApplication,QScrollArea
from PySide6.QtCore import QEventLoop,Qt
from .ui import MainWindow
from .storage import Store
from .catalog import TOOLS
from .engine import execute


def settle(app,ms=65):
    deadline=time.monotonic()+ms/1000
    while time.monotonic()<deadline:
        app.processEvents(QEventLoop.AllEvents,10)
        time.sleep(.005)


def run(directory,all_tools=False):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([])
    store=Store(directory/'review.sqlite3')
    window=MainWindow(store)
    window.resize(1480,960)
    window.show()
    settle(app)
    pdf=directory/'sample-document.pdf'
    document=fitz.open()
    for index in range(2):
        page=document.new_page()
        page.draw_rect(fitz.Rect(38,38,557,100),fill=(.04,.2,.23),color=None)
        page.insert_text((56,65),'CREDONOMICS',fontsize=17,color=(1,1,1))
        page.insert_text((56,86),'CYBER SOLUTIONS / LOCAL WORKSPACE',fontsize=9,color=(.7,.9,.85))
        page.insert_text((42,155),'Document service summary',fontsize=24)
        page.insert_text((42,183),'SYNTHETIC REVIEW DOCUMENT - NO CUSTOMER DATA',fontsize=9,color=(.4,.45,.5))
        for row,(title,details) in enumerate([('Service','Document preparation'),('Format','A4 / PDF'),('Processing','Local, offline'),('Status','Ready for review')]):
            y=232+row*54
            page.draw_line((42,y+24),(551,y+24),color=(.86,.89,.91))
            page.insert_text((42,y),title,fontsize=11)
            page.insert_text((230,y),details,fontsize=11)
        page.insert_text((42,535),'Preview. Adjust. Save or print.',fontsize=18,color=(.0,.42,.37))
        page.insert_text((42,785),f'CredoNomics Cyber Solutions  |  Page {index+1}',fontsize=9,color=(.4,.45,.5))
    document.save(pdf)
    document.close()
    photo=directory/'sample-photo.png'
    image=Image.new('RGB',(700,900),'#eee9e3')
    draw=ImageDraw.Draw(image)
    draw.ellipse((235,110,465,370),fill='#b58b70')
    draw.rounded_rectangle((110,410,590,940),70,fill='#253d53')
    draw.text((22,22),'SYNTHETIC PHOTO',fill='#5d6b77')
    image.save(photo)
    measurements=[]
    def capture(name):
        settle(app)
        window.grab().save(str(directory/(name+'.png')))
        measurements.append({'screen':name,'width':window.width(),'height':window.height(),
            'dpi_scale':window.devicePixelRatioF(),'horizontal_overflow':[s.objectName() or type(s).__name__ for s in window.findChildren(QScrollArea) if s.isVisible() and s.horizontalScrollBar().maximum()>0]})
    capture('workspace')
    window.toggle_sidebar()
    settle(app,300)
    capture('workspace-menu-collapsed')
    window.toggle_sidebar()
    settle(app,300)
    window.select_tool('Print')
    window.add_files([str(pdf)])
    capture('print')
    window.select_tool('Scan')
    # Device enumeration is read-only. No scanner capture or print is triggered.
    window.find_scanners()
    deadline=time.monotonic()+15
    while window.busy and time.monotonic()<deadline:
        settle(app,40)
    if window.busy:
        raise RuntimeError('Scanner enumeration exceeded visual-review deadline.')
    capture('scan')
    window.select_tool('PDF Editor')
    window.add_files([str(pdf)])
    capture('pdf-editor')
    window.select_tool('Photo Print')
    window.add_files([str(photo)])
    result=execute('Photo Print',window.inputs(),window.options(),store)
    window.show_result(result)
    capture('photo-print')
    dialog=window.create_settings_dialog()
    dialog.show()
    settle(app)
    dialog.grab().save(str(directory/'settings-branding.png'))
    dialog.tabs.setCurrentIndex(3)
    settle(app)
    dialog.grab().save(str(directory/'settings-appearance.png'))
    dialog.reject()
    from .legal import about_dialog,document_dialog
    about=about_dialog(window)
    about.show()
    settle(app)
    about.grab().save(str(directory/'about-legal.png'))
    license_view=document_dialog(about,'Open-Source Licenses',licenses=True)
    license_view.show()
    settle(app)
    if not license_view.license_list.count() or not license_view.browser.toPlainText().strip():
        raise RuntimeError('Packaged license viewer is empty.')
    license_view.grab().save(str(directory/'open-source-licenses.png'))
    license_view.reject()
    for title,path in [('Privacy','docs/legal/DATA-HANDLING.md'),('Software License','docs/legal/SOFTWARE-LICENSE.md'),('Build','docs/legal/BUILD-INFO.md')]:
        viewer=document_dialog(about,title,path)
        if viewer.browser.toPlainText().startswith('This document is missing.'):
            raise RuntimeError('Packaged legal document is missing: '+path)
        viewer.reject()
    about.reject()
    if all_tools:
        for tool in TOOLS:
            window.select_tool(tool.name)
            if tool.name not in ('QR Generator','Resume Maker','Bill Maker','Screen Recording'):
                window.add_files([str(photo if tool.name in ('PVC Tool','Auto ID Card','Auto Crop','Edit Screenshot','Photo Print','Photo & Sign','PAN Tool') else pdf)])
            capture('tool-'+tool.name.lower().replace(' ','-').replace('&','and'))
    for width,height in [(1280,800),(1024,768),(860,620)]:
        window.resize(width,height)
        window.home()
        capture(f'workspace-{width}')
        window.select_tool('Print')
        window.add_files([str(pdf)])
        capture(f'print-{width}')
    window.resize(1280,800)
    window.showMaximized()
    settle(app)
    maximized=window.isMaximized()
    window.showNormal()
    settle(app)
    restored=not window.isMaximized()
    window.close()
    (directory/'layout-report.json').write_text(json.dumps({'screens':measurements,'maximize':maximized,'restore':restored,'success':True},indent=2),encoding='utf-8')
    return measurements
