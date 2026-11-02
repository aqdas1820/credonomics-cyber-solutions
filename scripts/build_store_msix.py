# SPDX-License-Identifier: AGPL-3.0-only
# Copyright © 2026 CredoNomics Investment Solutions.
"""Build an unassociated Store candidate or a separately named local test package."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from string import Template
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]


def build(makeappx,makepri,app,output,work,mode='store',identity_file=None):
    brand=json.loads((ROOT/'brand/brand.json').read_text(encoding='utf-8'))
    identity=json.loads(Path(identity_file or ROOT/'packaging/windows/identity.json').read_text(encoding='utf-8'))
    if identity['version']!=brand['file_version']:
        raise ValueError('Package version must match the authoritative brand file version.')
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    stage=work/mode
    if stage.exists():
        raise ValueError('Use a fresh staging directory; existing packages must not be overwritten.')
    stage.mkdir()
    shutil.copytree(app,stage/'app')
    assets=stage/'Assets';assets.mkdir()
    for path in (ROOT/'store-assets/microsoft/icons').glob('*.png'):
        # Qualified variants are indexed by PRI; omit duplicate unqualified scale-100 files.
        if '.' not in path.stem and path.name!='Wide310x150Logo.png':continue
        shutil.copyfile(path,assets/path.name)
    name=identity['name'];publisher=identity['publisher']
    if mode!='store':
        name+='.'+'LocalTest'
        publisher='CN=CredoNomics Local Packaging Test'
        if mode=='unsigned-test':publisher+=', OID.2.25.311729368913984317654407730594956997722=1'
    values={'IDENTITY_NAME':name,'PUBLISHER_DN':publisher,'PACKAGE_VERSION':identity['version'],'PRODUCT':brand['product_name'],'PUBLISHER_DISPLAY':brand['publisher_name'],
        'DESCRIPTION':brand['product_name']+'. Support: '+brand['support_email']+' | '+brand['support_phone']+' | '+brand['website']}
    template=Template((ROOT/'packaging/windows/AppxManifest.template.xml').read_text(encoding='utf-8'))
    (stage/'AppxManifest.xml').write_text(template.substitute({key:escape(value,{'"':'&quot;'}) for key,value in values.items()}),encoding='utf-8')
    commands=[[str(makepri),'createconfig','/cf',str(work/(mode+'-priconfig.xml')),'/dq','en-US','/o'],
        [str(makepri),'new','/pr',str(stage),'/cf',str(work/(mode+'-priconfig.xml')),'/mn',str(stage/'AppxManifest.xml'),'/of',str(stage/'resources.pri'),'/o'],
        [str(makeappx),'pack','/d',str(stage),'/p',str(output),'/o']]
    logs=[]
    for command in commands:
        result=subprocess.run(command,capture_output=True,text=True,errors='replace')
        logs.append({'tool':Path(command[0]).name,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        (work/(mode+'-validation.json')).write_text(json.dumps(logs,indent=2)+'\n',encoding='utf-8')
        if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    record={'mode':mode,'identity_name':name,'publisher_dn':publisher,'partner_center_associated':False,'schema_pack_validation':True,'sha256':hashlib.sha256(Path(output).read_bytes()).hexdigest(),'package':Path(output).name,'stage':str(stage)}
    (work/(mode+'-result.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in record.items() if key!='stage'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('makeappx','makepri','app','output','work'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--mode',choices=['store','unsigned-test','signed-test'],default='store')
    parser.add_argument('--identity-file')
    args=parser.parse_args();build(args.makeappx,args.makepri,args.app,args.output,args.work,args.mode,args.identity_file)
