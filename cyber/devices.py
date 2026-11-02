# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import base64
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from .tempfiles import temporary_workspace


def powershell(script, timeout=60):
    encoded=base64.b64encode(script.encode('utf-16-le')).decode()
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or 'Windows device operation failed.')
    return result.stdout.decode('utf-8-sig',errors='replace').strip()


def scanners():
    if __import__('sys').platform!='win32':
        return []
    script="""$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; $m=New-Object -ComObject WIA.DeviceManager; $list=@(); foreach($d in $m.DeviceInfos){ if($d.Type -eq 1){ $list += @{id=$d.DeviceID;name=[string]$d.Properties.Item('Name').Value} } }; ConvertTo-Json -InputObject $list -Compress"""
    return json.loads(powershell(script) or '[]')


def scan_page(device_id, dpi=300):
    from .images import load_image
    if dpi not in (75,150,200,300,600):
        raise ValueError('Select a supported scanner resolution.')
    quoted=device_id.replace("'","''")
    with temporary_workspace() as directory:
        output=Path(directory,'page.png')
        escaped=str(output).replace("'","''")
        script=f"""$ErrorActionPreference='Stop'; $m=New-Object -ComObject WIA.DeviceManager; $device=$null; foreach($d in $m.DeviceInfos){{if($d.DeviceID -eq '{quoted}'){{$device=$d.Connect();break}}}}; if($null -eq $device){{throw 'Scanner disconnected'}}; $item=$device.Items.Item(1); $item.Properties.Item(6147).Value={dpi}; $item.Properties.Item(6148).Value={dpi}; $image=$item.Transfer('{{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}}'); $image.SaveFile('{escaped}')"""
        powershell(script,timeout=120)
        return load_image(output)


def mask_frame(frame, masks):
    height,width=frame.shape[:2]
    result=frame.copy()
    for x,y,w,h in masks:
        x1,y1=max(0,int(x)),max(0,int(y))
        x2,y2=min(width,int(x+w)),min(height,int(y+h))
        if x2>x1 and y2>y1:
            result[y1:y2,x1:x2]=0
    return result


def mjpeg_writer(path,fps,size):
    """Use OpenCV's built-in AVI/MJPEG encoder; never fall back to FFmpeg."""
    writer=cv2.VideoWriter(str(path),cv2.CAP_OPENCV_MJPEG,cv2.VideoWriter_fourcc(*'MJPG'),fps,size)
    if not writer.isOpened():
        writer.release()
        raise ValueError('The local AVI/MJPEG encoder could not create this recording.')
    return writer


class Recorder:
    def __init__(self):
        self.thread=None
        self.stop_event=threading.Event()
        self.error=None
        self.frames=0

    @property
    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def start(self,path,masks=(),fps=10,monitor=1):
        if self.running:
            raise ValueError('A recording is already running.')
        if not 1<=fps<=30:
            raise ValueError('Recording FPS must be between 1 and 30.')
        self.stop_event.clear()
        self.error=None
        self.frames=0
        def run():
            import mss
            writer=None
            try:
                with mss.mss() as screen:
                    if monitor<1 or monitor>=len(screen.monitors):
                        raise ValueError('Selected monitor is unavailable.')
                    area=screen.monitors[monitor]
                    writer=mjpeg_writer(path,fps,(area['width'],area['height']))
                    if not writer.isOpened():
                        raise ValueError('Could not create this AVI recording.')
                    while not self.stop_event.is_set():
                        started=time.monotonic()
                        frame=cv2.cvtColor(np.asarray(screen.grab(area)),cv2.COLOR_BGRA2BGR)
                        writer.write(mask_frame(frame,masks))
                        self.frames+=1
                        self.stop_event.wait(max(0,1/fps-(time.monotonic()-started)))
            except Exception as error:
                self.error=str(error)
            finally:
                if writer:
                    writer.release()
        self.thread=threading.Thread(target=run,daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        if self.running:
            raise ValueError('Recorder is still closing. Wait before exiting.')
        if self.error:
            raise ValueError(self.error)
        return self.frames
