# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import pytest
import pymupdf as fitz
from PIL import Image,ImageDraw


@pytest.fixture
def sample(tmp_path):
    pdf=tmp_path/'sample.pdf'
    document=fitz.open()
    for text in ('Original Alpha','Original Beta'):
        page=document.new_page()
        page.insert_text((60,80),text,fontsize=20)
    document.save(pdf)
    document.close()
    photo=tmp_path/'photo.png'
    image=Image.new('RGB',(700,900),'#f4f1ed')
    draw=ImageDraw.Draw(image)
    draw.ellipse((230,100,470,370),fill='#bb8866')
    draw.rounded_rectangle((120,390,580,890),40,fill='#25465d')
    draw.text((30,20),'SYNTHETIC TEST PHOTO',fill='black')
    image.save(photo)
    return {'pdf':pdf,'photo':photo,'directory':tmp_path}
