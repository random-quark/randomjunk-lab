import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'bin/lib'))

# These tests must never invoke platform commands. Individual tests replace
# Controller.run or subprocess.run with recording doubles when exercising them.
import pytest
import controller

@pytest.fixture(autouse=True)
def no_platform_commands(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('unexpected external platform command in isolated test')
    monkeypatch.setattr(controller.Controller, 'run', blocked)
