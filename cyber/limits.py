# SPDX-License-Identifier: AGPL-3.0-only
"""Bound native bitmap allocations before decoding unusual document geometry."""
import math

MAX_RASTER_PIXELS=32_000_000
MAX_IMAGE_PIXELS=80_000_000


def input_limit(tool,options=None):
    if tool=='Compress' and (options or {}).get('type')=='Image':return 1
    return {'Photo Print':1,'Photo & Sign':1,'Edit Screenshot':1,'PDF Editor':1,'Signature Check':1,'PAN Tool':2}.get(tool)


def validate_pixels(width,height,limit=MAX_RASTER_PIXELS):
    if not all(math.isfinite(float(v)) and v>0 for v in (width,height)) or width*height>limit or max(width,height)>30000:
        raise ValueError('This page or image is too large to render safely. Reduce its dimensions or choose a lower export resolution.')


def raster_page(page,dpi=150,**kwargs):
    validate_pixels(math.ceil(page.rect.width*dpi/72),math.ceil(page.rect.height*dpi/72))
    return page.get_pixmap(dpi=dpi,**kwargs)
