"""The generic release entrypoints must not point at a previous installer."""
from pathlib import Path
from tools.verify_arch_history import validate
from version import APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID
ROOT=Path(__file__).resolve().parents[1]

def test_release_readme_and_installer_guide_match_current_version():
    readme=(ROOT/'README.md').read_text(encoding='utf-8')
    guide=(ROOT/'README_INSTALLATION.md').read_bytes()
    assert APP_VERSION=='17.1.3'
    assert APP_VERSION_LABEL in readme and APP_BUILD_ID in readme
    assert guide==(ROOT/'README_INSTALLATION_V17_1_3.md').read_bytes()
    assert APP_BUILD_ID.encode() in guide
    assert b'v17_1_3' in guide and b'v17_0_2 --fresh-install' not in guide

def test_release_architecture_documentation_gate():
    result=validate(ROOT)
    assert result['ok'] and result['gate']=='PASS', result
