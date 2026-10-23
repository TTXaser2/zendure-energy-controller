#!/usr/bin/env python3
"""Fail-closed, release-bound UML atlas gate (technical + documented expert review)."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

INDEX_LINK = re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')
HTML_LINK = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
HEX_SHA = re.compile(r'^[0-9a-f]{64}$')
REQUIRED = ('README.md','INDEX.md','INDEX.html','CHANGE_IMPACT.md','RELEASE_TRACEABILITY.md','manifest.json')

def check(root:Path, *, require_manual:bool=True, verify_dot:bool=True)->dict:
    root=root.resolve(); u=root/'docs/architecture/uml'; errors=[]; warnings=[]
    def err(s):errors.append(s)
    for f in REQUIRED:
        p=u/f
        if not p.is_file() or not p.stat().st_size:err('MISSING:'+f)
    p=u/'manifest.json'
    if not p.is_file():return {'gate':'FAIL','technical_gate':'FAIL','manual_gate':'NOT_EVALUABLE','errors':errors,'warnings':warnings}
    try:m=json.loads(p.read_text(encoding='utf-8'))
    except (ValueError,UnicodeError) as ex:return {'gate':'FAIL','technical_gate':'FAIL','manual_gate':'NOT_EVALUABLE','errors':errors+['MANIFEST_INVALID:'+str(ex)],'warnings':warnings}
    version=root/'version.py'
    if not version.is_file():err('NO_VERSION_FILE');v=b=''
    else:
        text=version.read_text(encoding='utf-8')
        v=re.search(r'^APP_VERSION_LABEL\s*=\s*["\']([^"\']+)',text,re.M)
        b=re.search(r'^APP_BUILD_ID\s*=\s*["\']([^"\']+)',text,re.M)
        v=v.group(1) if v else '';b=b.group(1) if b else ''
    if not v or m.get('release')!=v:err('RELEASE_IDENTITY_MISMATCH')
    if not b or m.get('build_id')!=b:err('BUILD_IDENTITY_MISMATCH')
    if m.get('schema')!='ZEC_UML_ATLAS_V1':err('SCHEMA_MISMATCH')
    ds=m.get('diagrams')
    if not isinstance(ds,list) or len(ds)<19:err('INVENTORY_MISSING');ds=[]
    ids=[d.get('id') for d in ds if isinstance(d,dict)]
    if len(set(ids))!=len(ids) or not set('%02d'%x for x in range(1,20)).issubset(ids):err('DUPLICATE_OR_MISSING_HISTORIC_IDS')
    if not (u/'CHANGE_IMPACT.md').is_file():impact=''
    else:impact=(u/'CHANGE_IMPACT.md').read_text(encoding='utf-8')
    if not (u/'RELEASE_TRACEABILITY.md').is_file():trace=''
    else:trace=(u/'RELEASE_TRACEABILITY.md').read_text(encoding='utf-8')
    technical_count=0
    for d in ds:
        if not isinstance(d,dict):err('DIAGRAM_INVALID');continue
        idx=str(d.get('id','?'))
        if d.get('status') not in ('UPDATED','NEW','REVIEWED_UNCHANGED','HISTORICAL_ONLY'):err('BAD_CHANGE_STATUS:'+idx)
        if idx not in impact or idx not in trace:err('IMPACT_OR_TRACE_GAP:'+idx)
        sources=d.get('source_symbols')
        if not isinstance(sources,list) or not sources:err('NO_SOURCE_TRACE:'+idx)
        else:
            for s in sources:
                p=root/s.split('::',1)[0]
                if not p.is_file():err('MISSING_TRACED_SOURCE:'+idx+':'+s)
                elif '::' in s and p.suffix=='.py':
                    import ast
                    try:
                        tree=ast.parse(p.read_text(encoding='utf-8'))
                        names={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
                        if s.split('::',1)[1] not in names:err('SOURCE_SYMBOL_MISSING:'+idx+':'+s)
                    except (SyntaxError,UnicodeError):err('SOURCE_PARSE_ERROR:'+idx+':'+s)
        for key in ('source','rendered_svg','rendered_png'):
            rel=d.get(key,''); h=d.get(key+'_sha256','')
            if not isinstance(rel,str) or not rel or Path(rel).is_absolute() or '..' in Path(rel).parts:err('UNSAFE_PATH:'+idx+':'+key);continue
            f=u/rel
            if not f.is_file() or not f.stat().st_size:err('MISSING_FILE:'+idx+':'+rel);continue
            if not isinstance(h,str) or not HEX_SHA.fullmatch(h):err('MISSING_HASH:'+idx+':'+key);continue
            if hashlib.sha256(f.read_bytes()).hexdigest()!=h:err('HASH_MISMATCH:'+idx+':'+key)
            if key=='source':
                if f.suffix!='.dot':err('NON_DOT_CANONICAL:'+idx)
                elif verify_dot:
                    try:
                        q=subprocess.run(['dot','-Tsvg',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=14,check=False)
                        if q.returncode:err('DOT_SYNTAX:'+idx+':'+q.stderr.decode(errors='replace')[:130])
                    except FileNotFoundError:
                        warnings.append('DOT_RENDERER_UNAVAILABLE_BUILD_HOST')
                    except subprocess.TimeoutExpired:err('DOT_TIMEOUT:'+idx)
            elif key=='rendered_svg':
                try:
                    e=ET.parse(f).getroot()
                    if not e.tag.endswith('svg'):err('SVG_ROOT_INVALID:'+idx)
                except ET.ParseError:err('SVG_XML_INVALID:'+idx)
            elif key=='rendered_png':
                x=f.read_bytes()
                if len(x)<24 or x[:8]!=b'\x89PNG\r\n\x1a\n':err('PNG_INVALID:'+idx)
                else:
                    width,height=struct.unpack('>II',x[16:24])
                    if width<32 or height<32:err('PNG_SIZE_INVALID:'+idx)
        if d.get('secondary_plantuml') and d.get('plantuml_validation')!='SECONDARY_UNVERIFIED':
            err('UNSUPPORTED_PLANTUML_VERIFICATION_CLAIM:'+idx)
        technical_count+=1
    for filename,content,rx in [('INDEX.md',(u/'INDEX.md').read_text(encoding='utf-8') if (u/'INDEX.md').exists() else '',INDEX_LINK),('INDEX.html',(u/'INDEX.html').read_text(encoding='utf-8') if (u/'INDEX.html').exists() else '',HTML_LINK)]:
        for loc in rx.findall(content):
            loc=unquote(loc.split('#')[0].strip())
            if not loc or loc.startswith(('http:','https:','mailto:')):err('EXTERNAL_OR_EMPTY_ATLAS_LINK:'+filename+':'+loc);continue
            target=(u/loc).resolve()
            if not target.is_relative_to(u) or not target.is_file():err('BROKEN_ATLAS_LINK:'+filename+':'+loc)
    for outer,needle in [('README.md','docs/architecture/uml/INDEX.md'),('docs/INDEX.md','architecture/uml/INDEX.md'),('docs/architecture/README.md','uml/INDEX.md'),('docs/architecture/ZEC_V17_1_3_As_Built.md','uml/INDEX.md')]:
        f=root/outer
        if not f.is_file() or needle not in f.read_text(encoding='utf-8'):err('OUTER_REFERENCE_MISSING:'+outer)
    ctrl=root/'controller_logic.py'
    if ctrl.is_file() and m.get('source_baseline_controller_sha256') != hashlib.sha256(ctrl.read_bytes()).hexdigest():err('CONTROLLER_SOURCE_MISMATCH')
    manual=all(isinstance(d,dict) and d.get('diagram_semantic_status')=='SOURCE_REVIEW_PASS' for d in ds) and m.get('review_gate')=='MANUAL_SOURCE_REVIEW_PASS' and m.get('status')=='AS_BUILT_RELEASE_APPROVED'
    if not manual and require_manual:err('MANUAL_SOURCE_AND_VISUAL_REVIEW_PENDING')
    tech_errors=[e for e in errors if e!='MANUAL_SOURCE_AND_VISUAL_REVIEW_PENDING']
    return {'gate':'PASS' if not errors else 'FAIL','technical_gate':'PASS' if not tech_errors else 'FAIL','manual_gate':'PASS' if manual else 'PENDING','release':m.get('release'),'diagrams':technical_count,'errors':errors,'warnings':warnings}

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--technical-only',action='store_true');p.add_argument('--no-dot',action='store_true');p.add_argument('--json',action='store_true');a=p.parse_args()
    result=check(Path(a.root),require_manual=not a.technical_only,verify_dot=not a.no_dot)
    print(json.dumps(result,indent=2,ensure_ascii=False) if a.json else 'DOC_UML_RELEASE_GATE='+result['gate']+' '+repr(result['errors']))
    return 0 if result['gate']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
