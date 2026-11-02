# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import json
from pathlib import Path
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication,QPushButton,QLabel
from cyber import BRAND_CONFIG,BRAND,PUBLISHER,COPYRIGHT,WEBSITE,SUPPORT_EMAIL,SUPPORT_PHONE
from cyber import legal,windows_package,storage
from cyber import COPYRIGHT_SHORT,__version__


def test_authoritative_contact_values_and_shared_copy():
    assert (BRAND,PUBLISHER,WEBSITE,SUPPORT_EMAIL,SUPPORT_PHONE)==('CredoNomics Cyber Solutions','CredoNomics Investment Solutions','https://credonomics.in','support@credonomics.in','02562455327')
    assert COPYRIGHT=='Copyright © 2026 CredoNomics Investment Solutions. All rights reserved.'
    root=Path(__file__).resolve().parents[1]
    assert json.loads((root/'store-assets/shared-brand/brand.json').read_text(encoding='utf-8'))==BRAND_CONFIG
    assert BRAND_CONFIG['privacy_policy_url'] is None


def test_support_actions_open_only_verified_website_and_mailto(monkeypatch):
    app=QApplication.instance() or QApplication([])
    opened=[]
    monkeypatch.setattr(legal.QDesktopServices,'openUrl',lambda url:opened.append(url.toString()) or True)
    dialog=legal.support_dialog(None)
    for button in dialog.findChildren(QPushButton):
        if button.accessibleName() in ('Open '+WEBSITE,'Email '+SUPPORT_EMAIL):button.click()
    assert opened==[WEBSITE,'mailto:'+SUPPORT_EMAIL]
    assert not legal.open_contact('https://example.com')
    assert opened==[WEBSITE,'mailto:'+SUPPORT_EMAIL]
    assert any(SUPPORT_PHONE in widget.text() for widget in dialog.findChildren(QLabel))
    dialog.close()


def test_packaged_storage_is_separate_and_override_preserved(monkeypatch,tmp_path):
    monkeypatch.setattr(windows_package,'package_family_name',lambda:'CredoNomics.Test_fixture')
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    monkeypatch.delenv('CREDONOMICS_DATA_DIR',raising=False)
    assert storage.data_directory()==tmp_path/'Packages/CredoNomics.Test_fixture/LocalState'
    monkeypatch.setenv('CREDONOMICS_DATA_DIR',str(tmp_path/'chosen'))
    assert storage.data_directory()==tmp_path/'chosen'


def test_unpacked_storage_keeps_existing_location(monkeypatch,tmp_path):
    monkeypatch.setattr(windows_package,'package_family_name',lambda:None)
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    monkeypatch.setenv('CREDONOMICS_DATA_DIR','')
    assert storage.data_directory()==tmp_path/'CredoNomicsCyberSolutions'


def test_master_exports_and_ico_sizes():
    root=Path(__file__).resolve().parents[1]
    assert Image.open(root/'store-assets/shared-brand/master-logo-2048.png').size==(2048,2048)
    icon=Image.open(root/'assets/app.ico')
    assert {(16,16),(32,32),(48,48),(256,256)}<=icon.ico.sizes()


@pytest.mark.parametrize('size',[(1480,960),(860,620)])
def test_publisher_is_visible_without_widening_navigation(tmp_path,size):
    from cyber.ui import MainWindow
    app=QApplication.instance() or QApplication([])
    window=MainWindow(storage.Store(tmp_path/'publisher.db'))
    window.resize(*size)
    window.show()
    app.processEvents()
    assert window.windowTitle()==BRAND
    assert window.sidebar.width()==(232 if size[0]>=1180 else 72)
    assert window.copyright_badge.isVisible()
    assert window.copyright_badge.text()==COPYRIGHT_SHORT
    if size[0]>=1180:
        assert window.sidebar_publisher.isVisible() and window.local_note.isVisible()
        assert window.sidebar_publisher.text()==PUBLISHER
        for item in window.sidebar.findChildren(QLabel):
            if item.isVisible() and item.text()==PUBLISHER:
                assert item.height()>=item.heightForWidth(item.width())
    else:
        assert not window.publisher_brand_block.isVisible()
        assert not window.local_note.isVisible()
    settings=window.create_settings_dialog()
    settings.show()
    app.processEvents()
    expected={'Product Name':BRAND,'Publisher':PUBLISHER,'Website':WEBSITE,
              'Support Email':SUPPORT_EMAIL,'Support Phone':SUPPORT_PHONE,'Version':__version__}
    for name,value in expected.items():
        field=settings.publisher_identity[name]
        assert field.isVisible()
        assert field.accessibleName()==name+': '+value
    assert settings.brand_fields['company_name'].text()==PUBLISHER
    settings.close()
    window.close()
