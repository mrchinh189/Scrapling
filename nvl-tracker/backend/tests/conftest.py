"""Cho phép import `scrapling` từ repo cha khi chạy test trong môi trường dev.

Trong production, `scrapling` được cài qua pip (xem requirements.txt) nên đoạn này
không ảnh hưởng.
"""

import sys
from pathlib import Path

# nvl-tracker/backend/tests -> lên 3 cấp là gốc repo Scrapling
_repo_root = Path(__file__).resolve().parents[3]
if (_repo_root / "scrapling").is_dir():
    sys.path.insert(0, str(_repo_root))
