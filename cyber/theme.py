# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Shared UI tokens. Processing code has no dependency on this module."""
from string import Template
import sys
from pathlib import Path
from PySide6.QtGui import QColor

SPACE=(4,8,12,16,20,24,32,40,48)
TYPE={'page':24,'hero':24,'section':15,'card':14,'body':13,'secondary':12,'caption':12,'label':12}
RADIUS={'control':6,'input':8,'panel':10,'overlay':12}
MOTION={'hover':120,'navigation':180,'feedback':160}
COLORS=dict(background='#f7f8fa',surface='#ffffff',elevated='#ffffff',sidebar='#141d2a',
    sidebar_hover='#202d3d',sidebar_active='#243d45',sidebar_text='#c5ceda',sidebar_muted='#97a6b9',
    text='#192a39',secondary='#5e7082',muted='#65788c',border='#e0e6ec',subtle='#f0f3f6',
    accent='#007d70',accent_ink='#007d70',accent_hover='#006c61',accent_soft='#e9f5f2',accent_text='#ffffff',
    success='#137653',success_soft='#edf8f2',warning='#8c5a15',warning_soft='#fff6e5',
    error='#b03a47',error_soft='#fff0f1',focus='#007d70',preview='#e9eef2',
    information='#285e9b',information_soft='#edf3fb',disabled='#73808d',accent_pressed='#005c53',
    hero='#f2f8f6',stroke_strong='#bac7d0')

DARK=dict(background='#111a22',surface='#192630',elevated='#21323e',sidebar='#101922',
    sidebar_hover='#21323e',sidebar_active='#214c4a',sidebar_text='#d2dfe8',sidebar_muted='#a4b6c5',
    text='#e9f0f5',secondary='#b3c3cf',muted='#a4b7c6',border='#344753',subtle='#22333f',
    accent='#65d6c1',accent_ink='#8ae3d1',accent_hover='#8ae3d1',accent_pressed='#41bca6',
    accent_soft='#203e3b',accent_text='#102620',success='#88dfb6',success_soft='#1b3b31',
    warning='#f1ca81',warning_soft='#423723',error='#f6a9b1',error_soft='#462c35',
    information='#a5caff',information_soft='#24394f',focus='#8ae3d1',preview='#0d141b',
    disabled='#879ba9',hero='#1a2c32',stroke_strong='#607987')


def system_high_contrast():
    if sys.platform!='win32':return False
    import ctypes
    class HighContrast(ctypes.Structure):
        _fields_=[('size',ctypes.c_uint),('flags',ctypes.c_uint),('scheme',ctypes.c_wchar_p)]
    value=HighContrast();value.size=ctypes.sizeof(value)
    return bool(ctypes.windll.user32.SystemParametersInfoW(0x42,value.size,ctypes.byref(value),0) and value.flags&1)


def resolve_mode(mode):
    if mode=='High contrast' or system_high_contrast():return 'High contrast'
    if mode!='System':return 'Dark' if mode=='Dark' else 'Light'
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    app=QGuiApplication.instance()
    if app and app.styleHints().colorScheme()==Qt.ColorScheme.Dark:return 'Dark'
    if sys.platform=='win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                return 'Light' if winreg.QueryValueEx(key,'AppsUseLightTheme')[0] else 'Dark'
        except OSError:pass
    return 'Light'


def native_window_theme(window,dark):
    """Use standard Windows caption rendering; unsupported OS versions fall back."""
    if sys.platform!='win32':return False
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.platformName()!='windows':return False
    try:
        import ctypes
        value=ctypes.c_int(bool(dark))
        function=ctypes.WinDLL('dwmapi').DwmSetWindowAttribute
        function.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint]
        function.restype=ctypes.c_long
        return function(int(window.winId()),20,ctypes.byref(value),ctypes.sizeof(value))==0
    except OSError:return False


