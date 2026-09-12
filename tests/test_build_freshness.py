import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bin/lib'))
from pwa_build import build


def test_stale_check_does_not_write(tmp_path):
    (tmp_path/'sw.template.js').write_text('const cache="__LAB_CACHE__"; const assets=__LAB_ASSETS__;')
    (tmp_path/'index.html').write_text('shell')
    build(tmp_path)
    before = (tmp_path/'sw.js').read_bytes()
    (tmp_path/'new-module.js').write_text('export const value=1;')
    with pytest.raises(ValueError, match='stale service worker'):
        build(tmp_path, check=True)
    assert (tmp_path/'sw.js').read_bytes() == before
    build(tmp_path)
    assert '/new-module.js' in (tmp_path/'sw.js').read_text()
    assert build(tmp_path, check=True) is False


def test_custom_worker_unmanaged(tmp_path):
    (tmp_path/'sw.js').write_text('custom')
    assert build(tmp_path, check=True) is False
    assert (tmp_path/'sw.js').read_text() == 'custom'
