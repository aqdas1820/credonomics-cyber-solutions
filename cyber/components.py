# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Small reusable Qt components for the existing desktop workflow."""
import sys
from pathlib import Path
from functools import lru_cache
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, Property, QEasingCurve, QRectF,QTimer
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QLabel,QPushButton,QFrame,QVBoxLayout,QHBoxLayout,QAbstractButton,
    QDialog,QTextEdit,QGraphicsDropShadowEffect,QListWidget,QGridLayout,QFormLayout,QWidget,QScrollArea,QApplication)
from .theme import COLORS,MOTION,native_window_theme

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
ICONS={'Print':'printer','Scan':'scan-line','PVC Tool':'id-card','Auto ID Card':'contact-round',
 'Signature Check':'badge-check','Auto Crop':'crop','Portal PDF Pack':'file-down','PDF Editor':'file-pen-line',
 'Edit Screenshot':'scan-text','Photo Print':'image','Photo & Sign':'scan-face','PAN Tool':'id-card',
 'Merge Tool':'combine','Compress':'file-down','Convert':'repeat-2','Mini Print':'layout-grid',
 'QR Generator':'qr-code','Resume Maker':'file-user','Bill Maker':'receipt','Screen Recording':'screen-share'}
GROUPS=[('Documents',('Print','PDF Editor','Merge Tool','Compress','Convert','Mini Print')),
 ('Identity & photos',('PVC Tool','Auto ID Card','Photo Print','Photo & Sign','PAN Tool')),
 ('Capture',('Scan','Auto Crop','Edit Screenshot','Screen Recording')),
 ('Business & utilities',('QR Generator','Resume Maker','Bill Maker','Signature Check','Portal PDF Pack'))]
SHORT={'Print':'Prepare and print documents','Scan':'Paper to a multi-page PDF','PVC Tool':'Precision card layouts',
 'Auto ID Card':'Front and back, neatly paired','Signature Check':'Inspect document signatures','Auto Crop':'Straighten document edges',
 'Portal PDF Pack':'Attachments within portal limits','PDF Editor':'Edit, redact and annotate','Edit Screenshot':'Refine a selected image area',
 'Photo Print':'Passport photos, ready to print','Photo & Sign':'Exact pixels. Exact file limits.','PAN Tool':'Application photo attachments',
 'Merge Tool':'Bring your files together','Compress':'Smaller files, clear limits','Convert':'A format for every workflow',
 'Mini Print':'More pages on each sheet','QR Generator':'Create a crisp, scannable code','Resume Maker':'Polished resumes in ten styles',
 'Bill Maker':'Branded invoices and UPI QR','Screen Recording':'Capture with privacy masks'}


@lru_cache(maxsize=512)
def icon(name,color=COLORS['secondary'],size=20):
    path=ROOT/'assets/icons'/(name+'.svg')
    try:data=path.read_text(encoding='utf-8').replace('currentColor',color).encode()
    except OSError:
        from .diagnostics import record
        record('optional_icon_unavailable')
        return QIcon()
    renderer=QSvgRenderer(data)
    ratio=2
    pixmap=QPixmap(size*ratio,size*ratio)
    pixmap.fill(Qt.transparent)
    painter=QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return QIcon(pixmap)


def label(text,name='',wrap=False):
    item=QLabel(text)
    item.setObjectName(name)
    item.setWordWrap(wrap)
    item.setTextFormat(Qt.PlainText)
    return item


class ActionButton(QPushButton):
    """Keep dynamic operation labels accurate for assistive technology."""
    def setText(self,text):
        old_text=self.text()
        old_name=self.accessibleName()
        super().setText(text)
        if text and (not old_name or old_name==old_text):self.setAccessibleName(text)


