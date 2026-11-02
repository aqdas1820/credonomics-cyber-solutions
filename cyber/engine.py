# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import io
import json
import math
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pymupdf as fitz
from PIL import Image

from . import documents as pdf
from . import images
from .business import invoice_pdf,resume_pdf,resume_docx
from .storage import Store
from .limits import raster_page,validate_pixels,MAX_IMAGE_PIXELS,input_limit


@dataclass
class Result:
    data: bytes
    extension: str
    name: str
    message: str='Ready. Save or print when you are happy with the result.'
    preview: bytes|None=None
    record: dict|None=None


def rectangle(text):
    if not str(text).strip():
        return None
    try:
        values=[float(v.strip()) for v in text.split(',')]
        if len(values)!=4 or any(not math.isfinite(v) or v<0 for v in values) or values[2]<=0 or values[3]<=0:
            raise ValueError()
        return values
    except (ValueError,TypeError):
        raise ValueError('Rectangle must be x,y,width,height with positive dimensions.') from None


def execute(tool,files,options,store=None):
    store=store or Store()
    generators=('QR Generator','Resume Maker','Bill Maker')
    if tool not in generators and not files:
        raise ValueError('Open or drop at least one file first.')
    maximum=input_limit(tool,options)
    if maximum and len(files)>maximum:
        raise ValueError(f'This tool accepts at most {maximum} input '+('file' if maximum==1 else 'files')+' per job. Use Start another before loading a different document.')
    first=files[0] if files else None
    def out(data,ext='pdf',message='',preview=None,record=None):
        return Result(data,ext,tool.lower().replace(' ','-')+'.'+ext,message or 'Ready. Save or print when you are happy with the result.',preview,record)
    if tool=='Print':
        if 'current_input' in options:
            index=int(options['current_input'])
            if not 0<=index<len(files):
                raise ValueError('Select an input document before printing its current page.')
            files=[files[index]]
        merged=pdf.merge_documents(files)
        return out(pdf.extract_pages(merged,options['pages'],int(options['rotation']),options['colour']=='Black & white'))
    if tool in ('PVC Tool','Auto ID Card'):
        return out(pdf.card_sheet(files,options['paper'],float(options['width']),float(options['height']),options['autocrop']))
    if tool=='Signature Check':
        report=pdf.signature_report(first,options.get('trust') or None)
        return out(json.dumps(report,indent=2).encode(),'json',message='Signature inspection complete. Integrity and certificate trust are separate results.')
    if tool in ('Auto Crop','Portal PDF Pack'):
        merged=fitz.open()
        try:
            for path in files:
                with fitz.open(stream=pdf.as_pdf(path),filetype='pdf') as source:
                    for page in source:
                        pix=raster_page(page,dpi=160,colorspace=fitz.csRGB,alpha=False)
                        image=images.auto_crop(Image.frombytes('RGB',(pix.width,pix.height),pix.samples))
                        if options.get('bw'):
                            image=image.convert('L').point(lambda x:255 if x>170 else 0).convert('RGB')
                        p=merged.new_page(width=595.276,height=841.89)
                        p.insert_image(p.rect+(18,18,-18,-18),stream=images.image_bytes(image))
            data=merged.tobytes(garbage=4,deflate=True)
        finally:
            merged.close()
        if tool=='Portal PDF Pack':
            data=pdf.compress_pdf(data,int(options['kb']))
        return out(data,message='Cropped and rasterised locally. Check page edges in the preview before saving.')
    if tool=='PDF Editor':
        if options['mode']=='OCR':
            return out(pdf.ocr_pdf(first,{'English':'eng','Hindi':'hin','English + Hindi':'eng+hin'}[options.get('language','English')]))
        return out(pdf.edit_pdf(first,int(options['page'])-1,options['find'],options['text'],rectangle(options['box']),float(options['size']),{'Replace':'replace','Redact':'redact','Add text':'text','Rotate':'rotate'}[options['mode']]),message='PDF updated. Replaced/redacted source content is removed; editing invalidates existing digital signatures.')
    if tool=='Edit Screenshot':
        box=rectangle(options['box'])
        if not box:
            raise ValueError('Drag a rectangle over the preview or enter its coordinates.')
        image=images.replace_region(first,box,options['text'],float(options['size']),options['color'],options['background'],options['inpaint'])
        return out(images.image_bytes(image),'png')
    if tool in ('Photo Print','Photo & Sign','PAN Tool'):
        image=images.adjust(first,int(options.get('rotation',0)),float(options.get('brightness',1)),float(options.get('contrast',1)),rectangle(options.get('box','')))
        if options.get('background') in ('White','Transparent'):
            image=images.remove_background(image,'white' if options['background']=='White' else 'transparent')
        if tool=='Photo Print':
            return out(pdf.passport_sheet(image,float(options['width']),float(options['height']),int(options['copies']),options['paper']))
        if tool=='Photo & Sign':
            if options['format']=='PNG':
                from PIL import ImageOps
                validate_pixels(int(options['width']),int(options['height']),MAX_IMAGE_PIXELS)
                fitted=ImageOps.fit(image,(int(options['width']),int(options['height'])),Image.Resampling.LANCZOS)
                data=images.image_bytes(fitted,'PNG',optimize=True)
                if len(data)>int(options['kb'])*1024:
                    raise ValueError('PNG cannot meet this KB target. Select JPEG or raise the size limit.')
                return out(data,'png')
            return out(images.bounded_jpeg(image,int(options['kb']),int(options['width']),int(options['height'])),'jpg')
        output=fitz.open()
        page=output.new_page(width=595.276,height=841.89)
        page.insert_text((40,50),'PAN application attachments',fontsize=18)
        page.insert_text((40,72),'Photo and signature sizing sheet - not an identity document',fontsize=10)
        page.insert_image(fitz.Rect(40,100,40+25*pdf.MM,100+35*pdf.MM),stream=images.image_bytes(image))
        if len(files)>1:
            page.insert_image(fitz.Rect(40,230,40+40*pdf.MM,230+20*pdf.MM),stream=images.image_bytes(images.load_image(files[1])))
        page.insert_text((40,310),'Photo: 25 x 35 mm | Signature: 40 x 20 mm',fontsize=11)
        data=output.tobytes()
        output.close()
        return out(data)
    if tool=='Merge Tool':
        return out(pdf.merge_documents(files))
    if tool=='Compress':
        if options['type']=='Image':
            image=images.load_image(first)
            return out(images.bounded_jpeg(image,int(options['kb'])),'jpg')
        return out(pdf.compress_pdf(pdf.merge_documents(files),int(options['kb'])),message='Compressed locally. If rasterisation was needed, searchable text, links and signatures are not retained.')
    if tool=='Mini Print':
        return out(pdf.n_up(pdf.merge_documents(files),int(options['layout']),options['paper']))
    if tool=='QR Generator':
        fmt=options['format']
        data=images.qr_bytes(options['text'],fmt,int(options['size']),options['color'])
        preview=images.qr_bytes(options['text'],'PNG',int(options['size']),options['color']) if fmt=='SVG' else None
        return out(data,'jpg' if fmt=='JPEG' else fmt.lower(),preview=preview)
    if tool=='Resume Maker':
        data={k:str(options.get(k,'')) for k in ('name','role','phone','email','city','summary','experience','education','skills','projects')}
        design=int(options['design'])
        preview=resume_pdf(data,design)
        document=resume_docx(data,design) if options['format']=='Word' else preview
        return out(document,'docx' if options['format']=='Word' else 'pdf',preview=preview,record={'kind':'resume','phone':data['phone'],'title':data['name'],'body':dict(options)})
    if tool=='Bill Maker':
        data=dict(options)
        data['number']=data.get('number') or store.next_number()
        data['date']=data.get('date') or date.today().isoformat()
        result,totals=invoice_pdf(data,store.get('business',{}),int(options['design']))
        return out(result,record={'kind':'invoice','phone':data.get('phone',''),'title':data['number'],'body':data})
    if tool=='Convert':
        fmt=options['format']
        source=pdf.merge_documents(files)
        if fmt=='PDF':
            return out(source)
        with fitz.open(stream=source,filetype='pdf') as document:
            if fmt in ('PNG','JPEG'):
                archive=io.BytesIO()
                preview=None
                with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
                    for i,page in enumerate(document):
                        pix=raster_page(page,dpi=int(options['dpi']),colorspace=fitz.csRGB,alpha=False)
                        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                        data=images.image_bytes(image,fmt)
                        preview=preview or data
                        bundle.writestr(f'page-{i+1:03d}.{fmt.lower()}',data)
                return out(archive.getvalue(),'zip',preview=preview)
            text='\n\n'.join(page.get_text() for page in document)
            if fmt=='Text':
                return out(text.encode('utf-8'),'txt')
            if fmt=='Word':
                from docx import Document
                result=Document()
                for page in document:
                    result.add_paragraph(page.get_text())
                    result.add_page_break()
                stream=io.BytesIO()
                result.save(stream)
                return out(stream.getvalue(),'docx',message='Extracted PDF text to Word. Scanned text requires OCR first; complex layouts are not preserved.',preview=source)
            if fmt=='Excel':
                from openpyxl import Workbook
                workbook=Workbook()
                sheet=workbook.active
                sheet.title='Extracted text'
                for i,page in enumerate(document):
                    tables=page.find_tables()
                    if tables.tables:
                        for table in tables:
                            for row in table.extract():
                                sheet.append([str(c or '') for c in row])
                    else:
                        for line in page.get_text().splitlines():
                            sheet.append([i+1,line])
                stream=io.BytesIO()
                for row in sheet:
                    for cell in row:
                        if isinstance(cell.value,str):cell.data_type='s'
                workbook.save(stream)
                return out(stream.getvalue(),'xlsx',message='Tables extracted where detectable; other content is exported as page-numbered text.',preview=source)
    if tool=='Scan':
        return out(pdf.merge_documents(files))
    raise ValueError('Choose a supported tool.')
