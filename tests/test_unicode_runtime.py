# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise real native font/OCR APIs with non-ASCII installation resources."""

import shutil
import sys
from pathlib import Path

import pymupdf
from cyber import ui
from cyber.documents import ocr_pdf
from cyber.images import image_bytes
from cyber.storage import Store
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]


def test_unicode_installation_loads_actual_bundled_fonts(tmp_path, monkeypatch):
    root = tmp_path / "हिन्दी 😀"
    shutil.copytree(ROOT / "assets/fonts", root / "assets/fonts")
    app = QApplication.instance() or QApplication([])
    loaded = []
    for method in ("addApplicationFont", "addApplicationFontFromData"):
        original = getattr(QFontDatabase, method)

        def track(value, original=original):
            index = original(value)
            loaded.append(index)
            return index

        monkeypatch.setattr(QFontDatabase, method, track)
    monkeypatch.setattr(sys, "_MEIPASS", str(root), raising=False)
    window = ui.MainWindow(Store(tmp_path / "fonts.db"))
    app.processEvents()
    try:
        assert len(loaded) == 2
        assert all(index >= 0 and "Lato" in QFontDatabase.applicationFontFamilies(index) for index in loaded)
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        for index in loaded:
            if index >= 0:
                QFontDatabase.removeApplicationFont(index)


def test_unicode_installation_ocr_recognises_real_image_and_cleans_staging(tmp_path, monkeypatch):
    root = tmp_path / "हिन्दी 😀"
    (root / "tessdata").mkdir(parents=True)
    shutil.copyfile(ROOT / "tessdata/eng.traineddata", root / "tessdata/eng.traineddata")
    state = tmp_path / "ocr-state"
    monkeypatch.setenv("CREDONOMICS_DATA_DIR", str(state))
    monkeypatch.setenv("TESSDATA_PREFIX", str(ROOT / "tessdata"))
    monkeypatch.setattr(sys, "_MEIPASS", str(root), raising=False)
    image = Image.new("RGB", (1200, 400), "white")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
    ImageDraw.Draw(image).text((50, 100), "CREDONOMICS TEST", font=font, fill="black")
    with pymupdf.open() as source:
        page = source.new_page(width=600, height=200)
        page.insert_image(page.rect, stream=image_bytes(image))
        data = source.tobytes()
    result = ocr_pdf(data)
    with pymupdf.open(stream=result, filetype="pdf") as output:
        assert "CREDONOMICS TEST" in output[0].get_text().upper()
    assert not list((state / "temporary-work").glob("job-*"))
