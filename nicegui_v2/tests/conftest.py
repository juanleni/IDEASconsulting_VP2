import sys
from pathlib import Path

_NICEGUI_V2_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _NICEGUI_V2_DIR.parent
for _path in (_NICEGUI_V2_DIR, _REPO_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
