from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any

from .constants import (
    BLOCK_FIELD_MAP,
    PY_WEEKDAY_TO_KO,
    SPECIAL_LOCATION_HOMEROOM,
    SPECIAL_LOCATION_MOVE,
    WEEKDAYS,
)


def get_today_weekday_ko() -> str:
    return PY_WEEKDAY_TO_KO.get(datetime.now().weekday(), "월")


def list_classes(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        "SELECT DISTINCT class_no FROM student_master WHERE class_no IS NOT NULL ORDER BY class_no"
    ).fetchall()
    return [int(row[0]) for row in rows]


def list_student_numbers(conn: sqlite3.Connection, class_no: int | None) -> list[int]:
    if class_no is None:
        return []
    rows = conn.execute(
        """
        SELECT DISTINCT student_no
        FROM student_master
        WHERE class_no = ? AND student_no IS NOT NULL
        ORDER BY student_no
        """,
        (class_no,),
    ).fetchall()
    return [int(row[0]) for row in rows]


def get_student_by_id(conn: sqlite3.Connection, student_id: str) -> sqlite3.Row | None:
    normalized = re.sub(r"\D", "", student_id)
    if not normalized:
        return None
    return conn.execute("SELECT * FROM student_master WHERE student_id = ?", (normalized,)).fetchone()


def get_student_by_class_number(
    conn: sqlite3.Connection, class_no: int, student_no: int
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM student_master WHERE class_no = ? AND student_no = ?",
        (class_no, student_no),
    ).fetchone()


