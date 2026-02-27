from __future__ import annotations

import sys
from pathlib import Path


def _get_runtime_dir() -> Path:
    # PyInstaller 실행 파일에서는 exe가 있는 폴더에 DB를 저장한다.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_TITLE = "GS-Timetable"
BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = _get_runtime_dir()
DB_PATH = RUNTIME_DIR / "antigravity.db"

WEEKDAYS = ["월", "화", "수", "목", "금"]
PY_WEEKDAY_TO_KO = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

SPECIAL_LOCATION_MOVE = "__MOVE_CLASSROOM__"
SPECIAL_LOCATION_HOMEROOM = "__HOMEROOM__"

UPLOAD_EXCEPTION_RULES = {
    "동아리": SPECIAL_LOCATION_MOVE,
    "진로2": SPECIAL_LOCATION_MOVE,
    "스포츠": "체육관",
    "공강": SPECIAL_LOCATION_HOMEROOM,
}

BLOCK_FIELD_MAP = {
    "기초1": "basic1_classroom",
    "기초2": "basic2_classroom",
    "탐1": "inquiry1_classroom",
    "탐구1": "inquiry1_classroom",
    "탐2": "inquiry2_classroom",
    "탐구2": "inquiry2_classroom",
    "탐3": "inquiry3_classroom",
    "탐구3": "inquiry3_classroom",
    "교양": "liberal_classroom",
    "이동반": "move_classroom",
    "선택반": "move_classroom",
}
