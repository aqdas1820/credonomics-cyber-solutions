# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import io
import json
import zipfile
from decimal import Decimal

import cv2
import numpy as np
import pymupdf as fitz
import pytest
from PIL import Image,ImageDraw
from docx import Document

from cyber import documents as pdf,images
from cyber.business import invoice_totals,resume_pdf,resume_docx,invoice_pdf
from cyber.catalog import TOOLS
from cyber.engine import execute,rectangle
from cyber.storage import Store
from cyber.devices import mask_frame


def options(tool):
    result={field.key:field.default for field in tool.fields}
    if 'design' in result:
        result['design']=0
    return result


def test_merge_order_and_original_preserved(sample):
    original=sample['pdf'].read_bytes()
    data=pdf.merge_documents([sample['pdf'],sample['photo']])
    with fitz.open(stream=data,filetype='pdf') as doc:
        assert len(doc)==3
        assert 'Alpha' in doc[0].get_text()
        assert 'Beta' in doc[1].get_text()
    assert sample['pdf'].read_bytes()==original


@pytest.mark.parametrize('spec',['0','3','2-1','1-x','1-2-3'])
def test_invalid_page_ranges(spec):
    with pytest.raises(ValueError):
        pdf.parse_pages(spec,2)


def test_page_selection_and_nup(sample):
    data=pdf.extract_pages(sample['pdf'],'2,1',90)
    with fitz.open(stream=data,filetype='pdf') as doc:
        assert 'Beta' in doc[0].get_text()
        assert doc[0].rotation==90
    data=pdf.n_up(sample['pdf'],2)
    with fitz.open(stream=data,filetype='pdf') as doc:
        assert len(doc)==1
        assert 'Alpha' in doc[0].get_text() and 'Beta' in doc[0].get_text()


def test_redaction_actually_removes_text(sample):
    edited=pdf.edit_pdf(sample['pdf'],0,'Original Alpha','CredoNomics',size=16)
    with fitz.open(stream=edited,filetype='pdf') as doc:
        text=doc[0].get_text()
        assert 'Original Alpha' not in text
        assert 'CredoNomics' in text
    with fitz.open(sample['pdf']) as original:
        assert 'Original Alpha' in original[0].get_text()


def test_image_size_and_impossible_target(sample):
    data=images.bounded_jpeg(sample['photo'],20,350,450)
    assert len(data)<=20*1024
    assert Image.open(io.BytesIO(data)).size==(350,450)
    noise=Image.fromarray(np.random.default_rng(4).integers(0,255,(500,500,3),dtype=np.uint8))
    with pytest.raises(ValueError):
        images.bounded_jpeg(noise,1,500,500)
    with pytest.raises(ValueError):
        images.adjust(sample['photo'],crop=(0,0,99999,5))


def test_auto_crop_and_image_edit():
    image=Image.new('RGB',(600,400),'#202020')
    ImageDraw.Draw(image).rectangle((60,60,540,340),fill='white')
    cropped=images.auto_crop(image)
    assert 450<cropped.width<500
    assert 260<cropped.height<300
    edited=images.replace_region(image,(100,100,50,50),'X',18)
    assert edited.size==image.size
    assert edited.getpixel((100,100))==(255,255,255)


def test_compression_limit(sample):
    assert len(pdf.compress_pdf(sample['pdf'],50))<=50*1024
    with pytest.raises(ValueError):
        pdf.compress_pdf(sample['pdf'],0)


def test_physical_layouts(sample):
    data=pdf.passport_sheet(sample['photo'],35,45,8,'4x6')
    with fitz.open(stream=data,filetype='pdf') as doc:
        assert len(doc)==2
        assert round(doc[0].rect.width)==288
    data=pdf.card_sheet([sample['photo'],sample['photo']])
    with fitz.open(stream=data,filetype='pdf') as doc:
        assert len(doc)==1
        assert len(doc[0].get_images())>=1
    with pytest.raises(ValueError):
        pdf.passport_sheet(sample['photo'],500,500,1)


def test_qr_can_be_decoded():
    data=images.qr_bytes('CredoNomics offline test')
    pixels=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
    decoded,_,_=cv2.QRCodeDetector().detectAndDecode(pixels)
    assert decoded=='CredoNomics offline test'
    assert b'<svg' in images.qr_bytes('SVG test','SVG')


