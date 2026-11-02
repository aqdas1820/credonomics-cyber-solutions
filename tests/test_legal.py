# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
from pathlib import Path
import socket
import pytest
from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from cyber.ui import MainWindow
from cyber.storage import Store
from cyber.legal import about_dialog,document_dialog,resource_root
from cyber import PUBLISHER,COPYRIGHT,COPYRIGHT_SHORT
from cyber.distribution import is_store_build
from cyber import BRAND


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_about_identity_and_local_license_viewer(app,sample):
    window=MainWindow(Store(sample['directory']/'legal.db'))
    dialog=about_dialog(window)
    text=' '.join(widget.text().replace('\n',' ') for widget in dialog.findChildren(QLabel))
    assert PUBLISHER in text and COPYRIGHT in text and '1.2.0' in text
    titles={button.text() for button in dialog.findChildren(QPushButton)}
    assert {'Open-Source Licenses','Privacy Information','Third-Party Notices','Software License','Version / Build Information'}<=titles
    viewer=document_dialog(dialog,'Licenses',licenses=True)
    assert viewer.license_list.count()>10
    assert viewer.browser.toPlainText().strip()
    assert not viewer.browser.openExternalLinks()
    viewer.close();dialog.close();window.close()


@pytest.mark.parametrize('relative',['docs/legal/DATA-HANDLING.md','docs/legal/SOFTWARE-LICENSE.md','docs/legal/BUILD-INFO.md','THIRD_PARTY_NOTICES.md'])
def test_legal_documents_available_without_network(app,relative,monkeypatch):
    def deny(*args,**kwargs):raise AssertionError('Unexpected network connection')
    monkeypatch.setattr(socket.socket,'connect',deny)
    viewer=document_dialog(None,'Legal',relative)
    assert not viewer.browser.toPlainText().startswith('This document is missing.')
    assert len(viewer.browser.toPlainText())>200
    viewer.close()


def test_publisher_identity_survives_operator_branding(app,sample):
    store=Store(sample['directory']/'operator.db')
    store.set('branding',{'product_name':'Operator Desk','company_name':'Operator','copyright':'Operator'})
    window=MainWindow(store)
    assert window.windowTitle()==BRAND
    assert window.copyright_badge.text()==COPYRIGHT_SHORT
    assert COPYRIGHT in window.copyright_badge.toolTip()
    window.close()
    reopened=MainWindow(store)
    assert reopened.windowTitle()==BRAND
    dialog=about_dialog(reopened)
    assert any(PUBLISHER in item.text() for item in dialog.findChildren(QLabel))
    dialog.close();reopened.close()