def tokens(accent=None,mode='Light'):
    values=dict(COLORS)
    mode=resolve_mode(mode)
    if mode=='Dark':values.update(DARK)
    if mode=='High contrast':
        values.update({key:'#000000' for key in ('background','surface','elevated','sidebar','sidebar_hover','sidebar_active','subtle','preview','hero','accent_soft','success_soft','warning_soft','error_soft','information_soft')})
        values.update({key:'#ffffff' for key in ('text','secondary','muted','sidebar_text','sidebar_muted','border','stroke_strong')})
        values.update(accent='#00ffff',accent_ink='#00ffff',accent_hover='#ffff00',accent_pressed='#ffffff',accent_text='#000000',focus='#ffff00',success='#8dff9e',warning='#ffff00',error='#ffb9c6',information='#00ffff',disabled='#aaaaaa')
    values['dark']=mode!='Light'
    values['high_contrast']=mode=='High contrast'
    if mode=='High contrast':return values
    if accent and QColor(accent).isValid():
        color=QColor(accent)
        values.update(accent=color.name(),accent_hover=color.darker(115).name(),focus=color.name())
        dark=mode=='Dark'
        values['accent_soft']=QColor.fromRgbF(*(v*.18+.08 if dark else v*.08+.92 for v in color.getRgbF()[:3])).name()
        def linear(n):
            return n/12.92 if n<=.04045 else ((n+.055)/1.055)**2.4
        luminance=sum(a*linear(b) for a,b in zip((.2126,.7152,.0722),color.getRgbF()[:3]))
        values['accent_text']='#ffffff' if (1.05/(luminance+.05))>=4.5 else '#14212b'
        ink=QColor(color)
        def white_contrast(value):
            luminance=sum(a*linear(b) for a,b in zip((.2126,.7152,.0722),value.getRgbF()[:3]))
            return 1.05/(luminance+.05)
        if dark:
            base=QColor(values['surface'])
            base_luminance=sum(a*linear(b) for a,b in zip((.2126,.7152,.0722),base.getRgbF()[:3]))
            def surface_contrast(value):
                lum=sum(a*linear(b) for a,b in zip((.2126,.7152,.0722),value.getRgbF()[:3]))
                return (max(lum,base_luminance)+.05)/(min(lum,base_luminance)+.05)
            while surface_contrast(ink)<4.5:ink=ink.lighter(115) if ink.value() else QColor('#777777')
        else:
            while white_contrast(ink)<4.5:ink=ink.darker(112)
        values['accent_ink']=ink.name()
        values['focus']=ink.name()
    return values