def button(text,callback=None,primary=False,icon_name=None,quiet=False):
    item=ActionButton(text)
    item.setCursor(Qt.PointingHandCursor)
    item.setMinimumHeight(34)
    if primary:
        item.setObjectName('primary')
    elif quiet:
        item.setObjectName('quiet')
    if icon_name:
        item.setProperty('iconName',icon_name)
        item.setIcon(icon(icon_name,COLORS['accent_text'] if primary else COLORS['secondary'],17))
        item.setIconSize(QSize(17,17))
    if callback:
        item.clicked.connect(callback)
    item.setAccessibleName(text or icon_name or 'Action')
    return item


def widget_theme(widget):
    current=widget
    while current is not None:
        if isinstance(getattr(current,'theme',None),dict):return current.theme
        current=current.parentWidget()
    return COLORS


def fit_dialog(dialog,scroll_content=False,available=None):
    """Bound transient dialogs to the work area and release them on close."""
    dialog.setAttribute(Qt.WA_DeleteOnClose,True)
    if available is None:
        screen=dialog.screen()
        if screen is None:return
        available=screen.availableGeometry()
    width=max(320,available.width()-32)
    height=max(240,available.height()-40)
    if scroll_content and dialog.height()>height:
        content=QWidget()
        content.setLayout(dialog.layout())
        content.setMinimumWidth(0)
        area=QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(content)
        outer=QVBoxLayout(dialog)
        outer.setContentsMargins(0,0,0,0)
        outer.addWidget(area)
    dialog.setMinimumSize(min(dialog.minimumWidth(),width),min(dialog.minimumHeight(),height))
    dialog.setMaximumSize(width,height)
    dialog.resize(min(dialog.width(),width),min(dialog.height(),height))
    native_window_theme(dialog,widget_theme(dialog).get('dark',False))


class SettingsGroup(QFrame):
    """A labelled configuration surface; owns no processing logic."""
    def __init__(self,title,description=''):
        super().__init__()
        self.setObjectName('settingsGroup')
        self.box=QVBoxLayout(self)
        self.box.setContentsMargins(12,12,12,12)
        self.box.setSpacing(8)
        self.box.addWidget(label(title,'eyebrow'))
        if description:self.box.addWidget(label(description,'caption',True))
        self.form=QFormLayout()
        self.form.setContentsMargins(0,0,0,0)
        self.form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        self.form.setVerticalSpacing(8)
        self.box.addLayout(self.form)


class DeviceSelector(QFrame):
    """A real device selector with one compact refresh action."""
    def __init__(self,select,refresh,title):
        super().__init__()
        row=QHBoxLayout(self)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(8)
        row.addWidget(select,1)
        action=button('',refresh,icon_name='repeat-2',quiet=True)
        action.setFixedWidth(34)
        action.setToolTip(title)
        action.setAccessibleName(title)
        row.addWidget(action)


