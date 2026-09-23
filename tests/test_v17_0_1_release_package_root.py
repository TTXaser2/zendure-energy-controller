from pathlib import Path
from zipfile import ZipFile
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_package',ROOT/'tools'/'release_package.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_verify_rejects_rootless_zip(tmp_path):
    z=tmp_path/'bad.zip'
    with ZipFile(z,'w') as f:
        f.writestr('version.py','x')
        f.writestr('tools/install_zendure_controller.sh','x')
    r=mod.verify_zip(z,'17.0.1')
    assert not r['ok']
    assert any(e.startswith('ZIP_ROOT_MISMATCH:') for e in r['errors'])

def test_build_emits_installer_expected_root(tmp_path):
    src=tmp_path/'src'; (src/'tools').mkdir(parents=True)
    (src/'version.py').write_text('x')
    (src/'tools'/'install_zendure_controller.sh').write_text('x')
    out=tmp_path/'release.zip'
    r=mod.build(src,out,'17.0.1')
    assert r['ok']
    with ZipFile(out) as f:
        names=set(f.namelist())
    assert 'zendure_controller_v17_0_1/version.py' in names
    assert 'zendure_controller_v17_0_1/tools/install_zendure_controller.sh' in names
