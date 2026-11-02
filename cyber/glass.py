# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Native Qt navigation surfaces inspired by the referenced glass UI libraries.

Painted, controlled backdrops; no framebuffer capture or platform blur dependency.
"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import QFrame


class GlassSurface(QFrame):
    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.dark=dark
        self.effects=True
        self.accent='#007d70'
        self.theme=None

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        radius=0 if self.dark else 12
        base=QColor(self.theme['sidebar' if self.dark else 'hero'] if self.theme else '#172535' if self.dark else '#f5faf9')
        if not self.effects:
            painter.setBrush(base)
        else:
            gradient=QLinearGradient(bounds.topLeft(),bounds.bottomRight())
            gradient.setColorAt(0,QColor(self.theme['sidebar_hover' if self.dark else 'surface'] if self.theme else '#253b50' if self.dark else '#ffffff'))
            gradient.setColorAt(1,base)
            painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bounds,radius,radius)
        if self.effects:
            painter.save()
            from PySide6.QtGui import QPainterPath
            clip=QPainterPath()
            clip.addRoundedRect(bounds,radius,radius)
            painter.setClipPath(clip)
            glow=QRadialGradient(bounds.width()*.85,bounds.height()*.12,max(bounds.width(),bounds.height())*.8)
            tint=QColor(self.accent)
            tint.setAlpha(48 if self.dark else 30)
            glow.setColorAt(0,tint)
            glow.setColorAt(1,QColor(0,0,0,0))
            painter.fillRect(bounds,glow)
            painter.restore()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(self.theme['border']) if self.theme else QColor(255,255,255,38) if self.dark else QColor('#d8e8e4'),1))
        painter.drawRoundedRect(bounds,radius,radius)
