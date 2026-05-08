"""
Default Streamlit entrypoint (e.g. Streamlit Community Cloud expects `streamlit_app.py`).

Implementation lives in `streamlit_app/app.py` to keep a clear package layout; this file
only boots that script so the repo root filename matches Cloud defaults.
"""

from __future__ import annotations

import runpy
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_APP = _ROOT / "streamlit_app" / "app.py"

if not _APP.is_file():
    raise FileNotFoundError(f"Missing Streamlit UI at {_APP}")

runpy.run_path(str(_APP), run_name="__main__")
