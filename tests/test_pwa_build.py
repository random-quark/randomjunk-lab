from pathlib import Path
import re
import pytest
from pwa_build import build, GENERATED

def assets(root):
    (root/'index.html').write_text('original')
    (root/'app.js').write_text('one')
    (root/'sw.template.js').write_text("const CACHE='__LAB_CACHE__'; const ASSETS=__LAB_ASSETS__;")

def test_repeatable_hash_and_changed_assets(tmp_path):
    assets(tmp_path)
    assert build(tmp_path)
    original=(tmp_path/'sw.js').read_text()
    assert original.startswith(GENERATED)
    assert not build(tmp_path)
    assert '__LAB_CACHE__' in (tmp_path/'sw.template.js').read_text()
    (tmp_path/'app.js').write_text('two')
    assert build(tmp_path)
    assert original != (tmp_path/'sw.js').read_text()
    (tmp_path/'new.css').write_text('body{}')
    build(tmp_path)
    assert '/new.css' in (tmp_path/'sw.js').read_text()
    assert '/sw.template.js' not in (tmp_path/'sw.js').read_text()
    (tmp_path/'new.css').unlink()
    build(tmp_path)
    assert '/new.css' not in (tmp_path/'sw.js').read_text()

def test_custom_worker_not_overwritten(tmp_path):
    (tmp_path/'sw.js').write_text('custom')
    assert not build(tmp_path)
    assets(tmp_path)
    with pytest.raises(ValueError, match='custom'):
        build(tmp_path)
    assert (tmp_path/'sw.js').read_text()=='custom'

def test_links_rejected_without_overwriting(tmp_path):
    assets(tmp_path);build(tmp_path)
    original=(tmp_path/'sw.js').read_bytes()
    (tmp_path/'linked').symlink_to('/etc/passwd')
    with pytest.raises(OSError): build(tmp_path)
    assert (tmp_path/'sw.js').read_bytes()==original

def test_template_missing_marker_fails(tmp_path):
    assets(tmp_path);(tmp_path/'sw.template.js').write_text('custom')
    with pytest.raises(ValueError, match='retain'): build(tmp_path)

def test_asset_urls_escape_reserved_characters(tmp_path):
    assets(tmp_path)
    (tmp_path/'a #?.js').write_text('one')
    build(tmp_path)
    assert '/a%20%23%3F.js' in (tmp_path/'sw.js').read_text()
