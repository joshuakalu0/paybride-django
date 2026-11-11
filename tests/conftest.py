from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def clear_paybridge_cache():
    from paybridge_django.conf import clear_paybridge_settings_cache

    clear_paybridge_settings_cache()
    yield
    clear_paybridge_settings_cache()
