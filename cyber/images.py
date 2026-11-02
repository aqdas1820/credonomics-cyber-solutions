# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import io
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


def load_image(value):
    from .limits import validate_pixels,MAX_IMAGE_PIXELS
    if isinstance(value, Image.Image):
        validate_pixels(value.width,value.height,MAX_IMAGE_PIXELS)
        return value.copy()
    with Image.open(io.BytesIO(value) if isinstance(value, bytes) else value) as image:
        from .limits import validate_pixels,MAX_IMAGE_PIXELS
        validate_pixels(image.width,image.height,MAX_IMAGE_PIXELS)
        image.load()
        return ImageOps.exif_transpose(image).convert('RGB')


def image_bytes(image, fmt='PNG', **kwargs):
    stream = io.BytesIO()
    if fmt.upper() in ('JPEG', 'JPG'):
        image = image.convert('RGB')
        fmt = 'JPEG'
    image.save(stream, format=fmt, **kwargs)
    return stream.getvalue()


def bounded_jpeg(image, limit_kb, width=None, height=None):
    if limit_kb < 1:
        raise ValueError('File limit must be at least 1 KB.')
    image = load_image(image)
    if width and height:
        if not (1 <= width <= 20000 and 1 <= height <= 20000) or width * height > 80_000_000:
            raise ValueError('Image dimensions exceed the 80 megapixel limit.')
        image = ImageOps.fit(image, (int(width), int(height)), Image.Resampling.LANCZOS)
    low, high, best = 1, 95, None
    while low <= high:
        quality = (low + high) // 2
        data = image_bytes(image, 'JPEG', quality=quality, optimize=True)
        if len(data) <= limit_kb * 1024:
            best, low = data, quality + 1
        else:
            high = quality - 1
    if best is None:
        raise ValueError('This KB target is impossible at these dimensions. Reduce the dimensions or raise the limit.')
    return best


def adjust(image, rotation=0, brightness=1., contrast=1., crop=None):
    image = load_image(image)
    if crop:
        x, y, w, h = map(int, crop)
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > image.width or y+h > image.height:
            raise ValueError('Crop rectangle must be inside the image.')
        image = image.crop((x, y, x+w, y+h))
    image = image.rotate(-rotation, expand=True)
    return ImageEnhance.Contrast(ImageEnhance.Brightness(image).enhance(brightness)).enhance(contrast)


def auto_crop(image):
    source = np.array(load_image(image))
    gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 140)
    contours = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:15]:
        if cv2.contourArea(contour) < source.shape[0] * source.shape[1] * .10:
            continue
        points = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
        if len(points) == 4:
            p = points.reshape(4, 2).astype('float32')
            total, diff = p.sum(axis=1), np.diff(p, axis=1).ravel()
            rect = np.array([p[total.argmin()], p[diff.argmin()], p[total.argmax()], p[diff.argmax()]], dtype='float32')
            tl, tr, br, bl = rect
            width = max(int(np.linalg.norm(tr-tl)), int(np.linalg.norm(br-bl)))
            height = max(int(np.linalg.norm(bl-tl)), int(np.linalg.norm(br-tr)))
            if width > 10 and height > 10:
                destination = np.array([[0,0], [width-1,0], [width-1,height-1], [0,height-1]], dtype='float32')
                return Image.fromarray(cv2.warpPerspective(source, cv2.getPerspectiveTransform(rect, destination), (width,height)))
    return Image.fromarray(source)


def model_path():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return root / 'models' / 'u2netp.onnx'


def remove_background(image, background='white', path=None):
    from .distribution import is_commercial_build,MODEL_UNAVAILABLE
    if is_commercial_build():
        raise ValueError(MODEL_UNAVAILABLE)
    import onnxruntime as ort
    path = Path(path or model_path())
    if not path.is_file():
        raise ValueError('Local background model is missing. Run setup-model.ps1 once while online; no model is downloaded during use.')
    original = load_image(image).convert('RGBA')
    resized = original.convert('RGB').resize((320,320), Image.Resampling.LANCZOS)
    data = np.asarray(resized).astype('float32') / 255.
    data = (data - np.array([.485,.456,.406], dtype='float32')) / np.array([.229,.224,.225], dtype='float32')
    session = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
    mask = session.run(None, {session.get_inputs()[0].name: data.transpose(2,0,1)[None]})[0][0,0]
    mask = (mask - mask.min()) / max(float(mask.max()-mask.min()), 1e-8)
    alpha = Image.fromarray((mask*255).astype('uint8')).resize(original.size, Image.Resampling.LANCZOS)
    original.putalpha(alpha)
    if background == 'transparent':
        return original
    canvas = Image.new('RGBA', original.size, background)
    return Image.alpha_composite(canvas, original).convert('RGB')


def replace_region(image, box, text='', size=24, color='#15243b', background='#ffffff', inpaint=False):
    result = load_image(image)
    x,y,w,h = map(int, box)
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > result.width or y+h > result.height:
        raise ValueError('Select a rectangle inside the image preview.')
    if inpaint:
        pixels = np.array(result)
        mask = np.zeros(pixels.shape[:2], dtype='uint8')
        mask[y:y+h, x:x+w] = 255
        result = Image.fromarray(cv2.inpaint(pixels, mask, 3, cv2.INPAINT_TELEA))
    else:
        ImageDraw.Draw(result).rectangle((x,y,x+w,y+h), fill=background)
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    font = ImageFont.truetype(str(font_path), int(size)) if font_path.exists() else ImageFont.load_default(size=int(size))
    ImageDraw.Draw(result).text((x+2,y+2), text, font=font, fill=color)
    return result


def qr_bytes(text, fmt='PNG', size=640, color='#10243a'):
    import qrcode
    import qrcode.image.svg
    if not text.strip():
        raise ValueError('Enter QR content.')
    if len(text.encode('utf-8'))>7000:
        raise ValueError('QR content is too long. Shorten the text or use a shorter link.')
    from .limits import validate_pixels,MAX_IMAGE_PIXELS
    validate_pixels(size,size,MAX_IMAGE_PIXELS)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(text)
    try:qr.make(fit=True)
    except qrcode.exceptions.DataOverflowError:
        raise ValueError('QR content is too long. Shorten the text or use a shorter link.') from None
    except ValueError as error:
        if str(error).startswith('Invalid version'):
            raise ValueError('QR content is too long. Shorten the text or use a shorter link.') from None
        raise
    if fmt == 'SVG':
        image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        stream = io.BytesIO()
        image.save(stream)
        return stream.getvalue()
    image = qr.make_image(fill_color=color, back_color='white').convert('RGB')
    return image_bytes(image.resize((size,size), Image.Resampling.NEAREST), fmt)
