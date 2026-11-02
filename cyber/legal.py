# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Local legal documents and explicit publisher contact actions."""
import sys
from pathlib import Path
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTextBrowser,QListWidget,QGridLayout
from PySide6.QtCore import QUrl,Qt
from PySide6.QtGui import QDesktopServices
from . import BRAND,PUBLISHER,COPYRIGHT,__version__,WEBSITE,SUPPORT_EMAIL,SUPPORT_PHONE,FILE_VERSION
from .components import label,button,fit_dialog
from PySide6.QtGui import QIcon


def resource_root():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))


def open_contact(url):
    if url not in (WEBSITE,'mailto:'+SUPPORT_EMAIL,'tel:'+SUPPORT_PHONE):
        return False
    return QDesktopServices.openUrl(QUrl(url))


def contact_actions(parent=None):
    row=QHBoxLayout()
    website=button(QUrl(WEBSITE).host(),lambda:open_contact(WEBSITE))
    website.setAccessibleName('Open '+WEBSITE)
    website.setToolTip(WEBSITE)
    email=button(SUPPORT_EMAIL,lambda:open_contact('mailto:'+SUPPORT_EMAIL))
    email.setAccessibleName('Email '+SUPPORT_EMAIL)
    email.setToolTip(SUPPORT_EMAIL)
    row.addWidget(website)
    row.addWidget(email)
    return row


def support_dialog(parent):
    dialog=QDialog(parent)
    dialog.setWindowTitle('Help & Support')
    dialog.resize(620,470)
    box=QVBoxLayout(dialog)
    box.setContentsMargins(28,28,28,24)
    box.setSpacing(10)
    box.addWidget(label('Help & Support','title'))
    box.addWidget(label(BRAND+' · '+__version__,'sectionTitle',True))
    box.addWidget(label('Developed and published by\n'+PUBLISHER,'muted',True))
    box.addWidget(label('Website: '+WEBSITE+'\nEmail: '+SUPPORT_EMAIL+'\nPhone: '+SUPPORT_PHONE,'muted',True))
    box.addLayout(contact_actions(dialog))
    box.addWidget(label('Website opens your browser. Email opens your mail app; nothing is sent automatically and documents are not attached.','caption',True))
    box.addWidget(label(COPYRIGHT,'caption',True))
    from .diagnostics import directory
    diagnostic_folder=directory()
    if diagnostic_folder:
        box.addWidget(button('Open diagnostics folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(diagnostic_folder))),icon_name='folder-open'))
    box.addStretch()
    box.addWidget(button('Close',dialog.accept))
    fit_dialog(dialog,scroll_content=True)
    return dialog


def document_dialog(parent,title,relative=None,licenses=False):
    dialog=QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(850,650)
    box=QVBoxLayout(dialog)
    box.setContentsMargins(24,24,24,20)
    box.addWidget(label(title,'sectionTitle'))
    row=QHBoxLayout()
    browser=QTextBrowser()
    browser.setOpenExternalLinks(False)
    browser.setOpenLinks(False)
    if licenses:
        listing=QListWidget()
        listing.setAccessibleName('Included license texts')
        listing.setMaximumWidth(310)
        paths=sorted((resource_root()/'third-party-licenses').rglob('*'))
        paths=[path for path in paths if path.is_file() and path.suffix.lower() in ('.txt','.md','.rst','.license','')]
        for path in paths:
            listing.addItem(path.relative_to(resource_root()/'third-party-licenses').as_posix())
        listing.currentRowChanged.connect(lambda index:browser.setPlainText(paths[index].read_text(encoding='utf-8',errors='replace')) if index>=0 else None)
        row.addWidget(listing)
        if paths:
            listing.setCurrentRow(0)
        dialog.license_list=listing
    elif relative:
        path=resource_root()/relative
        if path.is_file():
            content=path.read_text(encoding='utf-8')
            browser.setMarkdown(content) if path.suffix=='.md' else browser.setPlainText(content)
        else:
            browser.setPlainText('This document is missing. Restore the complete application folder before redistribution.')
    row.addWidget(browser,1)
    box.addLayout(row,1)
    box.addWidget(button('Close',dialog.accept))
    dialog.browser=browser
    fit_dialog(dialog)
    return dialog


def about_dialog(parent):
    dialog=QDialog(parent)
    dialog.setWindowTitle('About & Legal')
    dialog.resize(660,680)
    box=QVBoxLayout(dialog)
    box.setContentsMargins(32,28,32,24)
    box.setSpacing(10)
    product_row=QHBoxLayout()
    mark=label('')
    mark.setFixedSize(56,56)
    mark.setPixmap(QIcon(str(resource_root()/'assets/brandmark.svg')).pixmap(56,56))
    mark.setAccessibleName('CredoNomics logo')
    product_row.addWidget(mark)
    product_words=QVBoxLayout()
    product_words.setSpacing(6)
    product_words.addWidget(label(BRAND,'title',True))
    product_words.addWidget(label(f'Version {__version__} · Build {FILE_VERSION}','muted'))
    product_row.addLayout(product_words,1)
    box.addLayout(product_row)
    box.addSpacing(6)
    box.addWidget(label('Developed and published by','muted'))
    box.addWidget(label(PUBLISHER,'publisherTitle',True))
    box.addWidget(label(COPYRIGHT.replace('. All rights reserved.','.\nAll rights reserved.'),'muted',True))
    box.addSpacing(4)
    box.addWidget(label('WEBSITE & SUPPORT','eyebrow'))
    box.addLayout(contact_actions(dialog))
    box.addWidget(label('Support phone: '+SUPPORT_PHONE,'muted',True))
    box.addWidget(button('Help & Support',lambda:support_dialog(dialog).exec(),icon_name='mail'))
    box.addSpacing(4)
    box.addWidget(label('LEGAL & LICENSES','eyebrow'))
    box.addWidget(label('Original material: AGPL-3.0-only. Third-party rights and license terms remain in effect.','caption',True))
    actions=[('Open-Source Licenses',None,True),('Third-Party Notices','THIRD_PARTY_NOTICES.md',False),
        ('Privacy Information','docs/legal/DATA-HANDLING.md',False),('Software License','docs/legal/SOFTWARE-LICENSE.md',False),
        ('Version / Build Information','docs/legal/BUILD-INFO.md',False)]
    legal_grid=QGridLayout()
    legal_grid.setSpacing(8)
    for index,(title,path,licenses) in enumerate(actions):
        legal_grid.addWidget(button(title,lambda checked=False,t=title,p=path,l=licenses:document_dialog(dialog,t,p,l).exec()),index//2,index%2)
    box.addLayout(legal_grid)
    box.addStretch()
    box.addWidget(button('Close',dialog.accept))
    fit_dialog(dialog,scroll_content=True)
    return dialog
