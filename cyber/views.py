# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Presentation for the existing MainWindow; processing stays in ui.py/engine.py."""
import sys
import shutil
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt,QSize,QEvent,QTimer,QUrl,QVariantAnimation,QEasingCurve
from PySide6.QtGui import QFont,QColor,QPixmap,QShortcut,QKeySequence,QPageLayout,QIcon
from PySide6.QtWidgets import (QWidget,QFrame,QLabel,QVBoxLayout,QHBoxLayout,QFormLayout,QListWidget,
    QListWidgetItem,QLineEdit,QTextEdit,QComboBox,QSpinBox,QDoubleSpinBox,QCheckBox,QScrollArea,
    QStackedWidget,QSplitter,QProgressBar,QDialog,QTabWidget,QTableWidget,QTableWidgetItem,
    QHeaderView,QAbstractItemView,QFileDialog,QColorDialog,QSizePolicy,QGraphicsDropShadowEffect)
from PySide6.QtPrintSupport import QPrinterInfo,QPrinter
from . import BRAND,__version__,COPYRIGHT,COPYRIGHT_SHORT,PUBLISHER,WEBSITE,SUPPORT_EMAIL,SUPPORT_PHONE
from .catalog import TOOLS,BY_NAME
from .components import (label,button,icon,IconBadge,ToolSection,FileDropZone,EmptyState,Feedback,Modal,GROUPS,ICONS,recolor_buttons,DocumentList,SettingsGroup,DashboardGrid,DeviceSelector,fit_dialog)
from .theme import COLORS,tokens,stylesheet,MOTION,native_window_theme
from .tool_layouts import ACTIONS,FIELD_GROUPS,PURPOSE,SEARCH_ALIASES
from .images import model_path
from .licensing import machine_id
from .glass import GlassSurface
from .distribution import is_commercial_build,is_store_build,MODEL_UNAVAILABLE


def scroll(widget):
    area=QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setWidget(widget)
    return area