def _extract_group_class_no_from_room(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    # 특수 레이아웃(기초자료 시트)에서 교실은 주로 801, 401 같은 형식이다.
    # 이 경우 앞자리(반 번호)를 시간표 패턴 조회용 반 번호로 사용한다.
    if len(digits) >= 3:
        try:
            return int(digits[:-2])
        except ValueError:
            return None
    try:
        return int(digits)
    except ValueError:
        return None


def get_schedule_pattern_class_no(student: sqlite3.Row) -> int | None:
    move_group_class_no = _extract_group_class_no_from_room(student["move_classroom"])
    if move_group_class_no is not None:
        return move_group_class_no
    return int(student["class_no"]) if student["class_no"] is not None else None


def _normalize_block(block_code: str | None) -> str:
    return re.sub(r"\s+", "", str(block_code or ""))


def _block_to_student_field(block_code: str | None) -> str | None:
    key = _normalize_block(block_code)
    if not key:
        return None

    if key.startswith("기초1"):
        return "basic1_classroom"
    if key.startswith("기초2"):
        return "basic2_classroom"
    if key.startswith("탐1") or key.startswith("탐구1"):
        return "inquiry1_classroom"
    if key.startswith("탐2") or key.startswith("탐구2"):
        return "inquiry2_classroom"
    if key.startswith("탐3") or key.startswith("탐구3"):
        return "inquiry3_classroom"
    if key.startswith("교양"):
        return "liberal_classroom"
    if key.startswith("이동반") or key.startswith("선택반"):
        return "move_classroom"

    return BLOCK_FIELD_MAP.get(key)


def _should_follow_destination_for_subject(timetable_row: sqlite3.Row) -> bool:
    block_key = _normalize_block(timetable_row["block_code"])
    if not block_key:
        return False
    if block_key == "공강":
        # 공강은 본반 시간표(과목/교사)를 적용해야 하므로 항상 목적지 기준 반으로 재조회한다.
        return True

    # These blocks depend on the student's assigned class, so subject/teacher must
    # be resolved from the destination class timetable (e.g., 탐1 = 4반).
    if _block_to_student_field(block_key) is not None:
        return True

    # 동아리는 exception_location 으로 이동반을 가리키므로 별도 처리한다.
    if str(timetable_row["exception_location"] or "") == SPECIAL_LOCATION_MOVE:
        return True

    return False


def _homeroom_text(student: sqlite3.Row) -> str:
    if student["homeroom_location"]:
        return str(student["homeroom_location"])
    if student["class_no"]:
        return f"{student['class_no']}반"
    return "본반"


def _resolve_exception_location(token: str, student: sqlite3.Row) -> str:
    if token in (SPECIAL_LOCATION_HOMEROOM, "본반"):
        return _homeroom_text(student)
    if token in (SPECIAL_LOCATION_MOVE, "본인선택반", "본인 선택반"):
        return student["move_classroom"] or "이동반교실 미설정"
    return token


def _format_destination_display(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    # Stored classroom values like 801/401 should be shown as 8반/4반.
    if text.isdigit():
        class_no = _extract_group_class_no_from_room(text)
        if class_no is not None:
            return f"{class_no}반"

    return text


def _resolve_destination_raw(student: sqlite3.Row, timetable_row: sqlite3.Row | None) -> str:
    if timetable_row is None:
        return "시간표 없음"

    # Keep explicit overrides so previously uploaded DB rows still render correctly
    # even if exception rules changed later.
    block_key = _normalize_block(timetable_row["block_code"])
    if block_key == "진로2":
        return student["move_classroom"] or "이동반교실 미설정"
    if block_key == "공강":
        return _homeroom_text(student)

    if timetable_row["exception_location"]:
        return _resolve_exception_location(str(timetable_row["exception_location"]), student)

    mapped_field = _block_to_student_field(timetable_row["block_code"])
    if mapped_field and student[mapped_field]:
        return str(student[mapped_field])

    return _homeroom_text(student)


def resolve_destination(student: sqlite3.Row, timetable_row: sqlite3.Row | None) -> str:
    if timetable_row is not None and _normalize_block(timetable_row["block_code"]) == "동아리":
        return "본인선택반"
    return _format_destination_display(_resolve_destination_raw(student, timetable_row))


def _resolve_subject_row_for_period(
    conn: sqlite3.Connection,
    student: sqlite3.Row,
    weekday: str,
    period: int,
    base_row: sqlite3.Row | None,
) -> tuple[int | None, sqlite3.Row | None]:
    if base_row is None:
        return None, None

    base_class_no = int(base_row["class_no"])
    if not _should_follow_destination_for_subject(base_row):
        return base_class_no, base_row

    raw_destination = _resolve_destination_raw(student, base_row)
    target_class_no = _extract_group_class_no_from_room(raw_destination)

    if target_class_no is None or target_class_no == base_class_no:
        return base_class_no, base_row

    override_row = conn.execute(
        """
        SELECT *
        FROM timetable_pattern
        WHERE class_no = ? AND weekday = ? AND period = ?
        """,
        (target_class_no, weekday, period),
    ).fetchone()
    if override_row is None:
        return base_class_no, base_row

    return target_class_no, override_row


def get_schedule_for_student(
    conn: sqlite3.Connection, student: sqlite3.Row, weekday: str
) -> list[dict[str, Any]]:
    if weekday not in WEEKDAYS:
        raise ValueError("요일은 월~금만 지원합니다.")

    pattern_class_no = get_schedule_pattern_class_no(student)
    if pattern_class_no is None:
        raise ValueError("학생의 시간표 기준 반(이동반/본반)을 결정할 수 없습니다.")

    rows = conn.execute(
        """
        SELECT *
        FROM timetable_pattern
        WHERE class_no = ? AND weekday = ?
        ORDER BY period
        """,
        (pattern_class_no, weekday),
    ).fetchall()
    by_period = {int(row["period"]): row for row in rows}

    schedule: list[dict[str, Any]] = []
    for period in range(1, 8):
        base_row = by_period.get(period)
        effective_class_no, row = _resolve_subject_row_for_period(
            conn=conn,
            student=student,
            weekday=weekday,
            period=period,
            base_row=base_row,
        )
        schedule.append(
            {
                "교시": period,
                "기준반": effective_class_no or pattern_class_no,
                "수업블록": row["block_code"] if row else None,
                "과목명(교사)": row["subject_teacher"] if row else "시간표 없음",
                "이동할 장소📍": resolve_destination(student, base_row),
            }
        )
    return schedule


def summarize_student(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "학번": row["student_id"],
        "이름": row["student_name"],
        "반": row["class_no"],
        "번호": row["student_no"],
        "본반": row["homeroom_location"],
    }
