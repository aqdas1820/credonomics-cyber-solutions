# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Evaluate package bytes and evidence; never accept a prewritten ready status."""
import argparse
import hashlib
import json
from pathlib import Path
import pefile

QT_LGPL_MODULES={'Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','Qt6Network.dll','Qt6OpenGL.dll','Qt6PrintSupport.dll','Qt6Svg.dll'}
OPENCV_PLUGIN_BUILD_PYD_SHA256='eefedf6ee006a84bbc7d3df5ec66046429b8c95dbfd5f8f8f98c5772b91d6d48'


def evaluate(app,audit,smoke,inventory):
    app=Path(app)
    files=[path for path in app.rglob('*') if path.is_file()]
    names={path.name for path in files}
    binaries=[path for path in files if path.suffix.lower() in {'.dll','.pyd','.exe'}]
    ffmpeg=[path.relative_to(app).as_posix() for path in binaries if any(part in path.name.lower() for part in ('ffmpeg','avcodec','avformat','avutil','swscale'))]
    models=[path.relative_to(app).as_posix() for path in files if path.suffix.lower() in {'.onnx','.pt','.pth','.safetensors','.tflite'}]
    approved_ocr={'eng.traineddata':'7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2','hin.traineddata':'4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825'}
    ocr=[]
    for path in files:
        if path.suffix.lower()=='.traineddata':
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            ocr.append({'path':path.relative_to(app).as_posix(),'sha256':digest,'approved':approved_ocr.get(path.name)==digest})
    modules=audit.get('pyinstaller_modules',[])
    pdf_files=[path.relative_to(app).as_posix() for path in binaries if any(part in path.name.lower() for part in ('mupdf','fitz','artifex'))]
    pdf_modules=[name for name in modules if name.split('.')[0] in {'pymupdf','fitz','pymupdf4llm','pymupdf_layout'}]
    qt={path.name for path in binaries if path.name.startswith('Qt6')}
    unknown_qt=sorted(qt-QT_LGPL_MODULES)
    missing_qt_imports=[]
    for path in binaries:
        pe=pefile.PE(str(path),fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
        for item in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
            dependency=item.dll.decode()
            if dependency.lower().startswith('qt6') and dependency.lower() not in {name.lower() for name in names}:
                missing_qt_imports.append({'file':path.relative_to(app).as_posix(),'missing':dependency})
    gates={}
    cv_path=app/'_internal/cv2/cv2.pyd'
    if cv_path.is_file():
        with cv_path.open('rb') as stream:known_cv=hashlib.file_digest(stream,'sha256').hexdigest()==OPENCV_PLUGIN_BUILD_PYD_SHA256
    else:known_cv=False
    executable=app/'CredoNomics Cyber Solutions.exe'
    if executable.is_file():
        with executable.open('rb') as stream:exe_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    else:exe_sha=None
    execution_ok=bool(exe_sha) and smoke.get('exe_sha256')==exe_sha and smoke.get('success') is True and inventory.get('exe_sha256')==exe_sha
    def gate(name,passed,reason,kind='legal'):
        gates[name]={'status':'PASS' if passed else 'HOLD','reason':reason,'kind':kind}
    gate('PyMuPDF/AGPL',not(pdf_files or pdf_modules),'Retained engine requires an Artifex commercial redistribution agreement and approved artifacts for the proprietary route.' if pdf_files or pdf_modules else 'No Artifex runtime modules/binaries detected.')
    gate('Qt',False,'Allowed LGPL module set verified' if not unknown_qt and not missing_qt_imports else 'Unexpected or unresolved Qt imports: '+str(unknown_qt+missing_qt_imports))
    if not unknown_qt and not missing_qt_imports:
        gates['Qt']['reason']+='; exact vendor binary-to-source/patch correspondence is not attested. Version-matched source kit and replacement instructions supplied; this does not substitute for confirmation.'
    gate('FFmpeg',execution_ok and known_cv and not ffmpeg and smoke.get('recording_backend')=='CV_MJPEG' and smoke.get('recording_decode') is True,'FFmpeg absent; hash-pinned audited OpenCV plugin architecture and exact-executable CV_MJPEG encode/decode evidence required.' if not ffmpeg else 'FFmpeg binaries remain: '+str(ffmpeg))
    marker=app/'_internal/COMMERCIAL-PROFILE.json'
    try:profile=json.loads(marker.read_text(encoding='utf-8'))['profile']
    except (OSError,ValueError,KeyError):profile=None
    gate('AI model',execution_ok and not models and len(ocr)==len(approved_ocr) and all(item['approved'] for item in ocr) and profile=='commercial-clearance' and smoke.get('ai_unavailable_expected') is True and smoke.get('ai_inference') is False,'No unapproved background weights; inference explicitly rejected. Retained OCR data must match approved Apache-2.0 file hashes and execution evidence.' if not models else 'Unapproved model artifacts remain: '+str(models))
    inventory_ok=bool(inventory) and not inventory.get('unmapped_modules') and not inventory.get('shipped_distributions_missing_from_inventory') and not audit.get('unknown_packaged_files') and not audit.get('findings') and not audit.get('developer_paths')
    gate('Third-party notices',False,'Runtime inventory mapped: '+str(inventory_ok)+'. Package/wheel texts retained; exact retained PDF engine native third-party notice/license scope still needs the licensed supplier distribution packet.')
    gate('Source-delivery obligations',False,'Qt source archives are version-matched but supplier patch correspondence is unconfirmed; retained AGPL engine is not approved for the intended proprietary route. No signed source offer is fabricated.')
    gate('Contributor ownership',False,'No signed assignments or corporate chain-of-title records supplied; ASSIGNMENT REQUIRED where material human rights are not vested.')
    gate('Trademark review',False,'No current qualified trademark clearance/registration record supplied.')
    gate('EULA legal review',False,'Only an unsigned draft exists; AGPL remains operative for this source edition.')
    gate('Code signing',False,'No code-signing certificate/signature; deployment policy hold, not an assertion that signing is a copyright requirement.','deployment')
    gate('Physical printer testing',False,'PDF print backend tested; no physical paper-printer job verified.','hardware')
    gate('Physical scanner testing',False,'WIA discovery/no-device handling tested; no physical scanner capture verified.','hardware')
    gate('Executable verification',execution_ok,'Smoke and inventory must identify this exact executable SHA-256.','deployment')
    legal_hold=any(item['status']=='HOLD' for item in gates.values() if item['kind']=='legal')
    return {'external_distribution':'HOLD' if legal_hold else 'PASS','legal_status':'HOLD' if legal_hold else 'PASS','deployment_status':'HOLD' if any(item['status']=='HOLD' for item in gates.values() if item['kind']!='legal') else 'PASS',
        'gates':gates,'actual_qt_modules':sorted(qt),'unexpected_qt_modules':unknown_qt,'missing_qt_imports':missing_qt_imports,'ffmpeg_binaries':ffmpeg,'unapproved_model_artifacts':models,'approved_ocr_artifacts':ocr,'artifex_binaries':pdf_files,'artifex_modules':pdf_modules,'inventory_complete':inventory_ok}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app',required=True)
    parser.add_argument('--audit',required=True)
    parser.add_argument('--smoke',required=True)
    parser.add_argument('--inventory',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--strict',action='store_true')
    args=parser.parse_args()
    load=lambda path:json.loads(Path(path).read_text(encoding='utf-8-sig'))
    report=evaluate(args.app,load(args.audit),load(args.smoke),load(args.inventory))
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for name,value in report['gates'].items():print(name+': '+value['status'])
    print('External distribution:',report['external_distribution'])
    if args.strict and report['external_distribution']=='HOLD':raise SystemExit(2)


if __name__=='__main__':main()