class DesktopUI:
    def setup_ui(self):
        self.appearance=dict(self.store.get('appearance',{}))
        self.theme=tokens(self.store.get('branding',{}).get('accent'),self.appearance.get('theme','Light'))
        self.setStyleSheet(stylesheet(self.theme))
        self.setWindowTitle(BRAND)
        asset_root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
        self.setWindowIcon(QIcon(str(asset_root/'assets/brandmark.svg')))
        self.resize(1480,960)
        self.setMinimumSize(760,480)
        self.setAcceptDrops(True)
        root=QWidget()
        self.setCentralWidget(root)
        shell=QHBoxLayout(root)
        shell.setContentsMargins(0,0,0,0)
        shell.setSpacing(0)
        self.appearance=dict(self.store.get('appearance',{}))
        self._sidebar_collapsed=bool(self.appearance.get('compact_menu',False))
        self.sidebar=GlassSurface(dark=True)
        self.sidebar.setObjectName('sidebar')
        self.sidebar.setFixedWidth(232)
        navbox=QVBoxLayout(self.sidebar)
        navbox.setContentsMargins(14,22,14,16)
        navbox.setSpacing(8)
        brandrow=QHBoxLayout()
        brandrow.setSpacing(10)
        self.brand_mark=label('C','mark')
        self.brand_mark.setAlignment(Qt.AlignCenter)
        self.brand_mark.setFixedSize(38,38)
        self.brand_mark.setAccessibleName(BRAND+' · '+PUBLISHER)
        brandrow.addWidget(self.brand_mark)
        self.brand_words=QWidget()
        words=QVBoxLayout(self.brand_words)
        words.setContentsMargins(0,0,0,0)
        words.setSpacing(4)
        self.brand_name=label('CredoNomics','brand')
        self.brand_subtitle=label('CYBER SOLUTIONS','brandSub')
        words.addWidget(self.brand_name)
        words.addWidget(self.brand_subtitle)
        brandrow.addWidget(self.brand_words,1)
        navbox.addLayout(brandrow)
        self.publisher_brand_block=QWidget()
        publisher_top=QVBoxLayout(self.publisher_brand_block)
        publisher_top.setContentsMargins(0,8,0,4)
        publisher_top.setSpacing(3)
        publisher_top.addWidget(label('A product of','brandSub'))
        self.sidebar_publisher=label(PUBLISHER,'sidebarPublisher',True)
        publisher_top.addWidget(self.sidebar_publisher)
        navbox.addWidget(self.publisher_brand_block)
        navbox.addSpacing(4)
        self.workspace_button=button('Workspace',self.home,icon_name='house')
        self.workspace_button.setObjectName('sidebarButton')
        self.workspace_button.setCheckable(True)
        navbox.addWidget(self.workspace_button)
        self.nav=QListWidget()
        self.nav.setObjectName('nav')
        self.nav.setIconSize(QSize(17,17))
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav_items={}
        self.nav_groups=[]
        for title,names in GROUPS:
            heading=QListWidgetItem(title.upper())
            heading.setFlags(Qt.NoItemFlags)
            heading.setSizeHint(QSize(180,32))
            self.nav.addItem(heading)
            self.nav_groups.append((heading,names))
            for name in names:
                item=QListWidgetItem(icon(ICONS[name],COLORS['sidebar_text'],17),name)
                item.setData(Qt.UserRole,name)
                item.setData(Qt.AccessibleTextRole,name)
                item.setData(Qt.AccessibleDescriptionRole,BY_NAME[name].description)
                item.setSizeHint(QSize(180,34))
                item.setToolTip(name)
                self.nav.addItem(item)
                self.nav_items[name]=item
        self.nav.itemClicked.connect(lambda item:self.select_tool(item.data(Qt.UserRole)) if item.data(Qt.UserRole) else None)
        self.nav.itemActivated.connect(lambda item:self.select_tool(item.data(Qt.UserRole)) if item.data(Qt.UserRole) else None)
        navbox.addWidget(self.nav,1)
        self.settings_button=button('Settings & branding',self.settings,icon_name='settings-2')
        self.settings_button.setObjectName('sidebarButton')
        navbox.addWidget(self.settings_button)
        self.about_button=button('About & Legal',self.about_legal,icon_name='badge-check')
        self.about_button.setObjectName('sidebarButton')
        self.about_button.setAccessibleName('About & Legal')
        navbox.addWidget(self.about_button)
        self.local_note=QFrame()
        self.local_note.setObjectName('publisherFooter')
        publisher_footer=QVBoxLayout(self.local_note)
        publisher_footer.setContentsMargins(10,14,4,0)
        publisher_footer.setSpacing(5)
        publisher_footer.addWidget(label('Developed by','brandSub'))
        publisher_footer.addWidget(label(PUBLISHER,'sidebarPublisher',True))
        publisher_footer.addWidget(label('Version '+__version__,'brandSub'))
        navbox.addWidget(self.local_note)
        shell.addWidget(self.sidebar)
        main=QVBoxLayout()
        main.setSpacing(0)
        self.topbar=QFrame()
        self.topbar.setObjectName('topbar')
        top=QHBoxLayout(self.topbar)
        top.setContentsMargins(24,12,24,12)
        self.menu_toggle=button('',self.toggle_sidebar,icon_name='panel-left',quiet=True)
        self.menu_toggle.setCheckable(True)
        self.menu_toggle.setAccessibleName('Collapse navigation')
        self.menu_toggle.setToolTip('Collapse navigation · Ctrl+B')
        top.addWidget(self.menu_toggle)
        context=QVBoxLayout()
        context.setSpacing(3)
        self.header_title=label('Workspace','headerTitle')
        self.breadcrumb=label('Your local document counter','caption')
        context.addWidget(self.header_title)
        context.addWidget(self.breadcrumb)
        top.addLayout(context,1)
        self.search=QLineEdit()
        self.search.setPlaceholderText('Find a tool…  Ctrl+K')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('Search all tools. Control K.')
        self.search_icon_action=self.search.addAction(icon('search',COLORS['secondary'],16),QLineEdit.LeadingPosition)
        self.search.setMinimumWidth(180)
        self.search.setMaximumWidth(310)
        self.search.textChanged.connect(self.filter_tools)
        self.search.installEventFilter(self)
        top.addWidget(self.search,1)
        self.offline_badge=label('●  LOCAL / OFFLINE','pill')
        self.offline_badge.setToolTip('Files are processed locally. No upload is needed.')
        top.addWidget(self.offline_badge)
        self.open_action=button('',lambda:self.select_and_open('Print'),icon_name='folder-open',quiet=True)
        self.open_action.setToolTip('Open document · Ctrl+O')
        top.addWidget(self.open_action)
        main.addWidget(self.topbar)
        self.stack=QStackedWidget()
        main.addWidget(self.stack,1)
        self.publisher_footer=QFrame()
        self.publisher_footer.setObjectName('workspacePublisherFooter')
        publisher_row=QHBoxLayout(self.publisher_footer)
        self.publisher_row=publisher_row
        publisher_row.setContentsMargins(28,8,28,8)
        self.copyright_badge=label(COPYRIGHT_SHORT,'caption')
        self.copyright_badge.setToolTip(COPYRIGHT)
        publisher_row.addWidget(self.copyright_badge)
        publisher_row.addStretch()
        from .legal import open_contact
        self.publisher_website=button(QUrl(WEBSITE).host(),lambda:open_contact(WEBSITE),quiet=True)
        self.publisher_website.setObjectName('publisherLink')
        self.publisher_website.setAccessibleName('Open '+WEBSITE)
        self.publisher_website.setToolTip(WEBSITE)
        publisher_row.addWidget(self.publisher_website)
        main.addWidget(self.publisher_footer)
        shell.addLayout(main,1)
        self.home_page=self.build_home()
        self.stack.addWidget(self.home_page)
        self.work_page=self.build_workspace()
        self.stack.addWidget(self.work_page)
        self.command_results=QListWidget(root)
        self.command_results.setObjectName('commandResults')
        self.command_results.setIconSize(QSize(18,18))
        self.command_results.setFocusPolicy(Qt.NoFocus)
        self.command_results.setAccessibleName('Tool search results')
        self.command_results.itemClicked.connect(lambda item:self.launch_search(item))
        self.command_results.hide()
        shadow=QGraphicsDropShadowEffect(self.command_results)
        shadow.setBlurRadius(12)
        shadow.setOffset(0,3)
        shadow.setColor(QColor(20,35,50,20))
        self.command_results.setGraphicsEffect(shadow)
        self._compact=None
        self._files_in_form=False
        QShortcut(QKeySequence('Ctrl+K'),self,activated=self.focus_search)
        QShortcut(QKeySequence('Ctrl+F'),self,activated=self.focus_search)
        QShortcut(QKeySequence('Ctrl+B'),self,activated=self.toggle_sidebar)
        QShortcut(QKeySequence('Ctrl+O'),self,activated=self.open_current_files)
        QShortcut(QKeySequence('Ctrl+S'),self,activated=self.save)
        QShortcut(QKeySequence('Ctrl+P'),self,activated=self.print_current)
        QShortcut(QKeySequence('Ctrl+,'),self,activated=self.settings)
        QShortcut(QKeySequence('Escape'),self,activated=self.dismiss_search)
        QShortcut(QKeySequence('Ctrl+='),self,activated=lambda:self.canvas.set_zoom(self.canvas.zoom*1.2))
        QShortcut(QKeySequence('Ctrl+-'),self,activated=lambda:self.canvas.set_zoom(self.canvas.zoom/1.2))
        QShortcut(QKeySequence('Ctrl+0'),self,activated=lambda:self.canvas.set_zoom(1))
        self.statusBar().setSizeGripEnabled(True)
        self.statusBar().showMessage('Ready · Files stay on this PC')
        self.apply_branding()
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.system_theme_changed)

    def system_theme_changed(self,*args):
        if self.appearance.get('theme')=='System':self.apply_branding()

    def build_home(self):
        page=QWidget()
        page.setObjectName('page')
        box=QVBoxLayout(page)
        box.setContentsMargins(28,24,28,28)
        box.setSpacing(16)
        hero=GlassSurface()
        self.hero_surface=hero
        hero.setObjectName('hero')
        hero_box=QVBoxLayout(hero)
        hero_box.setContentsMargins(20,16,20,16)
        hero_box.setSpacing(8)
        heading=QHBoxLayout()
        words=QVBoxLayout()
        words.setSpacing(7)
        hour=datetime.now().hour
        greeting='Good morning' if hour<12 else 'Good afternoon' if hour<17 else 'Good evening'
        words.addWidget(label(greeting+'.','heroTitle'))
        words.addWidget(label('Everything you need to run your document counter.','heroBody',True))
        heading.addLayout(words,1)
        self.hero_actions=QWidget()
        actions=QHBoxLayout(self.hero_actions)
        actions.setContentsMargins(0,0,0,0)
        actions.addWidget(button('Open document',lambda:self.select_and_open('Print'),True,'folder-open'))
        actions.addWidget(button('Scan document',lambda:self.select_tool('Scan'),icon_name='scan-line'))
        heading.addWidget(self.hero_actions)
        hero_box.addLayout(heading)
        box.addWidget(hero)
        quick=QFrame()
        quick.setObjectName('quickStrip')
        strip=QHBoxLayout(quick)
        strip.setContentsMargins(10,7,10,7)
        strip.setSpacing(2)
        for title,name in [('Print','Print'),('Scan','Scan'),('PDF tools','PDF Editor'),('ID / PVC','PVC Tool'),('Photo print','Photo Print')]:
            strip.addWidget(button(title,lambda checked=False,n=name:self.select_tool(n),icon_name=ICONS[name],quiet=True),1)
        box.addWidget(quick)
        self.sections=[]
        self.cards=[]
        for title,names in GROUPS:
            section=ToolSection(title,[BY_NAME[name] for name in names],self.select_tool)
            self.sections.append(section)
            self.cards.extend((card.tool,card) for card in section.cards)
        self.dashboard=DashboardGrid(self.sections)
        box.addWidget(self.dashboard)
        self.home_empty=label('No tools match your search. Try “photo”, “PDF” or “print”.','note',True)
        self.home_empty.hide()
        box.addWidget(self.home_empty)
        box.addStretch()
        return scroll(page)

    def build_workspace(self):
        from .ui import Canvas
        page=QWidget()
        page.setObjectName('page')
        root=QVBoxLayout(page)
        self.tool_root=root
        root.setContentsMargins(24,20,24,16)
        root.setSpacing(12)
        header=QHBoxLayout()
        back=button('',self.home,icon_name='arrow-left',quiet=True)
        self.back_button=back
        back.setToolTip('Back to workspace')
        header.addWidget(back)
        self.tool_badge=IconBadge('printer',42)
        header.addWidget(self.tool_badge)
        words=QVBoxLayout()
        words.setSpacing(4)
        self.tool_title=label('','title')
        self.tool_description=label('','muted',True)
        words.addWidget(self.tool_title)
        words.addWidget(self.tool_description)
        header.addLayout(words,1)
        self.history_button=button('Saved records',self.history,icon_name='clock')
        header.addWidget(self.history_button)
        root.addLayout(header)
        self.work_split=QSplitter(Qt.Horizontal)
        self.work_split.setChildrenCollapsible(False)
        self.file_scroll=scroll(QWidget())
        self.file_scroll.setMinimumWidth(190)
        self.file_scroll.setMaximumWidth(250)
        self.work_split.addWidget(self.file_scroll)
        self.preview_card=QFrame()
        self.preview_card.setObjectName('panel')
        view=QVBoxLayout(self.preview_card)
        self.preview_box=view
        view.setContentsMargins(12,12,12,12)
        view.setSpacing(8)
        heading=QHBoxLayout()
        self.preview_heading=label('DOCUMENT PREVIEW','eyebrow')
        heading.addWidget(self.preview_heading)
        heading.addStretch()
        self.preview_caption=label('','caption')
        self.preview_caption.setMaximumWidth(260)
        self.preview_caption.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        heading.addWidget(self.preview_caption)
        view.addLayout(heading)
        self.workflow_context=label('','workflowContext',True)
        self.workflow_context.hide()
        view.addWidget(self.workflow_context)
        self.empty_state=EmptyState(self.empty_action)
        view.addWidget(self.empty_state,1)
        self.canvas=Canvas()
        self.canvas.setMinimumSize(240,210)
        self.canvas.selected.connect(self.on_selection)
        self.canvas.hide()
        view.addWidget(self.canvas,1)
        self.text_preview=QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setAccessibleName('Document text or verification report')
        self.text_preview.hide()
        view.addWidget(self.text_preview,1)
        self.preview_toolbar=QWidget()
        nav=QHBoxLayout(self.preview_toolbar)
        nav.setContentsMargins(0,0,0,0)
        nav.setSpacing(4)
        self.page_actions=[]
        for name,callback,tip in [('chevron-left',lambda:self.change_page(-1),'Previous page'),('chevron-right',lambda:self.change_page(1),'Next page')]:
            action=button('',callback,icon_name=name,quiet=True)
            action.setToolTip(tip)
            action.setAccessibleName(tip)
            nav.addWidget(action)
            self.page_actions.append(action)
        self.page_label=label('','caption')
        nav.addWidget(self.page_label)
        nav.addStretch()
        for name,callback,tip in [('minus',lambda:self.canvas.set_zoom(self.canvas.zoom/1.25),'Zoom out'),('expand',lambda:self.canvas.set_zoom(1),'Fit preview'),('plus',lambda:self.canvas.set_zoom(self.canvas.zoom*1.25),'Zoom in')]:
            action=button('',callback,icon_name=name,quiet=True)
            action.setToolTip(tip)
            action.setAccessibleName(tip)
            nav.addWidget(action)
        self.show_input_button=button('Input',self.preview_input,quiet=True)
        self.show_input_button.setToolTip('Show selected original file')
        nav.addWidget(self.show_input_button)
        view.addWidget(self.preview_toolbar)
        self.preview_toolbar.hide()
        self.work_split.addWidget(self.preview_card)
        outer=QWidget()
        self.form_box=QVBoxLayout(outer)
        self.form_box.setContentsMargins(0,0,4,0)
        self.form_box.setSpacing(12)
        self.form_scroll=scroll(outer)
        self.form_scroll.setMinimumWidth(276)
        self.form_scroll.setMaximumWidth(360)
        self.work_split.addWidget(self.form_scroll)
        self.work_split.setStretchFactor(1,1)
        root.addWidget(self.work_split,1)
        self.progress=QProgressBar()
        self.progress.setRange(0,0)
        self.progress.hide()
        root.addWidget(self.progress)
        self.result_message=Feedback()
        self.open_output_button=button('',self.open_saved_output,icon_name='file-down',quiet=True)
        self.open_output_button.setAccessibleName('Open exported file')
        self.open_output_button.setToolTip('Open the file you just saved')
        self.open_folder_button=button('',lambda:self.open_saved_output(True),icon_name='folder-open',quiet=True)
        self.open_folder_button.setAccessibleName('Open export folder')
        self.open_folder_button.setToolTip('Open the folder containing your saved file')
        for action in (self.open_output_button,self.open_folder_button):
            action.setFixedSize(32,32);action.hide();self.result_message.layout().insertWidget(self.result_message.layout().count()-1,action)
        root.addWidget(self.result_message)
        self.action_bar=QFrame()
        self.action_bar.setObjectName('actionBar')
        footer=QHBoxLayout(self.action_bar)
        footer.setContentsMargins(12,8,12,8)
        footer.setSpacing(8)
        self.run_button=button('Prepare result',self.primary_action,True,'check')
        self.preview_button=button('Update preview',self.prepare,icon_name='sliders-horizontal')
        self.save_button=button('Save result',self.save,icon_name='file-down')
        self.print_button=button('Print',self.print_result,icon_name='printer')
        footer.addWidget(self.run_button)
        footer.addWidget(self.preview_button)
        footer.addWidget(self.save_button)
        self.copy_button=button('Copy image',self.copy_qr_image,icon_name='files',quiet=True)
        self.copy_button.setToolTip('Copy the generated QR image to the Windows clipboard')
        self.copy_button.hide()
        self.copy_button.setEnabled(False)
        footer.addWidget(self.copy_button)
        footer.addWidget(self.print_button)
        self.print_button.setToolTip('Print is available for PDF output')
        self.reset_button=button('Start another',self.reset_tool,icon_name='repeat-2',quiet=True)
        self.reset_button.setToolTip('Reset this tool and clear its unsaved inputs and result')
        footer.addWidget(self.reset_button)
        self.cancel_button=button('Discard result',self.discard_work,icon_name='x',quiet=True)
        self.cancel_button.setToolTip('Finish the current operation safely and discard its result. No file is exported.')
        self.cancel_button.hide()
        footer.addWidget(self.cancel_button)
        footer.addStretch()
        self.output_summary=label('','caption')
        footer.addWidget(self.output_summary)
        self.footer_note=label('Processed on this PC','caption')
        self.footer_note.hide()
        footer.addWidget(self.footer_note)
        root.addWidget(self.action_bar)
        self.save_button.setEnabled(False)
        self.print_button.setEnabled(False)
        return page

    def home(self):
        if self.busy or self.recorder.running:
            return
        if hasattr(self,'live_timer'):
            self.live_timer.stop()
        self.stack.setCurrentIndex(0)
        self.header_title.setText('Workspace')
        self.breadcrumb.setText('Your local document counter')
        self.workspace_button.setChecked(True)
        self.nav.clearSelection()
        self.command_results.hide()

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    def open_current_files(self):
        if self.busy or self.recorder.running:return
        if self.stack.currentIndex()==0 or not self.current or self.current.name in ('QR Generator','Resume Maker','Bill Maker','Screen Recording'):self.select_tool('Print')
        self.open_files()

    def print_current(self):
        if self.busy or self.recorder.running or getattr(self,'_printing',False):return
        if self.stack.currentIndex()==0 or not self.current:self.select_and_open('Print')
        elif self.current.name=='Print':self.primary_action()
        elif self.result and (self.result.preview or self.result.data).startswith(b'%PDF'):self.print_result()
        else:self.statusBar().showMessage('Prepare a PDF result before printing. Ctrl+S exports other results.')

    def dismiss_search(self):
        self.search.clear()
        self.command_results.hide()

    def launch_search(self,item=None):
        item=item or self.command_results.currentItem()
        if item and item.data(Qt.UserRole):
            name=item.data(Qt.UserRole)
            self.search.clear()
            self.command_results.hide()
            self.select_tool(name)
            self.run_button.setFocus()

    def filter_tools(self,text):
        query=text.lower().strip()
        matching=[]
        for tool in TOOLS:
            haystack=(tool.name+' '+tool.group+' '+tool.description+' '+SEARCH_ALIASES.get(tool.name,'')).lower()
            visible=all(word in haystack for word in query.split())
            self.nav_items[tool.name].setHidden(False)
            if visible:
                matching.append(tool)
        matching.sort(key=lambda tool:(tool.name.lower()!=query,not tool.name.lower().startswith(query)))
        for heading,names in self.nav_groups:
            heading.setHidden(bool(self._compact))
        self.home_empty.hide()
        self.command_results.clear()
        if query and self.search.hasFocus():
            for tool in matching:
                item=QListWidgetItem(icon(ICONS[tool.name],self.theme['accent_ink'],18),tool.name+'  /  '+tool.group)
                item.setData(Qt.UserRole,tool.name)
                item.setSizeHint(QSize(360,44))
                self.command_results.addItem(item)
            if not matching:
                item=QListWidgetItem('No tools found · Try another name')
                item.setFlags(Qt.NoItemFlags)
                self.command_results.addItem(item)
            self.command_results.setCurrentRow(0)
            position=self.search.mapTo(self.centralWidget(),self.search.rect().bottomLeft())
            width=max(350,self.search.width())
            self.command_results.setGeometry(min(position.x(),self.centralWidget().width()-width-16),position.y()+6,width,min(8,len(matching) or 1)*44+12)
            self.command_results.show()
            self.command_results.raise_()
        else:
            self.command_results.hide()

    def eventFilter(self,watched,event):
        if watched is self.search and event.type()==QEvent.KeyPress:
            if event.key() in (Qt.Key_Down,Qt.Key_Up) and self.command_results.isVisible():
                delta=1 if event.key()==Qt.Key_Down else -1
                self.command_results.setCurrentRow(max(0,min(self.command_results.count()-1,self.command_results.currentRow()+delta)))
                return True
            if event.key() in (Qt.Key_Return,Qt.Key_Enter):
                self.launch_search()
                return True
            if event.key()==Qt.Key_Escape:
                self.dismiss_search()
                self.search.clearFocus()
                return True
        return super().eventFilter(watched,event)

    def clear_form(self):
        if hasattr(self,'file_panel'):
            self.file_panel.setParent(None)
            self.file_panel.deleteLater()
        old=self.file_scroll.takeWidget()
        if old:
            old.deleteLater()
        self._files_in_form=False
        while self.form_box.count():
            item=self.form_box.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def select_tool(self,name):
        if self.busy or self.recorder.running or name not in BY_NAME:
            return
        if hasattr(self,'live_timer'):
            self.live_timer.stop()
            self.live_timer.deleteLater()
            del self.live_timer
        self.current=BY_NAME[name]
        self.saved_output=None
        self.open_output_button.hide();self.open_folder_button.hide()
        from .diagnostics import record
        record('tool_opened',tool=name)
        self.clear_form()
        self.fields={}
        self.result=None
        self.preview_data=None
        self.page_count=0
        self._input_page=0
        self.preview_is_input=False
        self._retry_preview=None
        self.canvas.set_image(None)
        self.canvas.hide()
        self.text_preview.hide()
        self.empty_state.show()
        self.page_label.clear()
        self.preview_caption.setText('No file selected')
        self.preview_heading.setText({'QR Generator':'QR PREVIEW','Resume Maker':'RESUME PREVIEW','Bill Maker':'INVOICE PREVIEW','Signature Check':'SIGNATURE REPORT','Screen Recording':'CAPTURE WORKSPACE'}.get(name,'DOCUMENT PREVIEW'))
        self.tool_title.setText(name)
        self.tool_description.setText(PURPOSE.get(name,self.current.description))
        self.tool_badge.setPixmap(icon(ICONS[name],self.theme['accent_ink'],23).pixmap(23,23))
        self.tool_badge.icon_name=ICONS[name]
        self.header_title.setText(name)
        group=next(title for title,names in GROUPS if name in names)
        self.breadcrumb.setText('Workspace  /  '+group)
        self.history_button.setVisible(name in ('Resume Maker','Bill Maker'))
        self.workspace_button.setChecked(False)
        self.run_button.setText(ACTIONS[name])
        self.run_button.setEnabled(True)
        self.preview_button.setVisible(name=='Print')
        self.save_button.setEnabled(False)
        self.print_button.setEnabled(False)
        self.print_button.setVisible(name!='Print')
        self.copy_button.setVisible(name=='QR Generator')
        self.copy_button.setEnabled(False)
        self.output_summary.clear()
        self.preview_toolbar.hide()
        self.files=DocumentList()
        self.files.setAccessibleName('Selected local documents')
        self.files.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.files.setFixedHeight(150)
        self.files.currentRowChanged.connect(lambda row:self.preview_input())
        self._files_expanded=False
        self.compact_files_button=button('Add / manage documents',self.toggle_files,icon_name='files')
        self.compact_files_button.setCheckable(True)
        self.form_box.addWidget(self.compact_files_button)
        self.files.model().rowsInserted.connect(self.update_file_summary)
        self.files.model().rowsRemoved.connect(self.update_file_summary)
        self.file_panel=QFrame()
        self.file_panel.setObjectName('panel')
        filebox=QVBoxLayout(self.file_panel)
        filebox.setContentsMargins(12,16,12,12)
        filebox.setSpacing(12)
        filebox.addWidget(label('SELECTED DOCUMENTS' if name!='Scan' else 'SCANNED PAGES','eyebrow'))
        drop=FileDropZone(self.open_files)
        self.file_drop=drop
        drop.apply_theme(self.theme)
        if name in ('PVC Tool','Auto ID Card','Photo Print','Photo & Sign','PAN Tool','Auto Crop','Edit Screenshot'):
            drop.subtitle.setText('PNG, JPEG, TIFF or WebP images')
            drop.setToolTip('Browse image files or drop them here. Originals remain unchanged.')
        drop.filesDropped.connect(self.add_files)
        filebox.addWidget(drop)
        self.document_summary=label('No files added','caption',True)
        filebox.addWidget(self.document_summary)
        filebox.addWidget(self.files)
        fileactions=QHBoxLayout()
        for symbol,callback,tip in [('arrow-up',lambda:self.move_file(-1),'Move selected file up'),('arrow-down',lambda:self.move_file(1),'Move selected file down'),('trash',self.remove_files,'Remove selected files')]:
            action=button('',callback,icon_name=symbol,quiet=True)
            action.setToolTip(tip)
            action.setAccessibleName(tip)
            fileactions.addWidget(action)
        fileactions.addStretch()
        filebox.addLayout(fileactions)
        if name=='Scan':
            rotate=button('Rotate selected page',self.rotate_scan_page,icon_name='repeat-2',quiet=True)
            rotate.setToolTip('Rotate an image page 90 degrees. Originals remain unchanged; use PDF Editor for imported PDFs.')
            filebox.addWidget(rotate)
        self.thumbnails=QListWidget()
        self.thumbnails.setIconSize(QSize(42,58))
        self.thumbnails.setAccessibleName('Document page thumbnails')
        self.thumbnails.itemClicked.connect(lambda item:self.go_page(item.data(Qt.UserRole)))
        self.thumbnails.hide()
        filebox.addWidget(self.thumbnails,1)
        filebox.addStretch(0)
        self.file_scroll.setWidget(self.file_panel)
        if name=='Scan':
            self.scan_select=QComboBox()
            self.scan_select.addItem('Find a connected scanner',None)
            self.scan_select.setAccessibleName('Scanner selector')
            device=SettingsGroup('SCANNER')
            device.box.addWidget(DeviceSelector(self.scan_select,self.find_scanners,'Refresh devices'))
            self.scanner_status=label('No scanner selected. Discover Windows WIA devices, or import existing scans.','note',True)
            device.box.addWidget(self.scanner_status)
            self.scan_button=button('Scan page',self.scan,False,'scan-line')
            self.scan_button.setEnabled(False)
            device.box.addWidget(self.scan_button)
            self.form_box.addWidget(device)
        if name=='Print':
            self.build_printer_controls()
        self.option_groups={}
        group_names={key:title for title,keys in FIELD_GROUPS[name] for key in keys}
        for spec in self.current.fields:
            if spec.choices:
                widget=QComboBox()
                widget.addItems(spec.choices)
                widget.setCurrentText(str(spec.default))
            elif spec.kind=='bool':
                widget=QCheckBox(spec.label)
                widget.setChecked(bool(spec.default))
            elif spec.kind in ('int','float'):
                widget=QSpinBox() if spec.kind=='int' else QDoubleSpinBox()
                widget.setRange(1 if spec.kind=='int' else .01,20000)
                if name=='Print' and spec.key=='copies':widget.setMaximum(999)
                if name=='QR Generator' and spec.key=='size':widget.setMaximum(8192)
                if name=='Screen Recording' and spec.key=='fps':widget.setMaximum(30)
                widget.setValue(spec.default)
                if spec.kind=='float':
                    widget.setDecimals(2)
            elif spec.kind=='multiline':
                widget=QTextEdit()
                widget.setFixedHeight(90)
                widget.setPlainText(WEBSITE if name=='QR Generator' and spec.key=='text' else str(spec.default))
            else:
                widget=QLineEdit(str(spec.default))
                widget.setPlaceholderText(spec.hint)
            widget.setObjectName('field_'+spec.key)
            widget.setAccessibleName(spec.label)
            self.fields[spec.key]=widget
            title=group_names.get(spec.key,'OPTIONS')
            if title not in self.option_groups:
                group=SettingsGroup(title)
                self.option_groups[title]=group
                self.form_box.addWidget(group)
            if name=='Print' and spec.key=='pages':
                self.page_scope=QComboBox()
                self.page_scope.addItems(['All pages','Current page','Custom range'])
                self.page_scope.setAccessibleName('Pages to print')
                self.page_scope.currentTextChanged.connect(self.sync_page_scope)
                self.option_groups[title].form.addRow('Page selection',self.page_scope)
                widget.setPlaceholderText('For example: 1-3, 5')
                widget.setEnabled(False)
            self.option_groups[title].form.addRow('' if spec.kind=='bool' else spec.label,widget)
            for signal in ('currentTextChanged','textChanged','valueChanged','toggled'):
                if hasattr(widget,signal):
                    getattr(widget,signal).connect(self.update_workflow_context)
                    break
        if name=='Merge Tool':
            self.form_box.addWidget(SettingsGroup('FILE ORDER','Use the arrows in the document list to arrange your files. The merged PDF follows this order.'))
        if name=='Bill Maker':
            self.items=QTableWidget(1,4)
            self.items.setHorizontalHeaderLabels(['Service','Qty','Rate','Tax %'])
            self.items.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
            for col in (1,2,3):
                self.items.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeToContents)
            self.items.verticalHeader().hide()
            self.items.setMinimumHeight(150)
            self.items.setItem(0,0,QTableWidgetItem('Document printing'))
            for col,value in enumerate(('1','5','0'),1):
                self.items.setItem(0,col,QTableWidgetItem(value))
            self.form_box.addWidget(self.items)
            line=QWidget()
            row=QHBoxLayout(line)
            row.setContentsMargins(0,0,0,0)
            row.addWidget(button('Add line',self.add_invoice_line,icon_name='plus'))
            row.addWidget(button('Remove last',lambda:self.items.removeRow(self.items.rowCount()-1),quiet=True))
            self.form_box.addWidget(line)
            self.invoice_totals_label=label('','sectionTitle',True)
            self.form_box.addWidget(self.invoice_totals_label)
            self.items.itemChanged.connect(self.update_invoice_totals)
            self.items.model().rowsRemoved.connect(self.update_invoice_totals)
            self.update_invoice_totals()
        if self.current.note:
            self.form_box.addWidget(label(self.current.note,'caption',True))
        if name in ('Photo Print','Photo & Sign','PAN Tool') and is_commercial_build():
            background=self.fields['background']
            background.clear()
            background.addItem('Keep')
            background.setEnabled(False)
            background.setToolTip('Background removal is not available in this edition. Photos keep their original background.')
            self.form_box.addWidget(label('Background removal is not available in this edition. Photo layouts keep the original background.' if is_store_build() else MODEL_UNAVAILABLE,'note',True))
        self.form_box.addStretch()
        if name in ('QR Generator','Resume Maker','Bill Maker'):
            timer=QTimer(self)
            self.live_timer=timer
            timer.setSingleShot(True)
            def live_preview():
                if self.current.name!=name or self.stack.currentIndex()!=1:
                    return
                if self.busy:
                    timer.start(400)
                    return
                if name=='Resume Maker' and not self.fields['name'].text().strip():
                    return
                if name=='QR Generator' and not self.fields['text'].toPlainText().strip():
                    return
                self.prepare()
            timer.timeout.connect(live_preview)
            for widget in self.fields.values():
                if isinstance(widget,QComboBox):
                    widget.currentTextChanged.connect(lambda:timer.start(700))
                elif isinstance(widget,(QLineEdit,QTextEdit)):
                    widget.textChanged.connect(lambda:timer.start(700))
            if name=='Bill Maker':
                self.items.itemChanged.connect(lambda:timer.start(700))
                self.items.model().rowsRemoved.connect(lambda:timer.start(700))
        generator=name in ('QR Generator','Resume Maker','Bill Maker','Screen Recording')
        self.empty_state.title.setText('Ready when you are' if generator else 'No scanned pages yet' if name=='Scan' else 'No document selected')
        self.empty_state.body.setText('Set your options to create a local preview.' if generator else 'Import a scan or connect a WIA scanner.' if name=='Scan' else 'Choose a PDF or image to get started.\nYour files stay on this PC.')
        self.empty_state.action.setText('Fill in the details' if generator else 'Import existing scan' if name=='Scan' else 'Choose a file')
        if generator:self.preview_caption.setText('Create a result to preview')
        if name=='Screen Recording':
            self.empty_state.title.setText('Ready to record')
            self.empty_state.body.setText('Choose a display and privacy masks. Recording starts only after you choose a save location.')
            self.empty_state.action.setText('Review capture settings')
            self.preview_caption.setText('No recording in progress')
        self.result_message.set_state('info','Ready to begin','Adjust your options, then prepare a result.' if generator else 'Open a local file. Original documents are preserved.')
        self.result_message.hide()
        self.stack.setCurrentIndex(1)
        self.nav.setCurrentItem(self.nav_items[name])
        for title,item in self.nav_items.items():
            item.setIcon(icon(ICONS[title],self.theme['sidebar_text'],17))
        self.command_results.hide()
        self.arrange_panels()
        if name=='Print':
            self.sync_printer()
            self.sync_page_scope()
        self.update_file_summary()
        self.update_workflow_context()
        self.adapt_height()
        recolor_buttons(self,self.theme)

    def empty_action(self):
        if getattr(self,'_retry_preview',None):
            self.load_background_preview(*self._retry_preview)
        elif self.current and self.current.name=='Scan' and getattr(self,'_scanner_discovered_empty',False):
            self.find_scanners()
        elif self.current and self.current.name in ('QR Generator','Resume Maker','Bill Maker','Screen Recording'):
            first=next(iter(self.fields.values()),None)
            if first:
                first.setFocus()
        else:
            self.open_files()

    def reset_tool(self):
        if self.current and not self.busy and not self.recorder.running:
            self.select_tool(self.current.name)

    def update_invoice_totals(self,*args):
        if not self.current or self.current.name!='Bill Maker':return
        from .business import invoice_totals
        try:
            totals=invoice_totals(self.options()['items'])
            self.invoice_totals_label.setText('Subtotal '+totals['subtotal']+'  ·  Tax '+totals['tax']+'\nTotal '+totals['total'])
        except ValueError:
            self.invoice_totals_label.setText('Check quantity, rate and tax values.')

    def sync_page_scope(self,*args):
        if 'pages' not in self.fields:return
        scope=self.page_scope.currentText()
        pages=self.fields['pages']
        pages.setEnabled(scope=='Custom range')
        group=self.option_groups.get('PAGES & COPIES')
        if group:group.form.setRowVisible(pages,scope=='Custom range')
        if scope=='All pages':pages.setText('all')
        elif scope=='Current page':pages.setText(str(getattr(self,'_input_page',0)+1))
        elif pages.text()=='all':pages.clear()

    def discard_work(self):
        if not self.busy:return
        self._discard_result=True
        self.cancel_button.setEnabled(False)
        self.result_message.set_state('processing','Finishing safely','The current operation will finish and its result will be discarded. No output file is exported.')

    def rotate_scan_page(self):
        if self.busy or not self.files.count():return
        item=self.files.currentItem()
        if item is None:return
        value=item.data(Qt.UserRole)
        if (isinstance(value,str) and Path(value).suffix.lower()=='.pdf') or (isinstance(value,bytes) and value.startswith(b'%PDF')):
            self.result_message.set_state('info','Open PDF Editor to rotate a PDF','This action rotates individual image pages. The imported PDF stays unchanged.')
            return
        from .images import load_image,image_bytes
        try:
            item.setData(Qt.UserRole,image_bytes(load_image(value).rotate(90,expand=True)))
            self.invalidate_result()
            self.preview_input()
            self.update_file_summary()
        except Exception as error:self.error(str(error))

    def update_workflow_context(self,*args):
        if not self.current or not hasattr(self,'workflow_context'):return
        def value(key,default=''):
            widget=self.fields.get(key)
            if widget is None:return default
            if isinstance(widget,QComboBox):return widget.currentText()
            if isinstance(widget,(QSpinBox,QDoubleSpinBox)):return f'{widget.value():g}'
            return widget.text() if isinstance(widget,QLineEdit) else default
        name=self.current.name
        text=''
        if name=='Print' and hasattr(self,'page_scope') and self.page_scope.currentText()=='Current page' and self.files.count():
            item=self.files.item(max(0,self.files.currentRow()))
            text='Current input: '+item.text()[:40]+' · Page '+str(getattr(self,'_input_page',0)+1)
            self.page_scope.setToolTip('Current page refers to the selected original input. Use Input to choose an original page before printing.')
        elif name in ('PVC Tool','Auto ID Card','Photo Print'):
            text=f'{value("width")} × {value("height")} mm · {value("paper")} sheet'
            if name=='Auto ID Card':text+=' · Front / back order'
            if name=='Photo Print':text+=' · '+value('copies')+' copies'
        elif name=='Photo & Sign':text=f'{value("width")} × {value("height")} px · {value("format")} · Limit {value("kb")} KB'
        elif name=='Convert':
            suffix='Files'
            if hasattr(self,'files') and self.files.count():
                source=self.files.item(0).data(Qt.UserRole)
                suffix=Path(source).suffix.lstrip('.').upper() if isinstance(source,str) else 'Image'
            text=f'FROM {suffix or "Files"}  →  TO {value("format")}'
        elif name in ('Compress','Portal PDF Pack'):text='Target maximum: '+value('kb')+' KB · Review output readability'
        elif name=='Mini Print':text=value('layout')+' pages per '+value('paper')+' sheet'
        elif name=='Merge Tool':text='Merged PDF follows the order of the document list'
        elif name=='Signature Check':text='Existing signatures · Offline trust inspection'
        elif name=='PAN Tool':text='First: photo · Optional second: signature · Attachment sheet'
        self.workflow_context.setText(text)
        self.workflow_context.setVisible(bool(text))

    def primary_action(self):
        if self.busy or getattr(self,'_printing',False):return
        if self.current.name=='Print':
            if self.result and self.options()==getattr(self,'_prepared_print_options',None) and self.inputs()==getattr(self,'_prepared_print_inputs',None):
                self.print_result()
            else:
                from .engine import execute
                files,options=self.inputs(),self.options()
                self.invalidate_result()
                self.work(lambda:execute('Print',files,options,self.store),self.print_after_prepare)
        else:
            self.prepare()

    def print_after_prepare(self,result):
        self.show_result(result)
        self.print_result()

    def build_printer_controls(self):
        device=SettingsGroup('PRINTER')
        self.printer_select=QComboBox()
        self.printer_select.setAccessibleName('Printer')
        infos=QPrinterInfo.availablePrinters()
        self.printers={info.printerName():info for info in infos}
        for info in infos:
            self.printer_select.addItem(info.printerName())
        if infos:
            default=QPrinterInfo.defaultPrinterName()
            self.printer_select.setCurrentText(default if default in self.printers else infos[0].printerName())
        else:
            self.printer_select.addItem('No printer installed')
            self.printer_select.setEnabled(False)
        device.box.addWidget(DeviceSelector(self.printer_select,self.refresh_printers,'Refresh printers'))
        self.printer_status=label('','note',True)
        device.box.addWidget(self.printer_status)
        self.form_box.addWidget(device)
        self.paper_select=QComboBox()
        self.paper_select.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.paper_select.setMinimumContentsLength(10)
        self.paper_select.setAccessibleName('Paper size reported by printer')
        self.orientation_select=QComboBox()
        self.orientation_select.addItems(['Portrait','Landscape'])
        self.scale_select=QComboBox()
        self.scale_select.addItems(['Fit printable area','Actual size'])
        form=QWidget()
        rows=QFormLayout(form)
        rows.setContentsMargins(0,0,0,0)
        rows.setRowWrapPolicy(QFormLayout.DontWrapRows)
        rows.addRow('Paper',self.paper_select)
        rows.addRow('Orientation',self.orientation_select)
        rows.addRow('Scale',self.scale_select)
        layout_group=SettingsGroup('PAPER & LAYOUT')
        layout_group.box.addWidget(form)
        self.form_box.addWidget(layout_group)
        self.printer_select.currentTextChanged.connect(self.sync_printer)

    def refresh_printers(self):
        if self.busy:return
        selected=self.printer_select.currentText()
        infos=QPrinterInfo.availablePrinters()
        self.printers={info.printerName():info for info in infos}
        self.printer_select.blockSignals(True)
        self.printer_select.clear()
        self.printer_select.addItems(list(self.printers) or ['No printer installed'])
        self.printer_select.setEnabled(bool(infos))
        default=QPrinterInfo.defaultPrinterName()
        self.printer_select.setCurrentText(selected if selected in self.printers else default if default in self.printers else self.printer_select.itemText(0))
        self.printer_select.blockSignals(False)
        self.sync_printer()

    def sync_printer(self):
        if not self.current or self.current.name!='Print' or not hasattr(self,'printer_select'):
            return
        info=self.printers.get(self.printer_select.currentText())
        previous=self.paper_select.currentData()
        previous_id=previous.id() if previous else None
        self.paper_select.clear()
        self.run_button.setEnabled(bool(info) and not self.busy)
        if not info:
            self.printer_status.setText('No printer installed. Prepare and save a PDF, or install a Windows printer driver.')
            return
        sizes=info.supportedPageSizes()
        for size in sizes:
            self.paper_select.addItem(size.name(),size)
        self.paper_select.setEnabled(bool(sizes))
        if not sizes:
            self.paper_select.addItem('Select in printer driver')
        default=info.defaultPageSize()
        preferred=previous_id if any(size.id()==previous_id for size in sizes) else default.id()
        for index in range(self.paper_select.count()):
            value=self.paper_select.itemData(index)
            if value and value.id()==preferred:
                self.paper_select.setCurrentIndex(index)
        modes=info.supportedDuplexModes()
        colours=info.supportedColorModes()
        if colours and 'colour' in self.fields:
            control=self.fields['colour']
            colour_index=control.findText('Colour')
            control.model().item(colour_index).setEnabled(QPrinter.Color in colours)
            if QPrinter.Color not in colours:
                control.setCurrentText('Black & white')
                control.setToolTip('The selected driver reports black-and-white output only.')
            else:
                control.setToolTip('Colour modes reported by the selected driver.')
        duplex=any(mode!=QPrinter.DuplexNone for mode in modes)
        if 'duplex' in self.fields:
            self.fields['duplex'].setEnabled(duplex if modes else True)
            self.fields['duplex'].setToolTip('Reported by the selected driver' if duplex else 'This driver does not report duplex support' if modes else 'Capability is not reported; confirm in the native print dialog')
            if modes and not duplex:
                self.fields['duplex'].setChecked(False)
        self.printer_status.setText(('Default printer' if info.isDefault() else 'Windows driver available')+'\n'+('Duplex available' if duplex else 'Duplex not reported')+'. Confirm settings in the print dialog.')
        if info.state()==QPrinter.Error:
            self.printer_status.setText('Windows reports a printer error. Check the print queue or select another printer.')

    def arrange_panels(self):
        if not self.current or not hasattr(self,'file_panel'):
            return
        has_files=self.current.name not in ('QR Generator','Resume Maker','Bill Maker','Screen Recording')
        wide=self.width()>=1320 and has_files
        if wide and self._files_in_form:
            self.form_box.removeWidget(self.file_panel)
            self.file_panel.setParent(None)
            self.file_scroll.setWidget(self.file_panel)
            self._files_in_form=False
        elif not wide and not self._files_in_form:
            self.file_scroll.takeWidget()
            self.form_box.insertWidget(1,self.file_panel)
            self._files_in_form=True
        self.file_panel.setVisible(has_files and (wide or self._files_expanded))
        self.compact_files_button.setVisible(has_files and not wide)
        self.file_scroll.setVisible(wide)
        if hasattr(self,'thumbnails'):
            self.thumbnails.setVisible(bool(wide and self.page_count and self.current.name in ('Print','Scan')))
        self.form_scroll.setMaximumWidth(340 if self.width()>=1180 else 296)
        if wide:
            self.work_split.setSizes([220,max(300,self.width()-820),310])
        else:
            self.work_split.setSizes([0,max(260,self.width()-440),300])

    def toggle_files(self):
        self._files_expanded=not self._files_expanded
        self.arrange_panels()

    def update_file_summary(self,*args):
        count=self.files.count()
        self.compact_files_button.setText(f'{count} document'+('s' if count!=1 else '')+' · Manage files' if count else 'Add / manage documents')
        if hasattr(self,'file_drop'):self.file_drop.set_compact(bool(count))
        total=0
        for index in range(count):
            value=self.files.item(index).data(Qt.UserRole)
            if isinstance(value,bytes):total+=len(value)
            elif isinstance(value,str):
                try:total+=Path(value).stat().st_size
                except OSError:pass
        if hasattr(self,'document_summary'):
            self.document_summary.setText(f'{count} file'+('s' if count!=1 else '')+f' · {total/1024:.1f} KB' if count else 'No files added')
        if self.current and self.current.name=='Scan':
            self.run_button.setEnabled(bool(count) and not self.busy)
            self.run_button.setToolTip('Build a PDF from the pages in this list' if count else 'Scan a page or import an existing image/PDF first')
        self.update_workflow_context()

    def toggle_sidebar(self):
        self._sidebar_collapsed=not self._sidebar_collapsed
        self.appearance['compact_menu']=self._sidebar_collapsed
        import sqlite3
        try:self.store.set('appearance',self.appearance)
        except (OSError,sqlite3.Error):self.statusBar().showMessage('Sidebar changed for this session. Local preferences could not be saved.')
        self.update_sidebar(animated=True)

    def update_sidebar(self,animated=False):
        compact=self.width()<1180 or self._sidebar_collapsed
        if compact!=self._compact:
            self._compact=compact
            target=72 if compact else 232
            if getattr(self,'menu_animation',None) is not None:
                self.menu_animation.stop()
                self.menu_animation.deleteLater()
                self.menu_animation=None
            if animated and not self.appearance.get('reduce_motion',False):
                self.menu_animation=QVariantAnimation(self)
                self.menu_animation.setDuration(MOTION['navigation'])
                self.menu_animation.setStartValue(self.sidebar.width())
                self.menu_animation.setEndValue(target)
                self.menu_animation.setEasingCurve(QEasingCurve.InOutCubic)
                self.menu_animation.valueChanged.connect(lambda value:self.sidebar.setFixedWidth(int(value)))
                self.menu_animation.start()
            else:
                self.sidebar.setFixedWidth(target)
            self.brand_words.setVisible(not compact)
            self.publisher_brand_block.setVisible(not compact)
            self.local_note.setVisible(not compact)
            self.brand_mark.setToolTip(BRAND+'\nA product of '+PUBLISHER)
            self.workspace_button.setText('' if compact else 'Workspace')
            self.workspace_button.setToolTip('Workspace')
            self.settings_button.setText('' if compact else 'Settings & branding')
            self.settings_button.setToolTip('Settings & branding')
            self.about_button.setText('' if compact else 'About & Legal')
            self.about_button.setToolTip('About & Legal')
            for name,item in self.nav_items.items():
                item.setText('' if compact else name)
                item.setSizeHint(QSize(40 if compact else 180,36 if compact else 34))
            for heading,names in self.nav_groups:
                heading.setHidden(compact)
            self.menu_toggle.setChecked(compact)
            action='Expand navigation' if compact else 'Collapse navigation'
            self.menu_toggle.setAccessibleName(action)
            self.menu_toggle.setToolTip(action+' · Ctrl+B')
        self.menu_toggle.setEnabled(self.width()>=1180)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not hasattr(self,'_compact'):
            return
        self.update_sidebar()
        self.hero_actions.setVisible(self.width()>=1080)
        self.offline_badge.setVisible(self.width()>=980)
        self.footer_note.hide()
        self.preview_caption.setVisible(self.width()>=1180)
        self.output_summary.setVisible(self.width()>=1100)
        self.adapt_height()
        self.command_results.hide()
        self.arrange_panels()

    def adapt_height(self):
        if not hasattr(self,'canvas'):return
        short=self.height()<700
        tight=self.height()<600
        self.tool_root.setContentsMargins(16 if short else 24,12 if short else 20,16 if short else 24,8 if short else 16)
        self.tool_root.setSpacing(8 if short else 12)
        self.tool_description.setVisible(not short)
        self.breadcrumb.setVisible(not tight)
        self.tool_badge.setFixedSize(32 if short else 42,32 if short else 42)
        self.canvas.setMinimumHeight(80 if short else 210)
        self.preview_box.setContentsMargins(8 if short else 12,8 if short else 12,8 if short else 12,8 if short else 12)
        self.preview_box.setSpacing(4 if short else 8)
        self.empty_state.set_compact(tight)
        self.result_message.body.setVisible(not tight and bool(self.result_message.body.text()))
        self.publisher_row.setContentsMargins(16 if short else 28,4 if short else 8,16 if short else 28,4 if short else 8)
        self.action_bar.layout().setContentsMargins(8 if short else 12,4 if short else 8,8 if short else 12,4 if short else 8)

    def go_page(self,page):
        if self.page_count and page is not None and not self.busy:
            self.page=max(0,min(self.page_count-1,int(page)))
            self.render_page()

    def refresh_thumbnails(self):
        if not hasattr(self,'thumbnails'):
            return
        self.thumbnails.clear()
        show=self.current and self.current.name in ('Print','Scan') and self.preview_data and self.preview_data.startswith(b'%PDF')
        self.thumbnails.setVisible(bool(show))
        if show:
            import pymupdf
            from PySide6.QtGui import QImage,QIcon
            with pymupdf.open(stream=self.preview_data,filetype='pdf') as doc:
                for index in range(min(len(doc),40)):
                    page=doc[index]
                    zoom=min(.1,100/max(page.rect.width,page.rect.height))
                    pix=page.get_pixmap(matrix=pymupdf.Matrix(zoom,zoom),colorspace=pymupdf.csRGB,alpha=False)
                    image=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
                    item=QListWidgetItem(QIcon(QPixmap.fromImage(image)),f'Page {index+1}')
                    item.setData(Qt.UserRole,index)
                    item.setSizeHint(QSize(120,64))
                    self.thumbnails.addItem(item)

    def apply_branding(self):
        brand=self.store.get('branding',{})
        self.theme=tokens(brand.get('accent'),self.appearance.get('theme','Light'))
        self.setStyleSheet(stylesheet(self.theme))
        native_window_theme(self,self.theme['dark'])
        self.search_icon_action.setIcon(icon('search',self.theme['secondary'],16))
        for surface in (self.sidebar,self.hero_surface):
            surface.accent=self.theme['accent']
            surface.theme=self.theme
            surface.effects=not self.appearance.get('reduce_transparency',False) and not self.theme['high_contrast']
            surface.update()
        self.setWindowTitle(BRAND)
        self.brand_name.setText('CredoNomics')
        self.brand_name.setToolTip(self.brand_name.text())
        self.brand_name.setMaximumWidth(142)
        self.brand_name.setText(self.brand_name.fontMetrics().elidedText(self.brand_name.toolTip(),Qt.ElideRight,142))
        self.brand_subtitle.setText('CYBER SOLUTIONS')
        self.copyright_badge.setText(COPYRIGHT_SHORT)
        self.copyright_badge.setToolTip(COPYRIGHT)
        logo=brand.get('logo') or self.store.get('business',{}).get('logo')
        if logo and Path(logo).is_file() and not QPixmap(logo).isNull():
            self.setWindowIcon(QIcon(logo))
            self.brand_mark.setPixmap(QPixmap(logo).scaled(34,34,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:
            self.brand_mark.setPixmap(QPixmap())
            self.brand_mark.setText('C')
        for badge in self.findChildren(IconBadge):
            badge.setPixmap(icon(badge.icon_name,self.theme['accent_ink'],20).pixmap(20,20))
        for tool,card in self.cards:
            card.theme=self.theme
            card.animation.setDuration(0 if self.appearance.get('reduce_motion',False) else MOTION['hover'])
            card.update()
        for drop in self.findChildren(FileDropZone):
            drop.apply_theme(self.theme)
        self.canvas.theme=self.theme
        self.canvas.update()
        if self.result_message.isVisible():
            self.result_message.set_state(self.result_message.state,self.result_message.title.text(),self.result_message.body.text())
        recolor_buttons(self,self.theme)

    def create_settings_dialog(self):
        dialog=QDialog(self)
        dialog.setWindowTitle('Settings & branding')
        dialog.resize(850,740)
        dialog.setMinimumSize(680,420)
        root=QVBoxLayout(dialog)
        root.setContentsMargins(24,24,24,20)
        root.setSpacing(16)
        heading=QHBoxLayout()
        heading.addWidget(IconBadge('settings-2',42))
        words=QVBoxLayout()
        words.addWidget(label('Settings & branding','title'))
        words.addWidget(label('Published by '+PUBLISHER,'muted',True))
        heading.addLayout(words,1)
        root.addLayout(heading)
        publisher_panel=QFrame()
        publisher_panel.setObjectName('panel')
        publisher_layout=QVBoxLayout(publisher_panel)
        publisher_layout.setContentsMargins(16,12,16,12)
        publisher_layout.setSpacing(8)
        publisher_layout.addWidget(label('APPLICATION IDENTITY','eyebrow'))
        publisher_columns=QHBoxLayout()
        publisher_columns.setSpacing(20)
        dialog.publisher_identity={}
        for values in ([('Product Name',BRAND),('Publisher',PUBLISHER),('Version',__version__)],
                       [('Website',WEBSITE),('Support Email',SUPPORT_EMAIL),('Support Phone',SUPPORT_PHONE)]):
            details=QFormLayout()
            details.setSpacing(6)
            for title,value in values:
                if title in ('Website','Support Email'):
                    from .legal import open_contact
                    url=WEBSITE if title=='Website' else 'mailto:'+SUPPORT_EMAIL
                    field=button(QUrl(WEBSITE).host() if title=='Website' else value,lambda checked=False,u=url:open_contact(u),quiet=True)
                    field.setObjectName('publisherLink')
                    field.setToolTip(url)
                else:
                    field=label(value,'sectionTitle' if title=='Publisher' else 'muted',True)
                    field.setTextInteractionFlags(Qt.TextSelectableByMouse)
                field.setAccessibleName(title+': '+value)
                dialog.publisher_identity[title]=field
                details.addRow(label(title,'caption'),field)
            publisher_columns.addLayout(details,1)
        publisher_layout.addLayout(publisher_columns)
        tabs=QTabWidget()
        root.addWidget(tabs,1)
        brand=dict(self.store.get('branding',{}))
        business=dict(self.store.get('business',{}))
        fields={}
        brand_page=QWidget()
        brand_stack=QVBoxLayout(brand_page)
        brand_stack.setContentsMargins(0,12,0,12)
        brand_stack.setSpacing(16)
        brand_stack.addWidget(publisher_panel)
        brand_stack.addWidget(label('WORKSPACE CUSTOMIZATION','eyebrow'))
        custom_brand=QWidget()
        identity=QHBoxLayout(custom_brand)
        brand_stack.addWidget(custom_brand)
        identity.setContentsMargins(0,20,0,0)
        form=QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        for key,title,default in [('product_name','Workspace name',BRAND),('company_name','Workspace company',PUBLISHER),('logo','Logo file',business.get('logo','')),('accent','Accent colour','#007d70'),('support','Workspace support details',SUPPORT_EMAIL+' · '+SUPPORT_PHONE),('website','Workspace website',WEBSITE),('copyright','Workspace footer',COPYRIGHT_SHORT)]:
            edit=QLineEdit(brand.get(key,default))
            edit.setAccessibleName(title)
            fields[key]=edit
            form.addRow(title,edit)
        left=QWidget()
        left.setLayout(form)
        leftbox=QVBoxLayout()
        leftbox.addWidget(left)
        actions=QHBoxLayout()
        actions.addWidget(button('Choose logo',lambda:self.choose_logo(fields['logo']),icon_name='image'))
        def choose_accent():
            color=QColorDialog.getColor(QColor(fields['accent'].text()),dialog,'Brand accent')
            if color.isValid():
                fields['accent'].setText(color.name())
        actions.addWidget(button('Choose colour',choose_accent))
        leftbox.addLayout(actions)
        leftbox.addStretch()
        identity.addLayout(leftbox,1)
        preview=QFrame()
        preview.setObjectName('panel')
        preview.setFixedWidth(265)
        p=QVBoxLayout(preview)
        p.setContentsMargins(20,24,20,24)
        p.addWidget(label('LIVE BRAND PREVIEW','eyebrow'))
        mark=label('C','mark')
        mark.setFixedSize(48,48)
        mark.setAlignment(Qt.AlignCenter)
        p.addWidget(mark)
        company=label(PUBLISHER,'muted',True)
        product=label(BRAND,'publisherTitle',True)
        p.addWidget(product)
        p.addWidget(company)
        sample=button('Primary action',primary=True)
        p.addWidget(sample)
        support=label('','muted',True)
        p.addWidget(support)
        copyright_label=label('','caption',True)
        p.addStretch()
        p.addWidget(copyright_label)
        identity.addWidget(preview)
        def refresh_preview():
            company.setText(fields['company_name'].text() or 'Company name')
            product.setText(fields['product_name'].text() or BRAND)
            support.setText(' · '.join(fields[key].text() for key in ('support','website') if fields[key].text()))
            copyright_label.setText(fields['copyright'].text())
            values=tokens(fields['accent'].text(),self.appearance.get('theme','Light'))
            sample.setStyleSheet(f'background:{values["accent"]};color:{values["accent_text"]};border:0;')
            mark.setStyleSheet(f'background:{values["accent"]};color:{values["accent_text"]};border-radius:10px;')
            pixmap=QPixmap(fields['logo'].text()) if fields['logo'].text() else QPixmap()
            if fields['logo'].text() and not pixmap.isNull():
                mark.setPixmap(pixmap.scaled(42,42,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            else:
                mark.setPixmap(QPixmap())
                mark.setText('C')
        for edit in fields.values():
            edit.textChanged.connect(refresh_preview)
        refresh_preview()
        tabs.addTab(scroll(brand_page),'Brand identity')
        business_page=QWidget()
        business_form=QFormLayout(business_page)
        business_form.setContentsMargins(8,24,16,24)
        business_form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        business_fields={}
        for key,title,default in [('name','Business name on invoices',BRAND),('address','Address',''),('gstin','GSTIN',''),('upi','UPI ID',''),('logo','Invoice logo file',''),('footer','Invoice footer','Thank you for your business.')]:
            edit=QLineEdit(business.get(key,default))
            business_fields[key]=edit
            business_form.addRow(title,edit)
        business_form.addRow(button('Choose invoice logo',lambda:self.choose_logo(business_fields['logo']),icon_name='image'))
        tabs.addTab(scroll(business_page),'Business details')
        local=QWidget()
        local_box=QVBoxLayout(local)
        local_box.setContentsMargins(8,24,8,24)
        local_box.setSpacing(16)
        local_box.addWidget(label('LOCAL COMPONENTS','eyebrow'))
        office=bool(shutil.which('soffice') or Path('C:/Program Files/LibreOffice/program/soffice.exe').exists())
        for title,description in [('AI background removal','Not included in this edition' if is_store_build() else MODEL_UNAVAILABLE if is_commercial_build() else 'Ready · bundled model' if model_path().is_file() else 'Model needs provisioning'),('OCR','Bundled English and Hindi data'),('Office documents','Built-in DOCX/XLSX · '+('LibreOffice found' if office else 'Legacy formats require installed LibreOffice')),('Windows printers',str(len(QPrinterInfo.availablePrinters()))+' installed'),('Edition','Windows desktop edition' if is_store_build() else 'Commercial investigation candidate · distribution on HOLD' if is_commercial_build() else 'Owner edition · all 20 tools available')]:
            local_box.addWidget(label(title,'sectionTitle'))
            local_box.addWidget(label(description,'muted',True))
        local_box.addWidget(label('PC ID: '+machine_id(),'caption'))
        from PySide6.QtGui import QDesktopServices
        local_box.addWidget(label('Developed and published by '+PUBLISHER+'\n'+WEBSITE+'\n'+SUPPORT_EMAIL+' · '+SUPPORT_PHONE,'muted',True))
        local_box.addWidget(button('Help & Support',self.help_support))
        def clear_folders():
            import sqlite3
            try:self.store.set('folders',{})
            except (OSError,sqlite3.Error):
                Modal(dialog,'Preferences could not be saved','Check local application-data permissions and available disk space.').exec();return
            self.statusBar().showMessage('Remembered folders cleared. Your documents and exported files are unchanged.')
        local_box.addWidget(button('Clear remembered folders',clear_folders))
        local_box.addWidget(button('Open application folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent.parent))),icon_name='folder-open'))
        local_box.addStretch()
        tabs.addTab(scroll(local),'Local workspace')
        appearance_page=QWidget()
        appearance_box=QVBoxLayout(appearance_page)
        appearance_box.setContentsMargins(16,24,16,24)
        appearance_box.setSpacing(16)
        appearance_box.addWidget(label('Comfort & appearance','sectionTitle'))
        appearance_box.addWidget(label('Glass lighting is limited to navigation and the welcome panel. Document previews keep a solid, neutral background.','muted',True))
        appearance_fields={}
        theme_select=QComboBox()
        theme_select.addItems(['Light','Dark','System','High contrast'])
        theme_select.setCurrentText(self.appearance.get('theme','Light'))
        theme_select.setAccessibleName('Application theme')
        theme_group=SettingsGroup('THEME','System follows the Windows application theme. Windows high-contrast preference takes priority. High contrast uses opaque surfaces and strong focus indicators.')
        theme_group.form.addRow('Application theme',theme_select)
        appearance_box.addWidget(theme_group)
        dialog.theme_select=theme_select
        for key,title in [('reduce_motion','Reduce navigation motion'),('reduce_transparency','Use solid navigation surfaces')]:
            check=QCheckBox(title)
            check.setChecked(bool(self.appearance.get(key,False)))
            appearance_fields[key]=check
            appearance_box.addWidget(check)
        appearance_box.addStretch()
        tabs.addTab(appearance_page,'Appearance')
        support_page=QWidget()
        support_box=QVBoxLayout(support_page)
        support_box.setContentsMargins(16,20,16,20)
        support_box.setSpacing(12)
        support_box.addWidget(label('Support & product information','sectionTitle'))
        support_box.addWidget(label(PUBLISHER,'muted',True))
        from .legal import contact_actions
        support_box.addLayout(contact_actions(dialog))
        support_box.addWidget(label('Support phone: '+SUPPORT_PHONE,'muted'))
        support_box.addWidget(button('Help & Support',self.help_support,icon_name='mail'))
        support_box.addWidget(button('About & Legal',self.about_legal,icon_name='badge-check'))
        support_box.addStretch()
        tabs.addTab(support_page,'Support')
        footer=QHBoxLayout()
        footer.addWidget(label('Changes apply to this installation.','caption'))
        footer.addStretch()
        footer.addWidget(button('Cancel',dialog.reject))
        def save_settings():
            if not QColor(fields['accent'].text()).isValid():
                Modal(dialog,'Choose a valid colour','Use a hex colour such as #007d70.').exec()
                return
            if fields['logo'].text() and QPixmap(fields['logo'].text()).isNull():
                Modal(dialog,'Logo could not be opened','Choose a readable local image file.').exec()
                return
            updated=self.appearance|{key:check.isChecked() for key,check in appearance_fields.items()}|{'theme':theme_select.currentText()}
            import sqlite3
            try:self.store.set_many({'branding':brand|{key:edit.text() for key,edit in fields.items()},'business':business|{key:edit.text() for key,edit in business_fields.items()},'appearance':updated})
            except (OSError,sqlite3.Error):
                Modal(dialog,'Settings could not be saved','Check permissions and free disk space in your local application-data folder. Your previous settings are unchanged.').exec()
                return
            self.appearance=updated
            self.apply_branding()
            self.statusBar().showMessage('Branding and business settings saved locally')
            dialog.accept()
        footer.addWidget(button('Save changes',save_settings,True,'check'))
        root.addLayout(footer)
        dialog.brand_fields=fields
        dialog.business_fields=business_fields
        dialog.appearance_fields=appearance_fields
        dialog.save_settings=save_settings
        dialog.tabs=tabs
        recolor_buttons(dialog,self.theme)
        fit_dialog(dialog)
        return dialog

    def settings(self):
        if not self.busy and not self.recorder.running:
            self.create_settings_dialog().exec()

    def about_legal(self):
        from .legal import about_dialog
        about_dialog(self).exec()

    def help_support(self):
        from .legal import support_dialog
        support_dialog(self).exec()
