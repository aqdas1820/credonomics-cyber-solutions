# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import json
import sys
import cv2
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication,QLabel
from cyber import distribution,images
from cyber.devices import mjpeg_writer
from cyber.storage import Store
from cyber.ui import MainWindow


def test_commercial_profile_blocks_model_even_with_explicit_path(monkeypatch,sample):
    monkeypatch.setattr(distribution,'build_profile',lambda:'commercial-clearance')
    with pytest.raises(ValueError,match='unavailable in this candidate'):
        images.remove_background(sample['photo'],path=images.model_path())


def test_frozen_missing_and_malformed_profile_fail_closed(monkeypatch,tmp_path):
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(tmp_path),raising=False)
    assert distribution.is_commercial_build()
    (tmp_path/'COMMERCIAL-PROFILE.json').write_text('not-json')
    assert distribution.is_commercial_build()
    (tmp_path/'COMMERCIAL-PROFILE.json').write_text(json.dumps({'profile':'commercial-clearance'}))
    assert distribution.is_commercial_build()


def test_commercial_photo_options_explain_unavailability(monkeypatch,sample):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(distribution,'build_profile',lambda:'commercial-clearance')
    window=MainWindow(Store(sample['directory']/'commercial-options.db'))
    window.select_tool('Photo Print')
    assert not window.fields['background'].isEnabled()
    assert window.fields['background'].currentText()=='Keep'
    assert any('no model with verified redistribution rights' in item.text() for item in window.findChildren(QLabel))
    window.add_files([str(sample['photo'])])
    from cyber.engine import execute
    result=execute('Photo Print',window.inputs(),window.options(),window.store)
    assert result.data.startswith(b'%PDF')
    window.close()


def test_recording_uses_builtin_encoder_and_decoder(tmp_path):
    output=tmp_path/'builtin.avi'
    writer=mjpeg_writer(output,10,(160,120))
    assert writer.getBackendName()=='CV_MJPEG'
    for value in (20,100,220):writer.write(np.full((120,160,3),value,dtype=np.uint8))
    writer.release()
    capture=cv2.VideoCapture(str(output),cv2.CAP_OPENCV_MJPEG)
    decoded=[]
    while True:
        success,frame=capture.read()
        if not success:break
        decoded.append(frame.mean())
    assert capture.getBackendName()=='CV_MJPEG'
    capture.release()
    assert len(decoded)==3
    assert all(abs(a-b)<8 for a,b in zip(decoded,(20,100,220)))
