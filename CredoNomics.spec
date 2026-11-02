# Build from the repository root: pyinstaller --noconfirm CredoNomics.spec
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
from PyInstaller.config import CONF
from pathlib import Path
import os,json
source_marker=Path(SPECPATH)/'COMMERCIAL-PROFILE.json'
default_profile=json.loads(source_marker.read_text(encoding='utf-8'))['profile'] if source_marker.exists() else 'development'
profile=os.environ.get('CREDONOMICS_RELEASE_PROFILE',default_profile)
if profile not in ('development','commercial-clearance','store-submission'):
    raise ValueError('Unknown release profile')
commercial=profile!='development'
store=profile=='store-submission'
marker=Path(CONF['workpath'])/'COMMERCIAL-PROFILE.json'
marker.parent.mkdir(parents=True,exist_ok=True)
marker_text=json.dumps({'profile':profile,'background_model_approved':False})+'\n'
if not marker.exists() or marker.read_text(encoding='utf-8')!=marker_text:
    marker.write_text(marker_text,encoding='utf-8')
datas=[('assets','assets'),('brand','brand'),('tessdata','tessdata'),('third-party-licenses','third-party-licenses'),('docs/legal','docs/legal'),('LICENSE','.'),('THIRD_PARTY_NOTICES.md','.'),(str(marker),'.')]
if not commercial:datas+=[('models','models')]
if store:
    datas=[entry for entry in datas if entry[0]!='docs/legal']
    datas += [('docs/legal/'+name,'docs/legal') for name in ('DATA-HANDLING.md','SOFTWARE-LICENSE.md','BUILD-INFO.md')]
datas+=collect_data_files('pyhanko')+collect_data_files('pyhanko_certvalidator')+collect_data_files('pymupdf')
a=Analysis(['store_main.py' if store else 'main.py'],pathex=['.'],binaries=([] if commercial else collect_dynamic_libs('onnxruntime'))+collect_dynamic_libs('pymupdf'),datas=datas,
    hiddenimports=['pyhanko.keys','pyhanko.sign.validation']+([] if commercial else ['onnxruntime']),
    excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick',
        'PySide6.QtPdf','PySide6.QtPdfWidgets','pymupdf.layout','pymupdf4llm','pymupdf_layout','rembg','numba','scipy','matplotlib','pandas','torch','IPython','notebook','tkinter']+(['onnxruntime','PySide6.QtQml','PySide6.QtQuick'] if commercial else [])+(['cyber.smoke','cyber.ui_review'] if store else []),
    noarchive=False)
if commercial:
    # These plugins bring unused PDF/QML/GPL-only virtual keyboard dependencies.
    blocked={'qt6virtualkeyboard.dll','qtvirtualkeyboardplugin.dll','qt6pdf.dll','qpdf.dll',
        'qt6qml.dll','qt6qmlmeta.dll','qt6qmlmodels.dll','qt6qmlworkerscript.dll','qt6quick.dll','opengl32sw.dll'}
    a.binaries=[entry for entry in a.binaries if Path(entry[0]).name.lower() not in blocked and 'ffmpeg' not in Path(entry[0]).name.lower()]
    a.datas=[entry for entry in a.datas if Path(entry[0]).parts[0].lower()!='models' and '__pycache__' not in Path(entry[0]).parts and Path(entry[0]).suffix.lower() not in {'.onnx','.pt','.pth','.safetensors'}]
if store:
    # python-docx opens templates/default.docx. The expanded source template is
    # unused at runtime; its .rels filename is rejected by MSIX payload validation.
    a.datas=[entry for entry in a.datas if 'docx/templates/default-docx-template/' not in Path(entry[0]).as_posix()]
    a.datas=[entry for entry in a.datas if Path(entry[0]).as_posix()!='assets/version-info.txt' and (Path(entry[0]).parts[0]=='third-party-licenses' or Path(entry[0]).suffix.lower() not in {'.pyi','.h','.hpp','.lib','.pdb','.exp'})]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='CredoNomics Cyber Solutions',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon='assets/app.ico',version='assets/version-info.txt')
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='CredoNomics Cyber Solutions')
