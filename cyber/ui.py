# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import pymupdf as fitz
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QPointF, QUrl, QTimer, QSaveFile, QIODevice,QSize
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QImage, QPainter, QPen, QPixmap, QPageLayout,QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget, QListWidgetItem, QStackedWidget,
    QScrollArea, QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QFormLayout, QSplitter, QProgressBar, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo

from . import BRAND, __version__, PUBLISHER, WEBSITE
from .views import DesktopUI
from .components import label,button,icon,Modal
from .theme import COLORS
from .catalog import TOOLS, BY_NAME, DESIGNS
from .engine import execute, rectangle, Result
from .images import load_image, image_bytes, model_path
from .storage import Store
from .devices import Recorder, scanners, scan_page
from .licensing import machine_id, verify_license
from .diagnostics import record







class Worker(QThread):
    ready=Signal(object)
    failed=Signal(str)
    def __init__(self,fn):
        super().__init__()
        self.fn=fn
    def run(self):
        try:
            self.ready.emit(self.fn())
        except Exception as error:
            record('worker_failed',error=error)
            self.failed.emit(str(error) or type(error).__name__)


class Canvas(QWidget):
    selected=Signal(object)
    def __init__(self):
        super().__init__()
        self.image=None
        self.origin=None
        self.selection=None
        self.target=QRectF()
        self.zoom=1.
        self.pan=QPointF()
        self.pan_origin=None
        self.setMinimumSize(280,350)
        self.setCursor(Qt.CrossCursor)
        self.setAccessibleName('Document preview')
        self.setAccessibleDescription('Mouse wheel to zoom, right-drag to pan, or drag to select a region. Selection coordinates can also be entered in the options.')
        self.setToolTip('Wheel: zoom · Right-drag: pan · Drag: select region\nCtrl+= / Ctrl+-: zoom · Ctrl+0: fit page')
    def set_image(self,image):
        self.selection=None
        self.zoom=1.
        self.pan=QPointF()
        if image is None:
            self.image=None
        else:
            rgb=image.convert('RGB')
            self.image=QImage(rgb.tobytes(),rgb.width,rgb.height,rgb.width*3,QImage.Format_RGB888).copy()
        self.update()
    def paintEvent(self,event):
        painter=QPainter(self)
        theme=getattr(self,'theme',COLORS)
        painter.fillRect(self.rect(),QColor(theme['preview']))
        if self.image is None:
            painter.setPen(QColor(theme['secondary']))
            painter.setFont(QFont('Lato',13))
            painter.drawText(self.rect(),Qt.AlignCenter,'Your file preview appears here\n\nOpen a file or prepare a result')
            return
        scale=min((self.width()-44)/self.image.width(),(self.height()-44)/self.image.height())*self.zoom
        w,h=self.image.width()*scale,self.image.height()*scale
        self.target=QRectF((self.width()-w)/2+self.pan.x(),(self.height()-h)/2+self.pan.y(),w,h)
        painter.fillRect(self.target.adjusted(-3,-3,3,3),QColor(theme['stroke_strong']))
        painter.drawImage(self.target,self.image)
        if self.selection:
            painter.setPen(QPen(QColor(theme['focus']),2,Qt.DashLine))
            painter.setBrush(QColor(0,167,147,30))
            painter.drawRect(self.selection)
    def mousePressEvent(self,event):
        if event.button()==Qt.RightButton:
            self.pan_origin=event.position()
            return
        if self.image and self.target.contains(event.position()):
            self.origin=event.position()
            self.selection=QRectF(self.origin,self.origin)
    def mouseMoveEvent(self,event):
        if self.pan_origin is not None:
            self.pan+=event.position()-self.pan_origin
            self.pan_origin=event.position()
            self.selection=None
            self.update()
            return
        if self.origin:
            self.selection=QRectF(self.origin,event.position()).normalized().intersected(self.target)
            self.update()
    def mouseReleaseEvent(self,event):
        if event.button()==Qt.RightButton:
            self.pan_origin=None
            return
        if self.origin and self.image and self.selection and self.selection.width()>2 and self.selection.height()>2:
            rect=self.selection
            scale=self.image.width()/self.target.width()
            self.selected.emit([(rect.x()-self.target.x())*scale,(rect.y()-self.target.y())*scale,rect.width()*scale,rect.height()*scale])
        self.origin=None
    def set_zoom(self,value):
        self.zoom=max(.5,min(6.,value))
        self.selection=None
        if value==1:
            self.pan=QPointF()
        self.update()
    def wheelEvent(self,event):
        self.set_zoom(self.zoom*(1.15 if event.angleDelta().y()>0 else 1/1.15))
        event.accept()


