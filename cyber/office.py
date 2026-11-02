# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Local, basic-layout OOXML rendering. No Office automation or network access."""
import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak


def render_ooxml(path):
    path=Path(path)
    stream=io.BytesIO()
    styles=getSampleStyleSheet()
    styles['BodyText'].leading=14
    story=[]
    width,height=595.276,841.89
    left=right=42
    if path.suffix.lower()=='.docx':
        from docx import Document
        from docx.text.paragraph import Paragraph as WordParagraph
        from docx.table import Table as WordTable
        document=Document(path)
        if document.sections:
            section=document.sections[0]
            width,height=section.page_width/12700,section.page_height/12700
            left,right=section.left_margin/12700,section.right_margin/12700
        for item in document.iter_inner_content():
            if isinstance(item,WordParagraph):
                if item.text.strip():
                    style=styles['BodyText']
                    name=item.style.name.lower()
                    if name.startswith('heading'):
                        style=styles['Heading2']
                    elif name=='title':
                        style=styles['Title']
                    rich=''
                    for run in item.runs:
                        text=escape(run.text).replace('\n','<br/>')
                        if run.bold:
                            text='<b>'+text+'</b>'
                        if run.italic:
                            text='<i>'+text+'</i>'
                        rich+=text
                    story.append(Paragraph(rich or escape(item.text),style))
                    story.append(Spacer(1,5))
                for blip in item._p.xpath('.//a:blip'):
                    relationship=blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if relationship and relationship in document.part.related_parts:
                        data=document.part.related_parts[relationship].blob
                        from .images import load_image,image_bytes
                        picture=load_image(data)
                        scale=min((width-left-right)/picture.width,260/picture.height)
                        story.append(Image(io.BytesIO(image_bytes(picture)),width=picture.width*scale,height=picture.height*scale))
            elif isinstance(item,WordTable):
                rows=[[Paragraph(escape(cell.text).replace('\n','<br/>'),styles['BodyText']) for cell in row.cells] for row in item.rows]
                if rows:
                    table=Table(rows,colWidths=[(width-left-right)/len(rows[0])]*len(rows[0]),repeatRows=1)
                    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b7c6d0')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)]))
                    story.extend([table,Spacer(1,10)])
    elif path.suffix.lower()=='.xlsx':
        from openpyxl import load_workbook
        workbook=load_workbook(path,data_only=False)
        for index,sheet in enumerate(workbook):
            if index:
                story.append(PageBreak())
            story.append(Paragraph(escape(sheet.title),styles['Heading1']))
            if sheet.max_row>10000 or sheet.max_column>100:
                raise ValueError('This spreadsheet is too large for basic PDF layout. Use an installed Office renderer.')
            rows=[]
            has_formulas=False
            for row in sheet.iter_rows():
                values=[]
                for cell in row:
                    value='' if cell.value is None else str(cell.value)
                    if cell.data_type=='f':
                        value='Formula: '+value
                        has_formulas=True
                    values.append(value)
                if any(values):
                    rows.append(values)
            if has_formulas:
                story.append(Paragraph('Formula expressions are shown without recalculation. Use an Office renderer for computed results.',styles['BodyText']))
            if rows:
                columns=max(len(row) for row in rows)
                # Wide sheets are split into readable groups rather than silently clipped.
                for offset in range(0,columns,6):
                    section=[[Paragraph(escape(value),styles['BodyText']) for value in row[offset:offset+6]] for row in rows]
                    count=min(6,columns-offset)
                    for row in section:
                        row.extend(['']*(count-len(row)))
                    table=Table(section,colWidths=[(width-left-right)/count]*count,repeatRows=1)
                    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4f2ed')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#c7d2db')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
                    story.extend([table,Spacer(1,15)])
    else:
        raise ValueError('Basic local conversion supports DOCX and XLSX only.')
    if not story:
        story.append(Paragraph('Empty document',styles['BodyText']))
    SimpleDocTemplate(stream,pagesize=(width,height),leftMargin=left,rightMargin=right,topMargin=42,bottomMargin=42).build(story)
    return stream.getvalue()
