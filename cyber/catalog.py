# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
from dataclasses import dataclass


@dataclass
class Field:
    key: str
    label: str
    default: object=''
    choices: tuple=()
    kind: str='text'
    hint: str=''


@dataclass
class Tool:
    name: str
    icon: str
    group: str
    description: str
    fields: tuple=()
    note: str=''


def f(key,label,default='',choices=(),kind='text',hint=''):
    return Field(key,label,default,tuple(choices),kind,hint)


PAPER=('A4','A3','A2','A1','4x6')
CROP=f('box','Selection (x, y, width, height)',hint='Drag over the preview, or type coordinates')
BACKGROUND=f('background','Photo background','Keep original',('Keep original','White','Transparent'))
DESIGNS=('Executive','Modern','Classic','Minimal','Editorial','Studio','Professional','Academic','Slate','Elegant')
TOOLS=[
    Tool('Print','PR','Print & scan','Prepare a document, choose pages and send it to your printer.',(
        f('pages','Pages','all'),f('colour','Colour','Colour',('Colour','Black & white')),f('rotation','Rotation','0',('0','90','180','270')),f('copies','Copies',1,kind='int'),f('duplex','Print both sides',False,kind='bool')), 'Prepare first, then use Print for the Windows printer dialog. Hardware decides which paper sizes and duplex modes are available.'),
    Tool('Scan','SC','Print & scan','Bring paper into your workspace. Add scans and build one PDF.',(
        f('dpi','Scan resolution','300',('75','150','200','300','600')),), 'Choose a WIA scanner with a Windows driver. Scan another page to build a multi-page document. Imported scans also work.'),
    Tool('PVC Tool','PV','Cards & forms','Crop and position cards at precise physical dimensions.',(
        f('width','Card width (mm)',85.6,kind='float'),f('height','Card height (mm)',54.,kind='float'),f('paper','Paper','A4',PAPER),f('autocrop','Detect card edges',True,kind='bool'))),
    Tool('Auto ID Card','ID','Cards & forms','Lay out fronts and backs together on a print-ready sheet.',(
        f('width','Card width (mm)',85.6,kind='float'),f('height','Card height (mm)',54.,kind='float'),f('paper','Paper','A4',PAPER),f('autocrop','Detect card edges',True,kind='bool')), 'Arrange the file list as front, back, front, back. Pairing follows your order; personal identity data is not guessed.'),
    Tool('Signature Check','ES','Documents','Inspect digital signatures, document integrity and local certificate trust.',(
        f('trust','Trusted root certificate (optional)',hint='Local .pem / .cer file path'),), 'This verifies existing signatures; it does not forge, remove or make a signature trusted. Offline checks cannot establish current revocation status.'),
    Tool('Auto Crop','AC','Documents','Straighten document edges and turn phone photos into a clean PDF.',(
        f('bw','High-contrast black & white',False,kind='bool'),)),
    Tool('Portal PDF Pack','JH','Cards & forms','Combine attachments into one PDF within a portal size limit.',(
        f('kb','Maximum size (KB)',500,kind='int'),f('bw','High-contrast black & white',False,kind='bool')), 'Compression can rasterise pages. Check readability before submitting. Files stay local; nothing is submitted to a portal.'),
    Tool('PDF Editor','PE','Documents','Replace text, add a correction, redact content or rotate a page.',(
        f('mode','Action','Replace',('Replace','Add text','Redact','Rotate','OCR')),f('page','Page',1,kind='int'),f('find','Find text'),f('text','New text'),f('size','Font size (pt)',12.,kind='float'),CROP,f('language','OCR language','English',('English','Hindi','English + Hindi'))), 'Select a region on a scanned page or search editable text. Edits invalidate signatures. OCR uses bundled local language data. Exact original font matching is not guaranteed.'),
    Tool('Edit Screenshot','SS','Photos & images','Replace words or hide a selected region in an image.',(
        CROP,f('text','Replacement text'),f('size','Font size (px)',24.,kind='float'),f('color','Text colour','#15243b'),f('background','Fill colour','#ffffff'),f('inpaint','Blend surrounding background',False,kind='bool'))),
    Tool('Photo Print','PP','Photos & images','Create passport photo sheets with physical sizes and cutting guides.',(
        f('width','Photo width (mm)',35.,kind='float'),f('height','Photo height (mm)',45.,kind='float'),f('copies','Photo copies',8,kind='int'),f('paper','Sheet','4x6',PAPER),BACKGROUND,CROP)),
    Tool('Photo & Sign','PS','Photos & images','Resize a photo or signature to exact pixels and a maximum KB.',(
        f('width','Width (pixels)',350,kind='int'),f('height','Height (pixels)',450,kind='int'),f('kb','Maximum size (KB)',50,kind='int'),f('format','Output','JPEG',('JPEG','PNG')),f('rotation','Rotation','0',('0','90','180','270')),f('brightness','Brightness',1.,kind='float'),f('contrast','Contrast',1.,kind='float'),BACKGROUND,CROP)),
    Tool('PAN Tool','PN','Cards & forms','Prepare photo and signature attachments for application forms.',(
        BACKGROUND,CROP), 'First file: photo. Optional second file: signature. Creates a labelled attachment sheet, not a PAN card or a government-issued document.'),
    Tool('Merge Tool','MG','Documents','Combine PDFs, photos and Office documents in your chosen order.'),
    Tool('Compress','CP','Documents','Reduce a PDF or image to a maximum file size.',(
        f('type','Content','PDF',('PDF','Image')),f('kb','Maximum size (KB)',500,kind='int')), 'PDF compression may rasterise pages and remove searchable text, links and digital signatures. Originals stay unchanged.'),
    Tool('Convert','CV','Documents','Move between PDF, images, text, Word and Excel.',(
        f('format','Convert to','PDF',('PDF','PNG','JPEG','Word','Excel','Text')),f('dpi','Image resolution','150',('72','96','150','200','300'))), 'DOCX/XLSX use a basic local layout. Legacy Office files require installed LibreOffice. PDF to Word extracts text; Excel detects tables where possible. Multi-page images are exported as a ZIP.'),
    Tool('Mini Print','MP','Print & scan','Place 2–16 document pages on a single sheet.',(
        f('layout','Pages per sheet','4',('2','4','6','8','9','12','16')),f('paper','Paper','A4',PAPER))),
    Tool('QR Generator','QR','Business','Create a scannable QR for a link, text, contact or UPI request.',(
        f('text','QR content','https://example.com',kind='multiline'),f('format','Output','PNG',('PNG','JPEG','SVG')),f('size','Image size (pixels)',640,kind='int'),f('color','QR colour','#10243a'))),
    Tool('Resume Maker','RM','Business','Build a professional resume in ten styles. Export PDF or Word.',(
        f('design','Design','Executive',DESIGNS),f('format','Output','PDF',('PDF','Word')),f('name','Full name'),f('role','Professional title'),f('phone','Phone'),f('email','Email'),f('city','Location'),f('summary','Profile',kind='multiline'),f('experience','Experience',kind='multiline'),f('education','Education',kind='multiline'),f('skills','Skills',kind='multiline'),f('projects','Projects & certifications',kind='multiline'))),
    Tool('Bill Maker','BL','Business','Create clear invoices with your brand, tax totals and a UPI QR.',(
        f('design','Design','Executive',DESIGNS),f('number','Invoice number',hint='Blank generates a local invoice number'),f('customer','Customer','Walk-in customer'),f('phone','Phone'),f('notes','Notes',kind='multiline')), 'Set your business details and UPI ID in Settings. An invoice is saved to local history only when you export it.'),
    Tool('Screen Recording','SR','Utilities','Record your screen locally and mask private areas.',(
        f('fps','Frames per second',10,kind='int'),f('monitor','Monitor number',1,kind='int'),f('masks','Privacy masks (one x,y,width,height per line)',kind='multiline')), 'Mask coordinates are relative to the selected monitor, in pixels. Silent AVI recording; audio is not captured. Recording begins only when you press Start.'),
]
BY_NAME={t.name:t for t in TOOLS}