class MainWindow(DesktopUI,QMainWindow):
    def __init__(self,store=None):
        super().__init__()
        asset_root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
        for font in (asset_root/'assets/fonts').glob('*.ttf'):
            # Qt's Windows native font loader can reject non-ASCII file paths.
            # Python reads the same bundled bytes through the wide-path API.
            try:
                QFontDatabase.addApplicationFontFromData(font.read_bytes())
            except OSError:
                record('font_unavailable')
        self.store=store or Store()
        self.current=None
        self.fields={}
        self.result=None
        self.preview_data=None
        self.page=0
        self.page_count=0
        self.pdf_ratio=1
        self.busy=False
        self.workers=[]
        self.recorder=Recorder()
        self.setup_ui()
        self.home()
        self.restore_window()

    def restore_window(self,first_launch=False):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import QRect
        saved=self.store.get('window',{})
        if not saved and not first_launch:return
        screen=self.screen() or QGuiApplication.primaryScreen()
        if not screen:return
        requested=QRect(saved.get('x',screen.availableGeometry().x()),saved.get('y',screen.availableGeometry().y()),max(760,saved.get('width',1480)),max(480,saved.get('height',960)))
        screen=next((s for s in QGuiApplication.screens() if s.availableGeometry().intersects(requested)),screen)
        available=screen.availableGeometry()
        width=min(requested.width(),available.width());height=min(requested.height(),available.height())
        x=max(available.x(),min(requested.x(),available.right()-width+1))
        y=max(available.y(),min(requested.y(),available.bottom()-height+1))
        self.setGeometry(x,y,width,height)
        if saved.get('maximized',False):self.setWindowState(self.windowState()|Qt.WindowMaximized)







    def select_and_open(self,name):
        if self.busy or self.recorder.running:
            return
        self.select_tool(name)
        self.open_files()


    def inputs(self):
        return [self.files.item(i).data(Qt.UserRole) for i in range(self.files.count())]

    def open_files(self):
        if self.busy or self.recorder.running:return
        paths,_=self.file_dialog(QFileDialog.getOpenFileNames,'Open local files',self.last_folder('input'),'Documents and images (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.doc *.docx *.xls *.xlsx *.ppt *.pptx *.odt *.ods);;All files (*)')
        if paths:self.remember_folder('input',Path(paths[0]).parent)
        self.add_files(paths)

    def file_dialog(self,function,*args):
        if getattr(self,'_file_dialog_active',False):return '', ''
        self._file_dialog_active=True
        try:return function(self,*args,options=QFileDialog.Options())
        finally:self._file_dialog_active=False

    def last_folder(self,key):
        value=self.store.get('folders',{}).get(key,'')
        try:return value if value and Path(value).is_dir() else ''
        except OSError:return ''

    def remember_folder(self,key,path):
        import sqlite3
        try:self.store.set('folders',self.store.get('folders',{})|{key:str(path)})
        except (OSError,sqlite3.Error):
            self.statusBar().showMessage('Folder preference could not be saved. Your document is unchanged.')

    def add_files(self,paths):
        if self.busy or self.recorder.running or not paths:
            return
        if self.current is None:
            self.select_tool('Print')
        elif self.stack.currentIndex()==0:
            self.select_tool('Print')
        if self.current.name in ('QR Generator','Resume Maker','Bill Maker','Screen Recording'):
            self.error('This tool uses form fields rather than document input. Open a document or photo tool to add files.');return
        image_types={'.png','.jpg','.jpeg','.tif','.tiff','.bmp','.webp'}
        accepted={'.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp'}|image_types
        if self.current.name in ('Photo Print','Photo & Sign','PAN Tool','Edit Screenshot'):accepted=image_types
        if self.current.name=='Signature Check':accepted={'.pdf'}
        valid=[]
        for path in paths:
            if isinstance(path,str):
                try:
                    source=Path(path)
                    if not source.is_file():
                        self.error('The selected file is unavailable. Choose a local document or image.');continue
                    size=source.stat().st_size
                except OSError:
                    self.error('The selected file could not be read. Check access permissions and choose it again.');continue
                if source.suffix.lower() not in accepted:
                    self.error('This file type is not supported by '+self.current.name+'. Choose a compatible local file.');continue
                if not size:
                    self.error('The selected file is empty. Choose a document that contains data.');continue
                if size>150*1024*1024:
                    self.error('Choose files smaller than 150 MB each.')
                    continue
                valid.append(path)
        if not valid:return
        from .limits import input_limit
        maximum=input_limit(self.current.name,self.options())
        if maximum and self.files.count()+len(valid)>maximum:
            self.error(f'This tool accepts at most {maximum} input '+('file' if maximum==1 else 'files')+' per job. Use Start another to clear the current input.');return
        self.invalidate_result()
        self.copy_button.setEnabled(False)
        for path in valid:
            item=QListWidgetItem(Path(path).name)
            item.setIcon(icon('image' if Path(path).suffix.lower() in image_types else 'files'))
            item.setData(Qt.UserRole,path)
            item.setToolTip(path)
            self.files.addItem(item)
        if self.files.count():
            self.files.setCurrentRow(0)
            self.preview_input()
        self.update_file_summary()

    def move_file(self,delta):
        row=self.files.currentRow()
        target=row+delta
        if 0<=target<self.files.count():
            item=self.files.takeItem(row)
            self.files.insertItem(target,item)
            self.files.setCurrentRow(target)
            self.invalidate_result()

    def remove_files(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))
        self.invalidate_result()
        self.preview_input()

    def invalidate_result(self):
        self.result=None
        self.saved_output=None
        if hasattr(self,'open_output_button'):
            self.open_output_button.hide();self.open_folder_button.hide()
        self.save_button.setEnabled(False)
        self.print_button.setEnabled(False)

    def options(self):
        result: dict[str, Any]={}
        for key,widget in self.fields.items():
            if isinstance(widget,QComboBox):
                result[key]=widget.currentText()
            elif isinstance(widget,QCheckBox):
                result[key]=widget.isChecked()
            elif isinstance(widget,(QSpinBox,QDoubleSpinBox)):
                result[key]=widget.value()
            elif isinstance(widget,QTextEdit):
                result[key]=widget.toPlainText()
            else:
                result[key]=widget.text()
        if 'design' in result:
            result['design']=DESIGNS.index(result['design'])
        if self.current.name=='Print' and hasattr(self,'page_scope') and self.page_scope.currentText()=='Current page':
            result['pages']=str(getattr(self,'_input_page',0)+1)
            result['current_input']=max(0,self.files.currentRow())
        if self.current.name=='Bill Maker':
            result['items']=[]
            for row in range(self.items.rowCount()):
                values=[self.items.item(row,col).text() if self.items.item(row,col) else '' for col in range(4)]
                if values[0].strip():
                    result['items'].append(dict(zip(('description','qty','rate','tax'),values)))
        return result

    def add_invoice_line(self):
        row=self.items.rowCount()
        self.items.insertRow(row)
        for col,value in enumerate(('','1','0','0')):
            self.items.setItem(row,col,QTableWidgetItem(value))

    def work(self,fn,callback,*,preview=False):
        if self.busy:
            return
        self.busy=True
        record('preview_started' if preview else 'operation_started',tool=self.current.name if self.current else None)
        self._discard_result=False
        self.run_button.setEnabled(False)
        self.nav.setEnabled(False)
        self.workspace_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.history_button.setEnabled(False)
        self.form_scroll.setEnabled(False)
        self.file_scroll.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.preview_toolbar.setEnabled(False)
        self.empty_state.action.setEnabled(False)
        self.save_button.setEnabled(False)
        self.print_button.setEnabled(False)
        self.reset_button.hide()
        self.copy_button.setEnabled(False)
        self.open_output_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        for action in (self.preview_button,self.save_button,self.print_button,self.copy_button):action.hide()
        self.progress.show()
        self.cancel_button.setText('Discard preview' if preview else 'Discard result')
        self.result_message.set_state('processing','Preparing preview' if preview else 'Processing locally','Please wait. Your original files remain unchanged.')
        self.statusBar().showMessage('Working locally…')
        worker=Worker(fn)
        self.workers.append(worker)
        def restore():
            self.busy=False
            self.run_button.setEnabled(True)
            self.nav.setEnabled(True)
            self.workspace_button.setEnabled(True)
            self.back_button.setEnabled(True)
            self.settings_button.setEnabled(True)
            self.history_button.setEnabled(True)
            self.form_scroll.setEnabled(True)
            self.file_scroll.setEnabled(True)
            self.preview_button.setEnabled(True)
            self.preview_toolbar.setEnabled(True)
            self.empty_state.action.setEnabled(True)
            self.open_output_button.setEnabled(True)
            self.open_folder_button.setEnabled(True)
            self.progress.hide()
            self.cancel_button.hide()
            self.reset_button.show()
            self.preview_button.setVisible(self.current.name=='Print')
            self.save_button.show()
            self.print_button.setVisible(self.current.name!='Print')
            self.copy_button.setVisible(self.current.name=='QR Generator')
            if self.current.name=='Print':self.sync_printer()
            elif self.current.name=='Scan':self.update_file_summary()
            if self.result:
                self.save_button.setEnabled(True)
                self.print_button.setEnabled(bool(self.preview_data and self.preview_data.startswith(b'%PDF')))
                self.copy_button.setEnabled(self.current.name=='QR Generator')
        def done(result):
            restore()
            if self._discard_result:
                if preview:
                    self.canvas.hide();self.text_preview.hide();self.preview_toolbar.hide()
                    self.empty_state.title.setText('Preview discarded')
                    self.empty_state.body.setText('Your file is unchanged. Load the preview again when you are ready.')
                    self.empty_state.action.setText('Retry preview');self.empty_state.show()
                    self.preview_caption.setText('Preview discarded')
                self.result_message.set_state('info','Preview discarded' if preview else 'Result discarded','The operation finished safely. No new output was exported.')
                self.statusBar().showMessage('Result discarded · Ready')
                return
            self.statusBar().showMessage('Ready · Local operation completed')
            try:
                callback(result)
                record('operation_completed',tool=self.current.name if self.current else None)
            except Exception as error:
                self.error(str(error))
        def failed(message):
            restore()
            if self._discard_result:
                self.result_message.set_state('info','Result discarded','No new output was exported.')
                return
            self.error(message)
        worker.ready.connect(done)
        worker.failed.connect(failed)
        worker.finished.connect(lambda:self.workers.remove(worker) if worker in self.workers else None)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def prepare(self):
        if self.busy or getattr(self,'_printing',False):return
        if self.current.name=='Screen Recording':
            self.toggle_recording()
            return
        options=self.options()
        files=self.inputs()
        name=self.current.name
        if name=='PDF Editor' and self.result and self.result.extension=='pdf':
            files=[self.result.data]
        self.invalidate_result()
        self.work(lambda:execute(name,files,options,self.store),self.show_result)

    def show_result(self,result):
        self.result=result
        self.saved_output=None
        self.open_output_button.hide();self.open_folder_button.hide()
        self.result_message.set_state('success','Your result is ready',result.message)
        if self.current.name=='Signature Check':
            report=json.loads(result.data)
            signatures=report.get('signatures',[])
            self.result_message.set_state('info' if signatures else 'warning','Signature inspection complete','Review document integrity and certificate trust separately. No current revocation status was checked.')
        self.save_button.setEnabled(True)
        preview=result.preview or result.data
        self.show_data(preview,result.name)
        self.print_button.setEnabled(preview.startswith(b'%PDF'))
        self.copy_button.setEnabled(self.current.name=='QR Generator')
        self.output_summary.setText(f'Output · {len(result.data)/1024:.1f} KB')
        self.output_summary.setToolTip(result.message)
        if self.current.name=='Print':
            self._prepared_print_options=dict(self.options())
            self._prepared_print_inputs=list(self.inputs())
            self.sync_printer()
        self.statusBar().showMessage(f'Result ready · {len(result.data)/1024:.1f} KB · original files unchanged')

    def copy_qr_image(self):
        if not self.result or self.current.name!='QR Generator':return
        image=QImage.fromData(self.result.preview or self.result.data)
        if image.isNull():
            self.error('Could not copy this image. Save the result to a file instead.')
            return
        QApplication.clipboard().setImage(image)
        self.result_message.set_state('success','QR image copied','Paste it into a document or another application.')

    @staticmethod
    def needs_background_preview(value):
        try:
            size=len(value) if isinstance(value,bytes) else Path(value).stat().st_size
            if (isinstance(value,bytes) and value.startswith(b'%PDF')) or (isinstance(value,str) and Path(value).suffix.lower()=='.pdf'):return size>5*1024*1024
            with Image.open(io.BytesIO(value) if isinstance(value,bytes) else value) as image:
                return size>5*1024*1024 or image.width*image.height>4_000_000
        except (OSError,ValueError):return False

    @staticmethod
    def preview_payload(value):
        """Decode/rasterise a large preview off the GUI thread; keep exports intact."""
        data=value if isinstance(value,bytes) else Path(value).read_bytes()
        thumbs=[]
        if data.startswith(b'%PDF'):
            with fitz.open(stream=data,filetype='pdf') as doc:
                page=doc[0];width=page.rect.width
                zoom=min(1.3,2048/max(page.rect.width,page.rect.height))
                pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),colorspace=fitz.csRGB,alpha=False)
                image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                count=len(doc)
                for index in range(min(count,40)):
                    p=doc[index];small=p.get_pixmap(matrix=fitz.Matrix(min(.1,100/max(p.rect.width,p.rect.height)),min(.1,100/max(p.rect.width,p.rect.height))),colorspace=fitz.csRGB,alpha=False)
                    thumbs.append((small.width,small.height,small.samples))
                return data,image,count,width/image.width,None,thumbs
        image=load_image(data);original=image.size
        image.thumbnail((2048,2048),Image.Resampling.LANCZOS)
        return data,image,0,1.,original,thumbs

    def load_background_preview(self,value,name,is_input):
        if self.busy:return
        self._retry_preview=(value,name,is_input)
        self.preview_caption.setText('Loading preview…')
        def ready(payload):
            data,image,count,ratio,original,thumbs=payload
            self._retry_preview=None
            self.preview_data=data;self.page=0;self.page_count=count;self.pdf_ratio=ratio
            self.preview_is_input=is_input
            if is_input:self._input_page=0
            self.image_ratio=(original[0]/image.width,original[1]/image.height) if original else (1.,1.)
            self.canvas.set_image(image);self.empty_state.hide();self.text_preview.hide();self.canvas.show()
            self.preview_caption.setText(name[:40]);self.preview_caption.setToolTip(name)
            self.page_label.setText(f'Page 1 of {count}' if count else f'{original[0]} × {original[1]} px')
            self.preview_toolbar.show()
            for action in self.page_actions:action.setVisible(bool(count))
            self.show_input_button.setVisible(bool(self.inputs()))
            self.thumbnails.clear()
            for index,(width,height,pixels) in enumerate(thumbs):
                thumb=QImage(pixels,width,height,width*3,QImage.Format_RGB888).copy()
                item=QListWidgetItem(QIcon(QPixmap.fromImage(thumb)),f'Page {index+1}')
                item.setData(Qt.UserRole,index);item.setSizeHint(QSize(120,64));self.thumbnails.addItem(item)
            self.thumbnails.setVisible(bool(count and self.width()>=1320 and self.current.name in ('Print','Scan')))
            self.result_message.set_state('info','Preview ready','Your original file and export resolution are preserved.')
        self.work(lambda:self.preview_payload(value),ready,preview=True)

    def show_data(self,data,name='Preview',is_input=False):
        if self.needs_background_preview(data):
            self.load_background_preview(data,name,is_input)
            return
        self._retry_preview=None
        self.page=0
        self.preview_is_input=is_input
        if is_input:self._input_page=0
        self.preview_data=data
        self.preview_toolbar.show()
        for action in self.page_actions:action.setVisible(data.startswith(b'%PDF'))
        self.show_input_button.setVisible(bool(self.inputs()))
        self.preview_caption.setText(name[:40])
        self.empty_state.hide()
        self.text_preview.hide()
        self.canvas.show()
        if data.startswith(b'%PDF'):
            with fitz.open(stream=data,filetype='pdf') as document:
                self.page_count=len(document)
            self.render_page()
        else:
            self.page_count=0
            self.pdf_ratio=1
            self.page_label.setText('')
            try:
                image=load_image(data)
                self.image_ratio=(1.,1.)
                self.canvas.set_image(image)
                self.page_label.setText(f'{image.width} × {image.height} px')
            except Exception:
                self.canvas.hide()
                self.text_preview.show()
                text=data.decode('utf-8') if not data.startswith(b'PK') else 'This result is a document or archive. Save it to open it with its associated application.'
                if self.current and self.current.name=='Signature Check' and name.endswith('.json'):
                    report=json.loads(text)
                    entries=report.get('signatures',[])
                    lines=['Signature inspection','',f'Embedded signatures found: {len(entries)}','']
                    if not entries:lines.append('No embedded digital signatures were found. This document is unsigned; it has not been verified.')
                    for index,entry in enumerate(entries,1):
                        lines.extend([f'Signature {index}: '+entry.get('field','Unnamed field')])
                        if entry.get('error'):lines.append('The offline check could not be completed. Save the report to inspect its details.')
                        else:
                            lines.extend(['Document integrity: '+('Intact' if entry.get('intact') else 'Not intact'),
                                          'Cryptographic check: '+('Valid' if entry.get('cryptographically_valid') else 'Not valid'),
                                          'Trusted by supplied roots: '+('Yes' if entry.get('trusted') else 'Not established')])
                        lines.append('')
                    lines.extend(['','Offline inspection only. This action does not sign a document or establish current revocation status.','Save result exports the complete inspection report.'])
                    text='\n'.join(lines)
                self.text_preview.setPlainText(text)
        self.refresh_thumbnails()

    def render_page(self):
        with fitz.open(stream=self.preview_data,filetype='pdf') as document:
            page=document[self.page]
            zoom=min(1.3,2048/max(page.rect.width,page.rect.height))
            pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False,colorspace=fitz.csRGB)
            self.pdf_ratio=page.rect.width/pix.width
            self.canvas.set_image(Image.frombytes('RGB',(pix.width,pix.height),pix.samples))
        self.page_label.setText(f'Page {self.page+1} of {self.page_count}')
        if getattr(self,'preview_is_input',False):
            self._input_page=self.page
            if self.current and self.current.name=='Print' and hasattr(self,'page_scope') and self.page_scope.currentText()=='Current page':
                self.fields['pages'].setText(str(self._input_page+1))
        self.update_workflow_context()

    def change_page(self,delta):
        if self.page_count and not self.busy:
            self.page=max(0,min(self.page_count-1,self.page+delta))
            self.render_page()

    def preview_input(self):
        if self.busy or not hasattr(self,'files'):
            return
        row=max(0,self.files.currentRow())
        if not self.files.count():
            self.preview_data=None
            self.page_count=0
            self.page_label.clear()
            self.preview_caption.setText('No file selected')
            self.canvas.set_image(None)
            self.canvas.hide()
            self.text_preview.hide()
            self.empty_state.show()
            self.preview_toolbar.hide()
            self.refresh_thumbnails()
            return
        value=self.files.item(row).data(Qt.UserRole)
        try:
            if isinstance(value,str) and Path(value).suffix.lower() in ('.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods'):
                self.preview_data=None
                self.page_count=0
                self._input_page=0
                self.page_label.clear()
                self.preview_toolbar.hide()
                self.thumbnails.clear()
                self.thumbnails.hide()
                self.canvas.set_image(None)
                self.canvas.hide()
                self.empty_state.show()
                self.empty_state.title.setText('Office document selected')
                self.empty_state.body.setText('Prepare your result to see the converted document.')
                self.preview_caption.setText('Prepare to convert this Office document')
                self.update_workflow_context()
                return
            if self.needs_background_preview(value):
                self.load_background_preview(value,self.files.item(row).text(),True)
                return
            data=value if isinstance(value,bytes) else Path(value).read_bytes()
            self.show_data(data,self.files.item(row).text(),is_input=True)
        except Exception as error:
            self.preview_data=None
            self.page_count=0
            self._input_page=0
            self.page_label.clear()
            self.preview_toolbar.hide()
            self.thumbnails.clear()
            self.thumbnails.hide()
            self.canvas.set_image(None)
            self.canvas.hide()
            self.empty_state.show()
            self.preview_caption.setText('Preview unavailable')
            self.result_message.set_state('warning','Preview unavailable','The file may be unsupported or damaged. Try another file or prepare it with Convert.')

    def on_selection(self,box):
        if 'box' in self.fields:
            ratios=(self.pdf_ratio,self.pdf_ratio) if self.preview_data and self.preview_data.startswith(b'%PDF') else getattr(self,'image_ratio',(1.,1.))
            self.fields['box'].setText(', '.join(str(round(n*ratios[index%2],1)) for index,n in enumerate(box)))
            if 'page' in self.fields:
                self.fields['page'].setValue(self.page+1)

    def save(self):
        if not self.result or self.busy or self.recorder.running:
            return
        start=str(Path(self.last_folder('export'))/self.result.name)
        path,_=self.file_dialog(QFileDialog.getSaveFileName,'Save result',start,f'Result (*.{self.result.extension})')
        if not path:
            return
        if not Path(path).suffix:
            path+='.'+self.result.extension
        originals=[Path(p).resolve() for p in self.inputs() if isinstance(p,str)]
        if Path(path).resolve() in originals:
            self.error('Choose a different name to preserve your original file.')
            return
        output=QSaveFile(path)
        if not output.open(QIODevice.WriteOnly):
            self.error(output.errorString())
            return
        if output.write(self.result.data)!=len(self.result.data):
            output.cancelWriting()
            self.error('Could not save the output completely. Check disk space and folder permissions.')
            return
        if not output.commit():
            self.error('Could not save the output completely. Check disk space and folder permissions.')
            return
        history_saved=True
        if self.result.record:
            record=self.result.record
            import sqlite3
            try:
                self.store.save_record(record['kind'],record['phone'],record['title'],record['body'])
                self.result.record=None
            except (OSError,sqlite3.Error):
                history_saved=False
        self.statusBar().showMessage('Saved · '+Path(path).name)
        self.result_message.set_state('success','Saved successfully',f'{Path(path).name} · {len(self.result.data)/1024:.1f} KB · Folder: {Path(path).parent.name}. Your original files are unchanged.')
        self.remember_folder('export',Path(path).parent)
        self.saved_output=Path(path)
        self.open_output_button.show();self.open_folder_button.show()
        if not history_saved:
            self.result_message.set_state('warning','File saved; history unavailable','Your exported file is complete. The local record could not be saved; check application-data permissions and disk space.')

    def open_saved_output(self,folder=False):
        path=getattr(self,'saved_output',None)
        if self.busy or not path:return
        target=path.parent if folder else path
        if not target.exists():
            self.error('The exported file is no longer available. Save it again or check the selected folder.');return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
            self.error('Could not open this location. Use Windows Explorer or choose another default application.')

    def print_result(self):
        if self.busy or self.recorder.running or getattr(self,'_printing',False):return
        self._printing=True
        try:self._print_result()
        finally:self._printing=False

    def _print_result(self):
        data=(self.result.preview or self.result.data) if self.result else None
        if not data or not data.startswith(b'%PDF'):
            return
        printer=QPrinter(QPrinter.HighResolution)
        printer.setDocName(self.result.name)
        options=self.options()
        scale_mode='Fit printable area'
        if self.current.name=='Print':
            name=self.printer_select.currentText()
            if name not in self.printers:
                self.error('Install a Windows printer driver or save your result as a PDF.')
                return
            printer.setPrinterName(name)
            paper=self.paper_select.currentData()
            if paper:
                printer.setPageSize(paper)
            printer.setPageOrientation(QPageLayout.Landscape if self.orientation_select.currentText()=='Landscape' else QPageLayout.Portrait)
            scale_mode=self.scale_select.currentText()
            printer.setColorMode(QPrinter.GrayScale if options.get('colour')=='Black & white' else QPrinter.Color)
        printer.setCopyCount(int(options.get('copies',1)) if self.current.name=='Print' else 1)
        if self.current.name=='Print' and options.get('duplex'):
            printer.setDuplex(QPrinter.DuplexLongSide)
        dialog=QPrintDialog(printer,self)
        try:accepted=dialog.exec()==QDialog.Accepted
        finally:dialog.deleteLater()
        if not accepted:
            self.result_message.set_state('info','Print cancelled','No print job was submitted by this application.')
            return
        try:
            self.paint_pdf(data,printer,scale_mode)
            from datetime import datetime
            self.result_message.set_state('success','Sent to Windows print driver',f'{printer.printerName()} · {self.result.name} · {datetime.now():%H:%M}. Check the Windows print queue for hardware status.')
            self.statusBar().showMessage('Sent to the selected printer. Check the Windows print queue for hardware status.')
        except Exception as error:
            self.error(str(error))

    @staticmethod
    def paint_pdf(data,printer,scale_mode='Fit printable area'):
        from .limits import validate_pixels,raster_page
        with fitz.open(stream=data,filetype='pdf') as document:
            selected=list(range(len(document)))
            if printer.printRange()==QPrinter.PageRange:selected=selected[max(0,printer.fromPage()-1):printer.toPage()]
            for index in selected:
                page=document[index]
                validate_pixels(__import__('math').ceil(page.rect.width*2.5),__import__('math').ceil(page.rect.height*2.5))
        painter=QPainter()
        if not painter.begin(printer):
            raise ValueError('Could not open the selected printer.')
        try:
            with fitz.open(stream=data,filetype='pdf') as document:
                selected=list(range(len(document)))
                if printer.printRange()==QPrinter.PageRange:
                    selected=selected[max(0,printer.fromPage()-1):printer.toPage()]
                for position,i in enumerate(selected):
                    page=document[i]
                    if position and not printer.newPage():
                        raise ValueError('Printer rejected a new page.')
                    pix=raster_page(page,dpi=180,alpha=False,colorspace=fitz.csRGB)
                    image=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
                    target=printer.pageLayout().paintRectPixels(printer.resolution())
                    ratio=min(target.width()/pix.width,target.height()/pix.height)
                    if scale_mode=='Actual size':
                        ratio=printer.resolution()/180
                    rect=QRectF((target.width()-pix.width*ratio)/2,(target.height()-pix.height*ratio)/2,pix.width*ratio,pix.height*ratio)
                    painter.drawImage(rect,image)
        finally:
            if not painter.end():raise ValueError('The Windows print driver could not finish this job. Check its queue before trying again.')

    def find_scanners(self):
        def ready(devices):
            self._scanner_discovered_empty=not bool(devices)
            self.scan_select.clear()
            for device in devices:
                self.scan_select.addItem(device['name'],device['id'])
            self.scan_button.setEnabled(bool(devices))
            if not devices:
                self.scan_select.addItem('No scanner connected',None)
                self.scanner_status.setText('No scanner detected. Connect a Windows-compatible scanner and refresh devices.')
                if not self.files.count():
                    self.empty_state.title.setText('No scanner detected')
                    self.empty_state.body.setText('Connect a Windows-compatible scanner and refresh devices. You can also import existing scans from the file panel.')
                    self.empty_state.action.setText('Refresh devices')
                self.result_message.set_state('warning','No scanner detected','Connect a scanner and refresh devices, or import existing scans.')
            else:
                self.scanner_status.setText(f'{len(devices)} scanner(s) discovered through Windows WIA.')
                self.result_message.set_state('success','Scanner available','Place a page in the scanner, then choose Scan / add page.')
        self.work(scanners,ready)

    def scan(self):
        device=self.scan_select.currentData()
        if not device:
            self.error('Find and select a scanner first.')
            return
        dpi=int(self.options()['dpi'])
        def ready(image):
            self.invalidate_result()
            data=image_bytes(image)
            item=QListWidgetItem(f'Scanned page {self.files.count()+1}')
            item.setData(Qt.UserRole,data)
            self.files.addItem(item)
            self.files.setCurrentRow(self.files.count()-1)
            self.show_data(data,item.text())
            self.result_message.set_state('success','Page scanned','Add another page or build and save the combined PDF. Scanned pages are currently held in this workspace.')
        self.work(lambda:scan_page(device,dpi),ready)

    def finish_recording_ui(self):
        if getattr(self,'record_timer',None):
            self.record_timer.stop()
            self.record_timer.deleteLater()
            self.record_timer=None
        self.run_button.setText('Start recording')
        for control in (self.nav,self.form_scroll,self.reset_button,self.workspace_button,self.back_button,self.settings_button,self.history_button,self.empty_state.action):
            control.setEnabled(True)

    def toggle_recording(self):
        if self.busy or getattr(self,'_file_dialog_active',False):return
        if time.monotonic()-getattr(self,'_last_record_action',0)<.25:return
        self._last_record_action=time.monotonic()
        try:
            if self.recorder.running:
                try:count=self.recorder.stop()
                finally:
                    if not self.recorder.running:self.finish_recording_ui()
                if not count:raise ValueError('No frames were recorded. Start another recording and wait for capture to begin.')
                self.result_message.set_state('success','Recording saved',f'{count} frames written. Your privacy masks were applied before encoding.')
                self.statusBar().showMessage('Recording saved · '+getattr(self,'recording_name','recording.avi'))
                return
            options=self.options()
            masks=[rectangle(line) for line in options['masks'].splitlines() if line.strip()]
            path,_=self.file_dialog(QFileDialog.getSaveFileName,'Save screen recording',str(Path(self.last_folder('export'))/'recording.avi'),'AVI video (*.avi)')
            if not path:
                return
            self.recorder.start(path,masks,int(options['fps']),int(options['monitor']))
            self._last_record_action=time.monotonic()
            self.recording_name=Path(path).name
            self.statusBar().showMessage('Recording locally · Choose Stop recording to finish')
            self.run_button.setText('Stop recording')
            for control in (self.nav,self.form_scroll,self.reset_button,self.workspace_button,self.back_button,self.settings_button,self.history_button,self.empty_state.action):control.setEnabled(False)
            self.record_timer=QTimer(self)
            def progress():
                self.result_message.set_state('processing','Recording locally',f'{self.recorder.frames} frames · Choose Stop recording to finish.')
                if not self.recorder.running:
                    self.finish_recording_ui()
                    self.error(self.recorder.error or 'Recording stopped.')
            self.record_timer.timeout.connect(progress)
            self.record_timer.start(500)
        except Exception as error:
            if not self.recorder.running:self.finish_recording_ui()
            self.error(str(error))

    def history(self):
        kind='resume' if self.current.name=='Resume Maker' else 'invoice'
        dialog=QDialog(self)
        dialog.setWindowTitle('Saved '+('resumes' if kind=='resume' else 'invoices'))
        dialog.setAttribute(Qt.WA_DeleteOnClose,True)
        dialog.resize(650,460)
        box=QVBoxLayout(dialog)
        box.setContentsMargins(24,24,24,24)
        box.setSpacing(16)
        box.addWidget(label('Saved '+('resumes' if kind=='resume' else 'invoices'),'title'))
        box.addWidget(label('Recall a local record by phone number. Exported files are kept separately.','muted',True))
        search=QLineEdit()
        search.setPlaceholderText('Find by phone number')
        box.addWidget(search)
        listing=QListWidget()
        box.addWidget(listing,1)
        def refresh():
            listing.clear()
            for record in self.store.records(kind,search.text()):
                item=QListWidgetItem(f"{record['title']}  ·  {record['phone']}  ·  {record['created'][:10]}")
                if record.get('corrupt'):item.setText(item.text()+' · Cannot load saved data')
                item.setData(Qt.UserRole,record)
                listing.addItem(item)
            if not listing.count():
                empty=QListWidgetItem('No matching records' if search.text() else 'No saved records yet. Save a resume or invoice to find it here.')
                empty.setFlags(Qt.NoItemFlags)
                listing.addItem(empty)
        def load():
            item=listing.currentItem()
            if not item or not item.data(Qt.UserRole):
                return
            record=item.data(Qt.UserRole)
            if record.get('corrupt') or not self.restore_options(record['body']):
                Modal(dialog,'Saved record could not be opened','The saved form data is damaged or incompatible. Your exported files and other records are unchanged.').exec()
                return
            dialog.accept()
        def delete():
            item=listing.currentItem()
            if item and item.data(Qt.UserRole) and Modal(dialog,'Delete this record?','This removes the saved local record. Your exported files are kept.','Delete record',destructive=True).exec()==QDialog.Accepted:
                self.store.delete_record(item.data(Qt.UserRole)['id'])
                refresh()
        search.textChanged.connect(refresh)
        refresh()
        row=QHBoxLayout()
        row.addWidget(button('Load into form',load,True))
        row.addWidget(button('Delete record',delete))
        row.addStretch()
        row.addWidget(button('Close',dialog.reject))
        box.addLayout(row)
        dialog.exec()

    def restore_options(self,options):
        import math
        if not isinstance(options,dict):return False
        for key,value in options.items():
            widget=self.fields.get(key)
            if widget is None:continue
            if key=='design':
                try:
                    if not 0<=int(value)<len(DESIGNS):return False
                except (ValueError,TypeError,OverflowError):return False
            elif isinstance(widget,QCheckBox):
                if type(value) is not bool:return False
            elif isinstance(widget,(QSpinBox,QDoubleSpinBox)):
                try:
                    if not math.isfinite(float(value)):return False
                    if isinstance(widget,QSpinBox):int(value)
                except (ValueError,TypeError,OverflowError):return False
            elif not isinstance(value,str):return False
        if 'items' in options and hasattr(self,'items'):
            if not isinstance(options['items'],list) or any(not isinstance(row,dict) for row in options['items']):return False
        for key,value in options.items():
            widget=self.fields.get(key)
            if widget is None:
                continue
            if isinstance(widget,QComboBox):
                widget.setCurrentText(DESIGNS[int(value)] if key=='design' else str(value))
            elif isinstance(widget,QTextEdit):
                widget.setPlainText(str(value))
            elif isinstance(widget,QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget,QCheckBox):
                widget.setChecked(bool(value))
            else:
                widget.setValue(int(value) if isinstance(widget,QSpinBox) else float(value))
        if 'items' in options and hasattr(self,'items'):
            self.items.setRowCount(len(options['items']))
            for row,item in enumerate(options['items']):
                for col,key in enumerate(('description','qty','rate','tax')):
                    self.items.setItem(row,col,QTableWidgetItem(str(item.get(key,''))))
        return True


    def choose_logo(self,widget):
        path,_=QFileDialog.getOpenFileName(self,'Choose logo','','Images (*.png *.jpg *.jpeg *.webp)',options=QFileDialog.Options())
        if path:
            widget.setText(path)

    def error(self,message):
        record('operator_error',tool=self.current.name if self.current else None)
        expected=('Choose ','Enter ','Select ','Selected monitor','Scanner ','Recording ','Install ','This ','The ','No ','Cannot ','Could not ','Page ','File ','Crop ','Replacement ','Local ','PDF ','QR ','Card ','Photo ','Image ','Rectangle ','Quantity','Use ','Add ')
        friendly=message if message.startswith(expected) and len(message)<450 else 'We could not finish that action. Check the selected file and settings, then try again.'
        if 'Permission denied' in message or 'Access is denied' in message:
            friendly='The file or folder is unavailable. Close the file in other applications or choose a different output folder.'
        elif any(term in message.lower() for term in ('cannot identify image','broken document','failed to open file','no objects found','empty file')):
            friendly='This file is damaged or does not match a supported document type. Choose another copy and try again.'
        elif 'no such file' in message.lower():
            friendly='The selected file is no longer available. Choose it again or save to an existing folder.'
        self.result_message.set_state('error','Action needs attention',friendly)
        self.statusBar().showMessage('Action needs attention')
        Modal(self,'Action needs attention',friendly,details=message if friendly!=message else None).exec()

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and not self.busy:
            event.acceptProposedAction()
    def dropEvent(self,event):
        self.add_files([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()
    def closeEvent(self,event):
        if self.busy:
            Modal(self,'Work in progress','Wait for the current local task to finish before closing.').exec()
            event.ignore()
            return
        if self.recorder.running:
            try:
                self.recorder.stop()
            except Exception as error:
                self.error(str(error))
                event.ignore()
                return
        if hasattr(self,'live_timer'):
            self.live_timer.stop()
        import sqlite3
        rect=self.normalGeometry() if self.isMaximized() else self.geometry()
        try:self.store.set('window',{'x':rect.x(),'y':rect.y(),'width':rect.width(),'height':rect.height(),'maximized':self.isMaximized()})
        except (OSError,sqlite3.Error):record('window_preference_not_saved')
        record('app_closed')
        event.accept()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName(BRAND)
    app.setOrganizationName(PUBLISHER)
    app.setOrganizationDomain(QUrl(WEBSITE).host())
    from .storage import data_directory
    from .diagnostics import configure
    import sqlite3
    try:diagnostics=configure(data_directory())
    except OSError:
        QMessageBox.critical(None,'Workspace unavailable','The local application-data folder could not be created. Choose a writable user location or contact support@credonomics.in. Your documents have not been changed.')
        return 1
    record('app_started')
    def unhandled(kind,value,tb):
        record('unexpected_exception',error=value)
        QMessageBox.critical(None,'Action could not be completed','An unexpected application error occurred. Close and reopen the application before continuing. No diagnostic data is uploaded. Contact support@credonomics.in if it happens again.')
    sys.excepthook=unhandled
    try:window=MainWindow()
    except (OSError,sqlite3.Error,ValueError,TypeError) as error:
        record('startup_failed',error=error)
        QMessageBox.critical(None,'Workspace unavailable','Local settings could not be opened. Check folder permissions and available disk space. If the settings database is damaged, keep a backup and contact support@credonomics.in. Your documents have not been changed.')
        return 1
    window.restore_window(first_launch=True)
    window.show()
    import threading
    from .tempfiles import cleanup_stale_workspaces
    def cleanup():
        try:cleanup_stale_workspaces()
        except OSError:record('temporary_cleanup_unavailable')
    threading.Thread(target=cleanup,daemon=True,name='CredoNomics temporary cleanup').start()
    return app.exec()