class DashboardGrid(QFrame):
    def __init__(self,sections):
        super().__init__()
        self.sections=sections
        self.grid=QGridLayout(self)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setSpacing(20)
        self.columns=2
        for i,section in enumerate(sections):self.grid.addWidget(section,i//2,i%2,Qt.AlignTop)
        self.grid.setColumnStretch(0,1)
        self.grid.setColumnStretch(1,1)
    def resizeEvent(self,event):
        columns=2 if self.width()>=920 else 1
        if columns!=self.columns:
            self.columns=columns
            while self.grid.count():self.grid.takeAt(0)
            for i,section in enumerate(self.sections):self.grid.addWidget(section,i//columns,i%columns,Qt.AlignTop)
            for i in range(2):self.grid.setColumnStretch(i,1 if i<columns else 0)
        super().resizeEvent(event)


class IconBadge(QLabel):
    def __init__(self,name,size=38,color=None,parent=None):
        super().__init__(parent)
        self.icon_name=name
        self.setObjectName('toolIcon')
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(size,size)
        self.setPixmap(icon(name,color or COLORS['accent'],20).pixmap(20,20))


class ToolCard(QAbstractButton):
    def __init__(self,tool,callback,parent=None):
        super().__init__(parent)
        self.tool=tool
        self.theme=COLORS
        self._hover=0.
        self.animation=QPropertyAnimation(self,b'hoverAmount',self)
        self.animation.setDuration(MOTION['hover'])
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.setFixedHeight(76)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(tool.name)
        self.setAccessibleDescription(tool.description)
        self.setToolTip(tool.description)
        box=QHBoxLayout(self)
        box.setContentsMargins(12,10,24,10)
        box.setSpacing(10)
        box.addWidget(IconBadge(ICONS[tool.name],32))
        words=QVBoxLayout()
        words.setSpacing(5)
        words.addWidget(label(tool.name,'cardTitle'))
        description=label(SHORT[tool.name],'cardDescription',True)
        description.setMaximumHeight(34)
        words.addWidget(description)
        box.addLayout(words,1)
        for widget in self.findChildren(QLabel):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.clicked.connect(callback)
    def get_hover(self):
        return self._hover
    def set_hover(self,value):
        self._hover=value
        self.update()
    hoverAmount=Property(float,get_hover,set_hover)
    def enterEvent(self,event):
        self.animation.stop()
        self.animation.setStartValue(self._hover)
        self.animation.setEndValue(1.)
        self.animation.start()
        super().enterEvent(event)
    def leaveEvent(self,event):
        self.animation.stop()
        self.animation.setStartValue(self._hover)
        self.animation.setEndValue(0.)
        self.animation.start()
        super().leaveEvent(event)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Return,Qt.Key_Enter):
            self.click()
            event.accept()
        else:
            super().keyPressEvent(event)
    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg=QColor(self.theme['surface'])
        tint=QColor(self.theme['accent_soft'])
        bg=QColor.fromRgbF(*(a+(b-a)*self._hover*.45 for a,b in zip(bg.getRgbF()[:3],tint.getRgbF()[:3])))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor(self.theme['focus'] if self.hasFocus() else self.theme['stroke_strong'] if self._hover>.2 else self.theme['border']),2 if self.hasFocus() else 1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),8,8)
        icon('chevron-right',self.theme['accent_ink'] if self._hover else self.theme['secondary'],15).paint(painter,self.width()-23,(self.height()-15)//2,15,15)


class ToolSection(QFrame):
    def __init__(self,title,tools,callback):
        super().__init__()
        self.box=QVBoxLayout(self)
        self.box.setContentsMargins(0,0,0,0)
        self.box.setSpacing(12)
        self.box.setAlignment(Qt.AlignTop)
        heading=QHBoxLayout()
        heading.addWidget(label(title,'sectionTitle'))
        self.count=label(str(len(tools))+' tools','caption')
        heading.addWidget(self.count)
        heading.addStretch()
        self.box.addLayout(heading)
        from PySide6.QtWidgets import QGridLayout
        self.grid=QGridLayout()
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignTop)
        self.box.addLayout(self.grid)
        self.cards=[ToolCard(tool,lambda checked=False,n=tool.name:callback(n)) for tool in tools]
        self.visible_cards=list(self.cards)
        self.columns=0
        self.reflow()
    def filter(self,text):
        self.visible_cards=[card for card in self.cards if text in (card.tool.name+' '+card.tool.description+' '+card.tool.group).lower()]
        for card in self.cards:
            card.setVisible(card in self.visible_cards)
        self.count.setText(f'{len(self.visible_cards)} tools')
        self.setVisible(bool(self.visible_cards))
        self.columns=0
        self.reflow()
    def reflow(self):
        columns=3 if self.width()>=920 else 2 if self.width()>=450 else 1
        if columns==self.columns:
            return
        self.columns=columns
        while self.grid.count():
            self.grid.takeAt(0)
        for i,card in enumerate(self.visible_cards):
            self.grid.addWidget(card,i//columns,i%columns)
        for i in range(3):
            self.grid.setColumnStretch(i,1 if i<columns else 0)
    def resizeEvent(self,event):
        self.reflow()
        super().resizeEvent(event)


class FileDropZone(QPushButton):
    filesDropped=Signal(list)
    def __init__(self,callback):
        super().__init__()
        self.setObjectName('dropZone')
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.compact=False
        self.theme=COLORS
        self.setAccessibleName('Choose or drop local files')
        self.apply_theme(COLORS)
        box=QHBoxLayout(self)
        box.setContentsMargins(12,12,12,12)
        box.setSpacing(10)
        badge=IconBadge('upload',32)
        box.addWidget(badge)
        words=QVBoxLayout()
        words.setSpacing(5)
        self.title=label('Browse files','sectionTitle')
        self.subtitle=label('Drop PDFs, images or Office files','caption',True)
        words.addWidget(self.title)
        words.addWidget(self.subtitle)
        box.addLayout(words,1)
        self.setToolTip('Open PDF, image or Office documents from this PC')
        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.clicked.connect(callback)
    def apply_theme(self,theme):
        self.theme=theme
        self.setStyleSheet(f'QPushButton#dropZone {{border:1px dashed {theme["stroke_strong"]};background:{theme["accent_soft"]};border-radius:8px;padding:4px;}} QPushButton#dropZone:hover,QPushButton#dropZone:focus {{border:2px solid {theme["focus"]};padding:3px;}}')
        if hasattr(self,'title'):self.set_compact(self.compact)
        for badge in self.findChildren(IconBadge):
            badge.setPixmap(icon(badge.icon_name,theme['accent_ink'],20).pixmap(20,20))
    def set_compact(self,compact):
        self.compact=bool(compact)
        self.setFixedHeight(52 if compact else 100)
        self.title.setText('Add more files' if compact else 'Browse files')
        self.subtitle.setVisible(not compact)
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self,event):
        self.filesDropped.emit([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()


class DocumentList(QListWidget):
    def paintEvent(self,event):
        super().paintEvent(event)
        if not self.count():
            painter=QPainter(self.viewport())
            painter.setPen(QColor(widget_theme(self)['secondary']))
            painter.drawText(self.viewport().rect().adjusted(8,8,-8,-8),Qt.AlignCenter,'No files added yet\nChoose a local file to begin.')


class EmptyState(QFrame):
    def __init__(self,callback):
        super().__init__()
        box=QVBoxLayout(self)
        self.box=box
        box.setContentsMargins(24,24,24,24)
        box.addStretch()
        self.badge=IconBadge('files',52)
        box.addWidget(self.badge,0,Qt.AlignCenter)
        box.addSpacing(12)
        self.title=label('No document selected','sectionTitle')
        self.title.setAlignment(Qt.AlignCenter)
        self.body=label('Choose a PDF or image to get started.\nYour files stay on this PC.','muted',True)
        self.body.setAlignment(Qt.AlignCenter)
        box.addWidget(self.title)
        box.addWidget(self.body)
        box.addSpacing(12)
        self.action=button('Choose a file',callback,icon_name='folder-open')
        box.addWidget(self.action,0,Qt.AlignCenter)
        box.addStretch()

    def set_compact(self,compact):
        self.badge.setVisible(not compact)
        self.body.setVisible(not compact)
        self.box.setContentsMargins(12 if compact else 24,12 if compact else 24,12 if compact else 24,12 if compact else 24)
        self.box.setSpacing(6 if compact else 10)
        for index in range(self.box.count()):
            spacer=self.box.itemAt(index).spacerItem()
            if spacer and spacer.sizeHint().height()>0:spacer.changeSize(0,4 if compact else 12)


class Feedback(QFrame):
    def __init__(self):
        super().__init__()
        box=QHBoxLayout(self)
        box.setContentsMargins(12,9,12,9)
        box.setSpacing(10)
        self.symbol=QLabel()
        self.symbol.setFixedWidth(20)
        box.addWidget(self.symbol,0,Qt.AlignTop)
        words=QVBoxLayout()
        words.setSpacing(3)
        self.title=label('Ready to begin','sectionTitle')
        self.body=label('','muted',True)
        words.addWidget(self.title)
        words.addWidget(self.body)
        box.addLayout(words,1)
        self.dismiss=button('',self.hide,icon_name='x',quiet=True)
        self.dismiss.setToolTip('Dismiss message')
        self.dismiss.setAccessibleName('Dismiss message')
        self.dismiss.setFixedSize(32,32)
        box.addWidget(self.dismiss,0,Qt.AlignTop)
        self.timer=QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.expire)
        self.set_state('info','Ready to begin','Choose your files and adjust the settings.')
        self.hide()
    def set_state(self,state,title,body=''):
        self.state=state
        self.timer.stop()
        theme=widget_theme(self)
        tone={'info':('info','information','information_soft'),'success':('circle-check','success','success_soft'),
              'warning':('triangle-alert','warning','warning_soft'),'error':('triangle-alert','error','error_soft'),
              'processing':('clock','accent','accent_soft')}[state]
        self.setStyleSheet(f'Feedback {{background:{theme[tone[2]]};border:1px solid {theme["border"]};border-radius:8px;}}')
        self.symbol.setPixmap(icon(tone[0],theme[tone[1]],18).pixmap(18,18))
        self.title.setText(title)
        self.title.setStyleSheet(f'color:{theme[tone[1]]};font-size:13px;')
        self.body.setText(body)
        self.body.setVisible(bool(body) and self.window().height()>=600)
        self.setToolTip(body)
        self.dismiss.setVisible(state!='processing')
        self.setAccessibleName(title+': '+body)
        self.show()
        if state=='success':self.timer.start(10000)
    def setText(self,text):
        self.set_state('info','Workspace update',text)
    def expire(self):
        focused=QApplication.focusWidget()
        if focused is not None and (focused is self or self.isAncestorOf(focused)):
            self.timer.start(5000)
        else:self.hide()
    def text(self):
        return self.body.text()


class Modal(QDialog):
    def __init__(self,parent,title,description,primary='Done',destructive=False,details=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        self.setMaximumWidth(620)
        box=QVBoxLayout(self)
        box.setContentsMargins(28,24,28,24)
        box.setSpacing(16)
        box.addWidget(IconBadge('triangle-alert' if destructive or details else 'info',40))
        box.addWidget(label(title,'title',True))
        box.addWidget(label(description,'muted',True))
        if details:
            disclosure=button('Show technical details',quiet=True)
            diagnostic=QTextEdit()
            diagnostic.setPlainText(details)
            diagnostic.setReadOnly(True)
            diagnostic.setMaximumHeight(140)
            diagnostic.hide()
            disclosure.clicked.connect(lambda:diagnostic.setVisible(not diagnostic.isVisible()))
            box.addWidget(disclosure)
            box.addWidget(diagnostic)
        actions=QHBoxLayout()
        actions.addStretch()
        if primary!='Done':
            actions.addWidget(button('Cancel',self.reject))
        self.accept_button=button(primary,self.accept,True)
        if destructive:
            self.accept_button.setObjectName('danger')
        actions.addWidget(self.accept_button)
        box.addLayout(actions)
        fit_dialog(self,scroll_content=True)


def recolor_buttons(root,theme):
    for badge in root.findChildren(IconBadge):
        badge.setPixmap(icon(badge.icon_name,theme['accent_ink'],20).pixmap(20,20))
    for item in root.findChildren(QPushButton):
        name=item.property('iconName')
        if name:
            color=theme['accent_text'] if item.objectName()=='primary' else theme['sidebar_text'] if item.objectName()=='sidebarButton' else theme['secondary']
            item.setIcon(icon(name,color,17))
