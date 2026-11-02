# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import base64
import io
import json
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image,ImageDraw,ImageFont
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,ed25519
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

from cyber.documents import signature_report,ocr_pdf,as_pdf
from cyber.images import remove_background,model_path,image_bytes
from cyber.licensing import canonical,verify_license


def test_real_signed_pdf_integrity_and_trust(sample):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'CredoNomics test root')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=True,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),critical=True)
        .sign(key,hashes.SHA256()))
    pfx=sample['directory']/'test.pfx'
    root=sample['directory']/'root.pem'
    root.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    pfx.write_bytes(pkcs12.serialize_key_and_certificates(b'test',key,cert,None,serialization.NoEncryption()))
    signer=signers.SimpleSigner.load_pkcs12(str(pfx))
    writer=IncrementalPdfFileWriter(io.BytesIO(sample['pdf'].read_bytes()))
    signed=signers.sign_pdf(writer,signers.PdfSignatureMetadata(field_name='TestSignature'),signer=signer)
    path=sample['directory']/'signed.pdf'
    path.write_bytes(signed.getvalue())
    report=signature_report(path,str(root))
    assert len(report['signatures'])==1
    result=report['signatures'][0]
    assert result.get('intact') is True,result
    assert result.get('cryptographically_valid') is True,result
    assert result.get('trusted') is True,result
    untrusted=signature_report(path)
    assert untrusted['signatures'][0]['trusted'] is False


def test_own_licence_rejects_other_pc_and_tampering(tmp_path):
    key=ed25519.Ed25519PrivateKey.generate()
    public=tmp_path/'public.pem'
    public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
    payload={'product':'CredoNomics Cyber Solutions','machine_id':'TEST-PC','customer':'Test'}
    envelope={'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode()}
    assert verify_license(envelope,public,'TEST-PC')['customer']=='Test'
    with pytest.raises(ValueError,match='another PC'):
        verify_license(envelope,public,'OTHER-PC')
    envelope['payload']['customer']='Tampered'
    with pytest.raises(Exception):
        verify_license(envelope,public,'TEST-PC')


def test_bundled_ocr_recognises_text():
    image=Image.new('RGB',(1200,400),'white')
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',72) if Path('C:/Windows/Fonts/arial.ttf').exists() else ImageFont.load_default(size=72)
    ImageDraw.Draw(image).text((50,100),'CREDONOMICS TEST',font=font,fill='black')
    source=fitz.open()
    page=source.new_page(width=600,height=200)
    page.insert_image(page.rect,stream=image_bytes(image))
    data=source.tobytes()
    source.close()
    result=ocr_pdf(data)
    with fitz.open(stream=result,filetype='pdf') as doc:
        assert 'CREDONOMICS' in doc[0].get_text().upper()


def test_actual_local_ai_model(sample):
    from cyber.distribution import is_commercial_build
    if is_commercial_build():
        assert not model_path().exists(),'Unapproved weights must not enter the commercial source/package.'
        with pytest.raises(ValueError,match='unavailable in this candidate'):
            remove_background(sample['photo'],'transparent')
        return
    assert model_path().exists(),'The development profile requires the local test model.'
    result=remove_background(sample['photo'],'transparent')
    assert result.mode=='RGBA'
    assert result.size==(700,900)
    extrema=result.getchannel('A').getextrema()
    assert extrema[0]<extrema[1]
