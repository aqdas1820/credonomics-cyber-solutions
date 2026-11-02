# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('commercial_gate',Path(__file__).resolve().parents[1]/'scripts/commercial_gate.py')
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_gate_does_not_trust_a_claimed_ready_status(tmp_path):
    internal=tmp_path/'_internal';internal.mkdir()
    (internal/'COMMERCIAL-PROFILE.json').write_text(json.dumps({'profile':'commercial-clearance'}))
    audit={'external_distribution':'PASS','pyinstaller_modules':['pymupdf','cyber.ui'],'unknown_packaged_files':[]}
    result=gate.evaluate(tmp_path,audit,{'success':True,'recording_backend':'CV_MJPEG','recording_decode':True}, {'unmapped_modules':[]})
    assert result['gates']['PyMuPDF/AGPL']['status']=='HOLD'
    assert result['external_distribution']=='HOLD'
    assert result['gates']['Contributor ownership']['status']=='HOLD'
    assert result['gates']['Source-delivery obligations']['status']=='HOLD'


def test_gate_rejects_unapproved_weights_and_ocr_data(tmp_path):
    internal=tmp_path/'_internal';internal.mkdir()
    (internal/'COMMERCIAL-PROFILE.json').write_text(json.dumps({'profile':'commercial-clearance'}))
    (internal/'unapproved.onnx').write_bytes(b'synthetic unapproved weight')
    (internal/'eng.traineddata').write_bytes(b'synthetic incorrect OCR data')
    result=gate.evaluate(tmp_path,{}, {'ai_unavailable_expected':True,'ai_inference':False}, {})
    assert result['gates']['AI model']['status']=='HOLD'
    assert result['unapproved_model_artifacts']==['_internal/unapproved.onnx']
    assert result['approved_ocr_artifacts'][0]['approved'] is False