@pytest.mark.parametrize('design',range(10))
def test_ten_business_designs(design):
    person=dict(name='Sample Applicant',phone='0000000000',summary='Customer service',experience='Print assistant',education='Diploma',skills='Office')
    with fitz.open(stream=resume_pdf(person,design),filetype='pdf') as doc:
        assert 'Sample Applicant' in doc[0].get_text()
    word=Document(io.BytesIO(resume_docx(person,design)))
    assert 'Sample Applicant' in '\n'.join(p.text for p in word.paragraphs)
    data,totals=invoice_pdf({'customer':'Sample','items':[{'description':'Print','qty':'3','rate':'2.50','tax':'18'}]}, {'name':'CredoNomics'},design)
    with fitz.open(stream=data,filetype='pdf') as doc:
        assert '8.85' in doc[0].get_text()
    assert totals['total']=='8.85'


@pytest.mark.parametrize('value',['NaN','Infinity','-1'])
def test_invoice_rejects_invalid_amounts(value):
    with pytest.raises(ValueError):
        invoice_totals([{'description':'Print','qty':value,'rate':'1'}])


def test_store_recall_and_delete(tmp_path):
    store=Store(tmp_path/'test.db')
    store.set('business',{'name':'CreDo'})
    assert store.get('business')['name']=='CreDo'
    assert store.next_number()=='CN-00001'
    assert store.next_number()=='CN-00002'
    ident=store.save_record('resume','123456','Person',{'name':'Person'})
    assert store.records('resume','345')[0]['id']==ident
    store.delete_record(ident)
    assert store.records('resume')==[]


@pytest.mark.parametrize('fmt',['PDF','PNG','JPEG','Word','Excel','Text'])
def test_conversion_formats(sample,fmt):
    tool=next(t for t in TOOLS if t.name=='Convert')
    opts=options(tool)|{'format':fmt}
    result=execute(tool.name,[str(sample['pdf'])],opts,Store(sample['directory']/'store.db'))
    if fmt in ('PNG','JPEG'):
        with zipfile.ZipFile(io.BytesIO(result.data)) as bundle:
            assert len(bundle.namelist())==2
    elif fmt=='Word':
        assert 'Original Alpha' in '\n'.join(p.text for p in Document(io.BytesIO(result.data)).paragraphs)
    elif fmt=='Excel':
        from openpyxl import load_workbook
        assert load_workbook(io.BytesIO(result.data)).active.max_row>=2
    elif fmt=='Text':
        assert b'Original Alpha' in result.data
    else:
        assert result.data.startswith(b'%PDF')


@pytest.mark.parametrize('name',['Print','Scan','PVC Tool','Auto ID Card','Auto Crop','Portal PDF Pack','PDF Editor','Edit Screenshot','Photo Print','Photo & Sign','PAN Tool','Merge Tool','Compress','Mini Print','QR Generator','Resume Maker','Bill Maker'])
def test_workspace_engine_paths(sample,name):
    tool=next(t for t in TOOLS if t.name==name)
    opts=options(tool)
    photo_tools={'PVC Tool','Auto ID Card','Auto Crop','Portal PDF Pack','Edit Screenshot','Photo Print','Photo & Sign','PAN Tool'}
    files=[str(sample['photo'] if name in photo_tools else sample['pdf'])]
    if name=='PDF Editor':
        opts|={'find':'Original Alpha','text':'Corrected'}
    if name=='Edit Screenshot':
        opts|={'box':'0,0,100,100','text':'Sample'}
    if name=='Resume Maker':
        opts|={'name':'Test Applicant'}
    if name=='Bill Maker':
        opts|={'items':[{'description':'Print','qty':'2','rate':'5','tax':'0'}]}
    result=execute(name,files,opts,Store(sample['directory']/'store.db'))
    assert len(result.data)>50


def test_unsigned_pdf_not_reported_verified(sample):
    report=pdf.signature_report(sample['pdf'])
    assert report['signatures']==[]
    assert 'unsigned' in report['trust_note']


def test_masks_are_applied_to_saved_frame():
    image=np.full((50,80,3),255,dtype=np.uint8)
    result=mask_frame(image,[(5,5,20,10)])
    assert not result[5:15,5:25].any()
    assert result[0,0].all()
    assert image.all()


def test_missing_background_model_does_not_download(sample,tmp_path):
    from cyber.distribution import is_commercial_build
    with pytest.raises(ValueError,match='unavailable in this candidate' if is_commercial_build() else 'model is missing'):
        images.remove_background(sample['photo'],path=tmp_path/'missing.onnx')


@pytest.mark.parametrize('text',['x,y,3,4','1,2','0,0,-1,3'])
def test_rectangle_validation(text):
    with pytest.raises(ValueError):
        rectangle(text)
