# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import time
import cv2
import numpy as np
import mss
from cyber.devices import Recorder


def test_video_writer_and_stop_apply_masks(monkeypatch,tmp_path):
    class SyntheticScreen:
        monitors=[{},dict(left=0,top=0,width=160,height=120)]
        def __enter__(self):
            return self
        def __exit__(self,*args):
            pass
        def grab(self,area):
            return np.full((120,160,4),255,dtype=np.uint8)
    monkeypatch.setattr(mss,'mss',SyntheticScreen)
    output=tmp_path/'recording.avi'
    recorder=Recorder()
    recorder.start(output,[(20,20,50,40)],fps=10)
    deadline=time.monotonic()+5
    while recorder.frames<3 and time.monotonic()<deadline:
        time.sleep(.02)
    assert recorder.stop()>=3
    assert not recorder.running
    capture=cv2.VideoCapture(str(output))
    success,frame=capture.read()
    capture.release()
    assert success
    assert frame[25:50,25:60].mean()<12
    assert frame[80:100,100:130].mean()>240
