# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import io
from datetime import date
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

from .images import qr_bytes

DESIGNS = ['Executive', 'Modern', 'Classic', 'Minimal', 'Editorial', 'Studio', 'Professional', 'Academic', 'Slate', 'Elegant']
PALETTES = ['#14334a','#007f78','#343c49','#242424','#734834','#525496','#225578','#2b5c45','#566274','#754761']


def styles(design=0):
    design=int(design)%10
    sheet=getSampleStyleSheet()
    accent=colors.HexColor(PALETTES[design])
    sheet.add(ParagraphStyle(name='Name',fontName='Times-Bold' if design in (2,7,9) else 'Helvetica-Bold',fontSize=26 if design%2 else 22,leading=30,textColor=accent,spaceAfter=8,alignment=1 if design in (2,3,9) else 0))
    sheet['Heading2'].textColor=accent
    sheet['Heading2'].spaceBefore=14
    sheet['BodyText'].leading=15
    return sheet,accent


def para(text, style):
    return Paragraph(escape(str(text)).replace('\n','<br/>'),style)


def resume_pdf(data, design=0):
    if not data.get('name','').strip():
        raise ValueError('Enter a name for the resume.')
    sheet,accent=styles(design)
    output=io.BytesIO()
    story=[para(data['name'],sheet['Name'])]
    story.append(para(' | '.join(str(data.get(key,'')) for key in ('role','phone','email','city') if data.get(key)),sheet['BodyText']))
    story.append(Spacer(1,10))
    for title,key in [('Profile','summary'),('Experience','experience'),('Education','education'),('Skills','skills'),('Projects & certifications','projects')]:
        value=data.get(key,'')
        if value.strip():
            story.append(para(title.upper() if design in (1,5,8) else title,sheet['Heading2']))
            for line in value.split('\n'):
                if line.strip():
                    story.append(para(line,sheet['BodyText']))
    def decorate(canvas,doc):
        canvas.setStrokeColor(accent)
        if design in (0,1,4,5,8):
            canvas.setFillColor(accent)
            canvas.rect(0,0,8 if design%2 else 14,842,fill=1,stroke=0)
        else:
            canvas.line(42,800,553,800)
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#73808b'))
        canvas.drawRightString(552,24,f'{doc.page}')
    SimpleDocTemplate(output,pagesize=(595.276,841.89),leftMargin=46,rightMargin=42,topMargin=48,bottomMargin=40).build(story,onFirstPage=decorate,onLaterPages=decorate)
    return output.getvalue()


def resume_docx(data, design=0):
    if not data.get('name','').strip():
        raise ValueError('Enter a name for the resume.')
    document=Document()
    section=document.sections[0]
    section.top_margin=Inches(.7)
    normal=document.styles['Normal']
    normal.font.name='Times New Roman' if design in (2,7,9) else 'Calibri'
    normal.font.size=Pt(11)
    document.add_heading(data['name'],0)
    document.add_paragraph(' | '.join(str(data.get(k,'')) for k in ('role','phone','email','city') if data.get(k)))
    for title,key in [('Profile','summary'),('Experience','experience'),('Education','education'),('Skills','skills'),('Projects & certifications','projects')]:
        if data.get(key,'').strip():
            heading=document.add_heading(title,1)
            for run in heading.runs:
                run.font.color.rgb=RGBColor.from_string(PALETTES[design%10][1:])
            for line in data[key].splitlines():
                if line.strip():
                    document.add_paragraph(line)
    output=io.BytesIO()
    document.save(output)
    return output.getvalue()


def invoice_totals(items):
    if not items:
        raise ValueError('Add at least one invoice item.')
    lines=[]
    subtotal=Decimal('0')
    tax_total=Decimal('0')
    for item in items:
        try:
            qty=Decimal(str(item['qty']))
            price=Decimal(str(item['rate']))
            tax=Decimal(str(item.get('tax',0)))
        except (DecimalException,KeyError,TypeError,ValueError):
            raise ValueError('Quantity, rate and tax must be valid numbers.') from None
        if not all(v.is_finite() for v in (qty,price,tax)) or qty<=0 or price<0 or not 0<=tax<=100:
            raise ValueError('Use a positive quantity, nonnegative rate and a tax percentage from 0 to 100.')
        try:
            amount=(qty*price).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            taxed=(amount*tax/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            subtotal+=amount
            tax_total+=taxed
        except DecimalException:
            raise ValueError('Quantity and rate are too large. Reduce the amounts.') from None
        lines.append(dict(description=str(item.get('description','Service')),qty=str(qty),rate=f'{price:.2f}',tax=f'{tax:g}',amount=f'{amount:.2f}'))
    return dict(items=lines,subtotal=f'{subtotal:.2f}',tax=f'{tax_total:.2f}',total=f'{subtotal+tax_total:.2f}')


def invoice_pdf(data, business, design=0):
    totals=invoice_totals(data.get('items',[]))
    sheet,accent=styles(design)
    stream=io.BytesIO()
    heading=business.get('name') or 'CredoNomics Cyber Solutions'
    story=[para(heading,sheet['Name']),para(business.get('address',''),sheet['BodyText'])]
    if business.get('gstin'):
        story.append(para('GSTIN: '+business['gstin'],sheet['BodyText']))
    if business.get('logo'):
        from pathlib import Path
        logo=Path(business['logo'])
        if logo.is_file():
            from .images import load_image,image_bytes
            picture=load_image(logo)
            story.insert(0,Image(io.BytesIO(image_bytes(picture)),width=72,height=72*picture.height/picture.width))
    story += [Spacer(1,16),para('INVOICE '+data.get('number','DRAFT'),sheet['Heading1']),
        para('Date: '+data.get('date',date.today().isoformat()),sheet['BodyText']),
        para('Bill to: '+data.get('customer','Walk-in customer'),sheet['BodyText']),
        para('Contact: '+data.get('phone',''),sheet['BodyText']),Spacer(1,18)]
    rows=[['Description','Qty','Rate (INR)','Tax %','Amount']]
    rows += [[para(i['description'],sheet['BodyText']),i['qty'],i['rate'],i['tax'],i['amount']] for i in totals['items']]
    table=Table(rows,colWidths=[235,45,75,50,100],repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),accent),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f8')]),
        ('LINEBELOW',(0,-1),(-1,-1),.5,accent)]))
    story += [table,Spacer(1,16),para(f"Subtotal: INR {totals['subtotal']} | Tax: INR {totals['tax']}",sheet['BodyText']),para(f"TOTAL: INR {totals['total']}",sheet['Heading1'])]
    if business.get('upi'):
        uri='upi://pay?'+urlencode(dict(pa=business['upi'],pn=heading,am=totals['total'],cu='INR',tn=data.get('number','Invoice')))
        story += [Image(io.BytesIO(qr_bytes(uri)),width=105,height=105),para('Scan to pay via UPI',sheet['BodyText'])]
    if data.get('notes'):
        story += [Spacer(1,10),para(data['notes'],sheet['BodyText'])]
    story += [Spacer(1,20),para(business.get('footer','Thank you for your business.'),sheet['BodyText'])]
    SimpleDocTemplate(stream,pagesize=(595.276,841.89),leftMargin=45,rightMargin=45,topMargin=40,bottomMargin=40).build(story)
    return stream.getvalue(),totals