def stylesheet(values=None):
    values=values or COLORS
    values=dict(values)|{'font_'+key:value for key,value in TYPE.items()}|{'radius_'+key:value for key,value in RADIUS.items()}
    css=Template('''
* {font-family: "Lato"; font-size:${font_body}px; color:$text;}
QMainWindow,QDialog {background:$background;}
QWidget#page {background:$background;}
QFrame#sidebar {background:$sidebar; border:0;}
QLabel#brand {color:white; font-weight:700; font-size:17px;}
QLabel#brandSub {color:$sidebar_muted; font-size:11px;}
QLabel#sidebarPublisher {color:$sidebar_text; font-size:12px; font-weight:600;}
QFrame#publisherFooter {border:0; border-top:1px solid $sidebar_hover;}
QFrame#workspacePublisherFooter {background:$background; border:0; border-top:1px solid $border;}
QPushButton#publisherLink {background:transparent; border:0; color:$accent_ink; font-size:11px; padding:1px 0; min-height:16px; text-align:left;}
QPushButton#publisherLink:hover {text-decoration:underline;}
QPushButton#publisherLink:focus {border:1px solid $accent;}
QLabel#publisherTitle {font-size:18px; font-weight:700;}
QLabel#mark {background:$accent; color:$accent_text; border-radius:10px; font-size:23px; font-weight:700;}
QFrame#topbar {background:$surface; border-bottom:1px solid $border;}
QLabel#headerTitle {font-size:15px; font-weight:700;}
QLabel#title {font-size:${font_page}px; font-weight:700;}
QLabel#sectionTitle {font-size:${font_section}px; font-weight:700;}
QLabel#cardTitle {font-size:${font_card}px; font-weight:700;}
QLabel#muted,QLabel#cardDescription {color:$secondary; font-size:${font_secondary}px;}
QLabel#caption {color:$secondary; font-size:${font_caption}px;}
QLabel#eyebrow {color:$secondary; font-size:11px; font-weight:700;}
QLabel#pill {background:$accent_soft; color:$accent_ink; border:1px solid $border; border-radius:5px; padding:5px 9px; font-size:10px; font-weight:700;}
QFrame#panel,QFrame#card {background:$surface; border:1px solid $border; border-radius:10px;}
QFrame#hero {background:$surface; border:1px solid $border; border-radius:12px;}
QLabel#heroTitle {font-size:${font_hero}px; font-weight:700;}
QLabel#heroBody {color:$secondary; font-size:13px;}
QFrame#quickStrip {background:$surface; border:1px solid $border; border-radius:8px;}
QLabel#note {color:$secondary; background:$subtle; border-radius:6px; padding:12px; font-size:12px;}
QLabel#toolIcon {background:$accent_soft; border-radius:8px;}
QPushButton {background:$surface; border:1px solid $border; border-radius:6px; padding:8px 12px; font-weight:600; min-height:18px;}
QPushButton:hover {background:$subtle; border-color:#bdcbd5;}
QPushButton:pressed {background:$accent_soft;}
QPushButton:focus {border:2px solid $focus; padding:7px 11px;}
QPushButton:disabled {color:$disabled; background:$subtle; border-color:$border;}
QPushButton#primary {background:$accent; color:$accent_text; border-color:$accent;}
QPushButton#primary:hover {background:$accent_hover;}
QPushButton#primary:pressed {background:$accent_pressed;}
QPushButton#primary:disabled {background:$subtle; border-color:$border; color:$disabled;}
QPushButton#quiet {background:transparent; border:1px solid transparent;}
QPushButton#quiet:hover {background:$subtle;}
QPushButton#danger {background:$error_soft; color:$error; border-color:#efc5ca;}
QPushButton#sidebarButton {background:transparent; color:$sidebar_text; border-color:transparent; text-align:left; padding:10px;}
QPushButton#sidebarButton:hover {background:$sidebar_hover;}
QPushButton#sidebarButton:checked {background:$sidebar_active; color:#89e0ce;}
QPushButton#sidebarButton:focus {border:2px solid #89e0ce;}
QListWidget#nav {background:transparent; border:0; outline:0; padding:0;}
QListWidget#nav::item {color:$sidebar_text; padding:7px 10px; margin:1px 0; border:1px solid transparent; border-radius:6px;}
QListWidget#nav::item:selected {background:$sidebar_active; color:$sidebar_text; border:1px solid #6cbfae; border-left:3px solid #89e0ce; padding-left:8px;}
QListWidget#nav::item:hover {background:$sidebar_hover;}
QListWidget#nav::item:focus {border:1px solid #89e0ce;}
QListWidget#nav::item:disabled {color:$sidebar_muted; background:transparent; font-size:10px; font-weight:700; padding:16px 8px 5px 8px;}
QLineEdit,QTextEdit,QComboBox,QSpinBox,QDoubleSpinBox {background:$surface; border:1px solid $stroke_strong; border-radius:${radius_input}px; padding:7px 8px; selection-background-color:$accent; selection-color:$accent_text; min-height:18px;}
QLineEdit:focus,QTextEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border:2px solid $focus; padding:7px;}
QLineEdit:disabled,QComboBox:disabled,QSpinBox:disabled {background:$subtle; color:$disabled;}
QComboBox::drop-down {border:0; width:24px;}
QComboBox QAbstractItemView {background:$surface; selection-background-color:$accent_soft; selection-color:$text; padding:6px; border:1px solid $border;}
QCheckBox {spacing:9px; padding:3px 0;}
QCheckBox::indicator {width:18px; height:18px; border:1px solid $stroke_strong; border-radius:4px; background:$surface;}
QCheckBox::indicator:checked {background:$accent; border-color:$accent;}
QCheckBox:focus {outline:2px solid $focus;}
QCheckBox::indicator:focus {border:2px solid $focus;}
QListWidget,QTableWidget {background:$surface; border:1px solid $border; border-radius:6px; outline:0;}
QListWidget::item {padding:8px;}
QListWidget::item:selected {background:$accent_soft; color:$text;}
QListWidget::item:focus {border:1px solid $focus;}
QHeaderView::section {background:$subtle; color:$secondary; padding:8px; border:0; font-size:11px; font-weight:700;}
QTableWidget {gridline-color:$border;}
QScrollArea {border:0; background:transparent;}
QScrollArea>QWidget>QWidget {background:transparent;}
QScrollBar:vertical {background:transparent; width:7px; margin:0;}
QScrollBar::handle:vertical {background:#c9d2db; border-radius:3px; min-height:28px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:none;}
QSplitter::handle {background:transparent; width:12px; height:12px;}
QProgressBar {border:0; background:$accent_soft; border-radius:2px; max-height:4px;}
QProgressBar::chunk {background:$accent;}
QStatusBar {background:$surface; border-top:1px solid $border; color:$secondary; font-size:11px;}
QStatusBar::item {border:0;}
QTabWidget::pane {border:0; background:$surface;}
QTabBar::tab {background:transparent; color:$secondary; border-bottom:2px solid transparent; padding:12px 14px;}
QTabBar::tab:selected {color:$accent; border-bottom:2px solid $accent;}
QTabBar::tab:focus {background:$accent_soft;}
QFrame#commandResults {background:$elevated; border:1px solid $border; border-radius:8px;}
QListWidget#commandResults {background:$elevated; border:1px solid $stroke_strong; border-radius:${radius_overlay}px; padding:4px;}
QListWidget#commandResults::item {padding:10px; border-radius:6px;}
QListWidget#commandResults::item:selected {background:$accent_soft; color:$text;}
QFrame#settingsGroup {background:$surface; border:1px solid $border; border-radius:${radius_panel}px;}
QFrame#actionBar {background:$surface; border:1px solid $border; border-radius:${radius_panel}px;}
QLabel#workflowContext {color:$accent_ink; background:$accent_soft; padding:5px 8px; border-radius:6px; font-size:12px;}
QToolTip {background:$sidebar; color:white; border:0; padding:7px;}
''').substitute(values)
    assets=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'assets/icons'
    up=(assets/('arrow-up-light.svg' if values.get('dark') else 'arrow-up.svg')).as_posix()
    down=(assets/('chevron-down-light.svg' if values.get('dark') else 'chevron-down.svg')).as_posix()
    check=(assets/('check-white.svg' if values['accent_text']=='#ffffff' else 'check-dark.svg')).as_posix()
    css+=f'''
QComboBox::down-arrow {{image:url("{down}");width:12px;height:12px;}}
QSpinBox::up-button,QDoubleSpinBox::up-button {{subcontrol-origin:border;subcontrol-position:top right;width:22px;height:17px;border-left:1px solid #e0e6ec;}}
QSpinBox::down-button,QDoubleSpinBox::down-button {{subcontrol-origin:border;subcontrol-position:bottom right;width:22px;height:17px;border-left:1px solid #e0e6ec;}}
QSpinBox::up-arrow,QDoubleSpinBox::up-arrow {{image:url("{up}");width:10px;height:10px;}}
QSpinBox::down-arrow,QDoubleSpinBox::down-arrow {{image:url("{down}");width:10px;height:10px;}}
QCheckBox::indicator:checked {{image:url("{check}");}}
'''
    return css
