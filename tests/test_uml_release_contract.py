"""UML release gate: technical integrity and strict manual review boundary."""
from pathlib import Path
import json
import shutil
from tools.verify_uml_release import check

ROOT=Path(__file__).resolve().parents[1]

def test_atlas_technical_contract():
    actual=check(ROOT,require_manual=False,verify_dot=False)
    assert actual['technical_gate']=='PASS',actual
    assert actual['diagrams']>=19

def test_manual_approval_not_synthesized():
    result=check(ROOT,require_manual=True,verify_dot=False)
    manifest=json.loads((ROOT/'docs/architecture/uml/manifest.json').read_text())
    if manifest['status']=='TECHNICAL_DRAFT':
        assert result['manual_gate']=='PENDING'
        assert result['gate']=='FAIL'
        assert 'MANUAL_SOURCE_AND_VISUAL_REVIEW_PENDING' in result['errors']
    else:
        assert result['gate']=='PASS',result

def test_tampering_is_detected(tmp_path):
    # Minimal copied fixtures: all paths redirected into a complete small source tree.
    # A local copy is intentionally used, never mutate the release tree under test.
    manifest=ROOT/'docs/architecture/uml/manifest.json'
    data=json.loads(manifest.read_text())
    bad=dict(data); bad['build_id']='invented-build'
    # Reusable gate can be invoked with a disposable minimal clone of the relevant tree.
    root=tmp_path/'pkg'
    shutil.copytree(ROOT/'docs/architecture/uml',root/'docs/architecture/uml')
    shutil.copy(ROOT/'version.py',root/'version.py')
    shutil.copy(ROOT/'controller_logic.py',root/'controller_logic.py')
    (root/'README.md').write_text('docs/architecture/uml/INDEX.md')
    (root/'docs/INDEX.md').write_text('architecture/uml/INDEX.md')
    (root/'docs/architecture/README.md').write_text('uml/INDEX.md')
    (root/'docs/architecture/ZEC_V17_1_3_As_Built.md').write_text('uml/INDEX.md')
    for d in data['diagrams']:
        for source in d['source_symbols']:
            rel=source.split('::',1)[0]
            p=root/rel
            if not p.is_file():p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test fixture')
    (root/'docs/architecture/uml/manifest.json').write_text(json.dumps(bad))
    result=check(root,require_manual=False,verify_dot=False)
    assert 'BUILD_IDENTITY_MISMATCH' in result['errors']
    # Correct manifest, then mutate an SVG. Independent integrity check must catch it.
    (root/'docs/architecture/uml/manifest.json').write_text(json.dumps(data))
    diagram=data['diagrams'][0]
    (root/'docs/architecture/uml'/diagram['rendered_svg']).write_text('<svg/>')
    result=check(root,require_manual=False,verify_dot=False)
    assert any(x.startswith('HASH_MISMATCH:') for x in result['errors'])
