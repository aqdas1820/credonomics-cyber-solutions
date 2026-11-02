# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import io
import math
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pymupdf as fitz
from PIL import Image

from .images import auto_crop, image_bytes, load_image
from .limits import raster_page
from .tempfiles import temporary_workspace

MM = 72 / 25.4
PAPERS = {'A4': (595.276,841.89), 'A3': (841.89,1190.55), 'A2': (1190.55,1683.78), 'A1': (1683.78,2383.94), '4x6': (288,432)}


def parse_pages(spec, count):
    if not spec.strip() or spec.lower() == 'all':
        return list(range(count))
    result = []
    for part in spec.split(','):
        try:
            ends = part.strip().split('-')
            if len(ends) > 2:
                raise ValueError()
            start, end = int(ends[0]), int(ends[-1])
        except ValueError:
            raise ValueError('Pages must look like 1-3,5 or all.') from None
        if start < 1 or end > count or start > end:
            raise ValueError(f'Page range must be between 1 and {count}.')
        for number in range(start-1,end):
            if number not in result:
                result.append(number)
    return result


def office_pdf(path):
    import os
    import sys
    if Path(path).suffix.lower() in ('.docx','.xlsx') and not os.environ.get('CREDONOMICS_OFFICE_BINARY'):
        from .office import render_ooxml
        return render_ooxml(path)
    executable = os.environ.get('CREDONOMICS_OFFICE_BINARY') or shutil.which('soffice')
    if not executable:
        for candidate in ('C:/Program Files/LibreOffice/program/soffice.exe', 'C:/Program Files (x86)/LibreOffice/program/soffice.exe'):
            if Path(candidate).exists():
                executable = candidate
                break
    if not executable:
        raise ValueError('Install LibreOffice locally for Office-to-PDF conversion. Your document is not uploaded.')
    console=Path(executable).with_suffix('.com')
    if __import__('sys').platform=='win32' and console.exists():
        executable=str(console)
    with temporary_workspace() as directory:
        profile = Path(directory,'profile').as_uri()
        process=subprocess.Popen([executable, f'-env:UserInstallation={profile}', '--headless', '--nologo', '--nodefault', '--norestore', '--convert-to', 'pdf', '--outdir', directory, str(Path(path).resolve())], stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            stdout,stderr=process.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            if __import__('sys').platform=='win32':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            else:
                process.kill()
            process.communicate(timeout=10)
            raise ValueError('Local Office conversion timed out. Check the LibreOffice installation and document.') from None
        output = Path(directory,Path(path).stem+'.pdf')
        if process.returncode or not output.exists():
            raise ValueError('LibreOffice could not convert this document. Check its installation, or that the file is not corrupt or password protected. '+stderr.decode(errors='replace')[-250:])
        return output.read_bytes()


def as_pdf(value):
    if isinstance(value, bytes):
        source = fitz.open(stream=value)
    else:
        path = Path(value)
        if path.suffix.lower() in ('.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp'):
            return office_pdf(path)
        if path.suffix.lower() in ('.jpg','.jpeg','.png','.bmp','.tif','.tiff','.webp'):
            output = fitz.open()
            with Image.open(path) as image:
                from PIL import ImageOps
                for index in range(getattr(image,'n_frames',1)):
                    image.seek(index)
                    frame = ImageOps.exif_transpose(image.copy()).convert('RGB')
                    page = output.new_page(width=595.276,height=841.89)
                    page.insert_image(page.rect+ (18,18,-18,-18),stream=image_bytes(frame))
            data = output.tobytes(garbage=4,deflate=True)
            output.close()
            return data
        source = fitz.open(path)
    try:
        if source.needs_pass:
            raise ValueError('This PDF requires its owner password. Unlock it with authorisation before importing.')
        return source.tobytes(garbage=4,deflate=True) if source.is_pdf else source.convert_to_pdf()
    finally:
        source.close()


def merge_documents(paths):
    if not paths:
        raise ValueError('Add at least one document.')
    output = fitz.open()
    try:
        for path in paths:
            with fitz.open(stream=as_pdf(path),filetype='pdf') as document:
                output.insert_pdf(document)
        return output.tobytes(garbage=4,deflate=True)
    finally:
        output.close()


def extract_pages(data, spec='all', rotation=0, grayscale=False):
    with fitz.open(stream=as_pdf(data),filetype='pdf') as source:
        output = fitz.open()
        for number in parse_pages(spec,len(source)):
            output.insert_pdf(source,from_page=number,to_page=number,rotate=rotation)
        if grayscale:
            raster = fitz.open()
            for page in output:
                pix = raster_page(page,dpi=150,colorspace=fitz.csGRAY)
                raster.new_page(width=page.rect.width,height=page.rect.height).insert_image(page.rect,stream=pix.tobytes('png'))
            output.close()
            output = raster
        data = output.tobytes(garbage=4,deflate=True)
        output.close()
        return data


def compress_pdf(data, limit_kb=500):
    if limit_kb < 1:
        raise ValueError('Enter a positive KB limit.')
    data = as_pdf(data)
    if len(data) <= limit_kb*1024:
        return data
    with fitz.open(stream=data,filetype='pdf') as source:
        compact = source.tobytes(garbage=4,deflate=True)
        if len(compact) <= limit_kb*1024:
            return compact
        # Rasterisation is explicit in the workspace: searchable text and signatures are lost.
        for dpi in (160,120,96,72,50):
            for quality in (75,45,20):
                output = fitz.open()
                for page in source:
                    pix = raster_page(page,dpi=dpi,colorspace=fitz.csRGB,alpha=False)
                    image = Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                    new = output.new_page(width=page.rect.width,height=page.rect.height)
                    new.insert_image(new.rect,stream=image_bytes(image,'JPEG',quality=quality,optimize=True))
                candidate = output.tobytes(garbage=4,deflate=True)
                output.close()
                if len(candidate) <= limit_kb*1024:
                    return candidate
    raise ValueError('Cannot meet this file limit without reducing the page count. No oversized result was saved.')


def n_up(data, per_sheet=4, paper='A4'):
    if per_sheet not in (2,4,6,8,9,12,16):
        raise ValueError('Choose 2, 4, 6, 8, 9, 12 or 16 pages per sheet.')
    width,height = PAPERS[paper]
    columns = 2 if per_sheet in (2,4,6,8) else (3 if per_sheet in (9,12) else 4)
    rows = math.ceil(per_sheet/columns)
    margin,gap = 18,8
    cellw = (width-2*margin-(columns-1)*gap)/columns
    cellh = (height-2*margin-(rows-1)*gap)/rows
    with fitz.open(stream=as_pdf(data),filetype='pdf') as source:
        output = fitz.open()
        for i in range(0,len(source),per_sheet):
            page = output.new_page(width=width,height=height)
            for j in range(min(per_sheet,len(source)-i)):
                x,y = margin+(j%columns)*(cellw+gap), margin+(j//columns)*(cellh+gap)
                page.show_pdf_page(fitz.Rect(x,y,x+cellw,y+cellh),source,i+j)
        result = output.tobytes(garbage=4,deflate=True)
        output.close()
        return result


def card_sheet(paths, paper='A4', width_mm=85.6, height_mm=54., auto=False):
    if not paths:
        raise ValueError('Add the fronts and backs in the desired order.')
    output = fitz.open()
    width,height = PAPERS[paper]
    w,h = width_mm*MM,height_mm*MM
    if w <= 0 or h <= 0 or w+36 > width or h+36 > height:
        raise ValueError('Card dimensions must fit on the selected paper.')
    columns = max(1,int((width-24)//(w+12)))
    rows = max(1,int((height-24)//(h+18)))
    page = None
    position = 0
    for path in paths:
        with fitz.open(stream=as_pdf(path),filetype='pdf') as source:
            for original in source:
                if position%(columns*rows)==0:
                    page=output.new_page(width=width,height=height)
                slot=position%(columns*rows)
                x=18+(slot%columns)*(w+12)
                y=18+(slot//columns)*(h+18)
                rect=fitz.Rect(x,y,x+w,y+h)
                if auto:
                    pix=raster_page(original,dpi=180)
                    image=auto_crop(Image.frombytes('RGB',(pix.width,pix.height),pix.samples))
                    page.insert_image(rect,stream=image_bytes(image),keep_proportion=True)
                else:
                    page.show_pdf_page(rect,source,original.number,keep_proportion=True)
                page.draw_rect(rect,color=(.65,.69,.74),dashes='[2 2]',width=.3)
                position+=1
    result=output.tobytes(garbage=4,deflate=True)
    output.close()
    return result


def passport_sheet(image, width_mm=35., height_mm=45., count=8, paper='4x6'):
    from PIL import ImageOps
    if count<1 or count>100 or min(width_mm,height_mm)<=0:
        raise ValueError('Enter positive photo dimensions and 1–100 copies.')
    image=load_image(image)
    width,height=PAPERS[paper]
    w,h=width_mm*MM,height_mm*MM
    columns=int((width-20)//(w+5))
    rows=int((height-20)//(h+8))
    if not columns or not rows:
        raise ValueError('Photo dimensions do not fit the selected paper.')
    dimensions=(round(width_mm/25.4*300),round(height_mm/25.4*300))
    from .limits import MAX_IMAGE_PIXELS, validate_pixels
    validate_pixels(*dimensions,MAX_IMAGE_PIXELS)
    fitted=ImageOps.fit(image,dimensions,Image.Resampling.LANCZOS)
    output=fitz.open()
    page=None
    for i in range(count):
        if i%(columns*rows)==0:
            page=output.new_page(width=width,height=height)
        j=i%(columns*rows)
        x,y=10+(j%columns)*(w+5),10+(j//columns)*(h+8)
        rect=fitz.Rect(x,y,x+w,y+h)
        page.insert_image(rect,stream=image_bytes(fitted))
        page.draw_rect(rect,color=(.5,.5,.5),dashes='[2 2]',width=.3)
    result=output.tobytes(garbage=4,deflate=True)
    output.close()
    return result


def edit_pdf(data, page_number, search='', replacement='', box=None, size=12, mode='replace'):
    with fitz.open(stream=as_pdf(data),filetype='pdf') as document:
        if not 0<=page_number<len(document):
            raise ValueError('Page number is outside this document.')
        page=document[page_number]
        if mode=='rotate':
            page.set_rotation((page.rotation+90)%360)
        elif mode=='text':
            x,y=(box[:2] if box else [40,40])
            page.insert_text((x,y+size),replacement,fontsize=size,fontname='helv')
        else:
            rects=[fitz.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3])] if box else page.search_for(search)
            if not rects:
                raise ValueError('Text not found. For scanned pages, select a rectangle in the preview or run OCR first.')
            for rect in rects:
                page.add_redact_annot(rect,fill=(1,1,1))
            page.apply_redactions()
            if mode!='redact':
                for rect in rects:
                    # Actual redaction removes old content; replacements may use a different available font.
                    area=fitz.Rect(rect.x0,rect.y0, max(rect.x1,rect.x0+len(replacement)*size*.6),max(rect.y1,rect.y0+size*1.8))
                    result=page.insert_textbox(area,replacement,fontsize=size,fontname='helv')
                    if result<0:
                        raise ValueError('Replacement does not fit. Reduce font size or select a larger rectangle.')
        return document.tobytes(garbage=4,deflate=True)


@contextmanager
def ocr_data_path(tesspath,codes):
    """Keep native Tesseract's Windows narrow file API away from Unicode paths."""
    import sys
    if sys.platform!='win32' or str(tesspath).isascii():
        yield str(tesspath)
        return
    with temporary_workspace() as folder:
        native=str(folder)
        if not native.isascii():
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.GetShortPathNameW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint]
            kernel.GetShortPathNameW.restype=ctypes.c_uint
            buffer=ctypes.create_unicode_buffer(32768)
            size=kernel.GetShortPathNameW(native,buffer,len(buffer))
            if 0<size<len(buffer):
                native=buffer.value
        if not native.isascii():
            raise ValueError('Local OCR needs an application-data folder with a Windows-compatible path. Contact support for help selecting a writable folder using Latin letters.')
        for code in codes:
            shutil.copyfile(tesspath/(code+'.traineddata'),Path(folder)/(code+'.traineddata'))
        yield native


def ocr_pdf(data,language='eng'):
    import os
    import sys
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    tesspath=root/'tessdata'
    if not tesspath.exists():
        tesspath=Path(os.environ.get('TESSDATA_PREFIX','C:/Program Files/Tesseract-OCR/tessdata'))
    codes=language.split('+')
    import re
    if any(not re.fullmatch(r'[A-Za-z0-9_]+',code) for code in codes):
        raise ValueError('Local OCR language selection is invalid.')
    for code in codes:
        if not (tesspath/(code+'.traineddata')).is_file():
            raise ValueError(f'Local OCR data for {code} is missing. Run setup-model.ps1 while online to provision language data.')
    with ocr_data_path(tesspath,codes) as native_tessdata,fitz.open(stream=as_pdf(data),filetype='pdf') as source:
        output=fitz.open()
        for page in source:
            pix=raster_page(page,dpi=200)
            with fitz.open(stream=pix.pdfocr_tobytes(language=language,tessdata=native_tessdata),filetype='pdf') as converted:
                output.insert_pdf(converted)
        result=output.tobytes(garbage=4,deflate=True)
        output.close()
        return result


def signature_report(path, trust_path=None):
    from pyhanko.keys import load_cert_from_pemder
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext
    context=ValidationContext(trust_roots=[load_cert_from_pemder(trust_path)] if trust_path else [],allow_fetching=False,revocation_mode='soft-fail')
    results=[]
    with open(path,'rb') as stream:
        reader=PdfFileReader(stream)
        for signature in reader.embedded_signatures:
            try:
                status=validate_pdf_signature(signature,signer_validation_context=context)
                results.append(dict(field=signature.field_name,intact=status.intact,cryptographically_valid=status.valid,trusted=status.trusted,
                    report=status.pretty_print_details()))
            except Exception as error:
                results.append(dict(field=signature.field_name,error=str(error)))
    return {'signatures':results,'trust_note':'Offline: no revocation or certificate network requests. Supply a trusted root certificate to establish a trust chain. An empty signature list means unsigned, not verified.'}
