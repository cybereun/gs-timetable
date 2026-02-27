from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .constants import UPLOAD_EXCEPTION_RULES, WEEKDAYS


@dataclass
class ParseResult:
    rows: list[dict[str, Any]]
    warnings: list[str]


def read_tabular_file(uploaded_file: Any) -> pd.DataFrame:
    name = (getattr(uploaded_file, "name", "") or "").lower()
    raw = uploaded_file.getvalue()

    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))

    if name.endswith(".csv"):
        return _read_csv_dataframe_from_bytes(raw)

    raise ValueError("지원하지 않는 파일 형식입니다. CSV/XLSX/XLS만 지원합니다.")


def parse_student_master_file(uploaded_file: Any, default_grade: int = 2) -> ParseResult:
    name = (getattr(uploaded_file, "name", "") or "").lower()
    raw = uploaded_file.getvalue()

    if name.endswith((".xlsx", ".xls")):
        special_result = _try_parse_special_student_excel(raw, default_grade=default_grade)
        if special_result is not None:
            return special_result

    df = read_tabular_file(uploaded_file)
    return parse_student_master(df, default_grade=default_grade)


def parse_timetable_pattern_file(uploaded_file: Any, target_grade: int | None = 2) -> ParseResult:
    raw = uploaded_file.getvalue()
    try:
        df = read_tabular_file(uploaded_file)
        return parse_timetable_pattern(df)
    except Exception as standard_error:
        name = (getattr(uploaded_file, "name", "") or "").lower()
        if not name.endswith(".csv"):
            raise
        try:
            return _parse_sectioned_timetable_csv(raw, target_grade=target_grade)
        except Exception:
            raise standard_error


def _read_csv_dataframe_from_bytes(raw: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949로 저장해 주세요.")


def _decode_csv_text(raw: bytes) -> str:
    for enc in ("cp949", "euc-kr", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 텍스트를 해석할 수 없습니다. CP949 또는 UTF-8로 저장해 주세요.")


def normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_/()\-]+", "", text)
    return text


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def clean_code_text(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    if re.fullmatch(r"-?\d+\.0+", text):
        return str(int(float(text)))
    return text


def to_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = re.findall(r"\d+", text)
    if not digits:
        return None
    return int(digits[-1])


def normalize_weekday(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    compact = text.replace("요일", "").strip()
    if compact in WEEKDAYS:
        return compact

    key = compact.lower()[:3]
    mapping = {"mon": "월", "tue": "화", "wed": "수", "thu": "목", "fri": "금"}
    return mapping.get(key)


def normalize_block_code(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", "", text)


def _pick_column(columns: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        key = normalize_header(alias)
        if key in columns:
            return columns[key]
    return None


def _split_subject_teacher(subject_teacher: str | None) -> tuple[str | None, str | None]:
    if not subject_teacher:
        return None, None
    text = subject_teacher.strip()
    if "/" in text:
        subject, teacher = [part.strip() for part in text.split("/", 1)]
        return subject or None, teacher or None
    if " " in text:
        subject, teacher = text.rsplit(" ", 1)
        return subject.strip() or None, teacher.strip() or None
    return text, None


def _build_subject_teacher(subject_name: str | None, teacher_name: str | None) -> str:
    if subject_name and teacher_name:
        return f"{subject_name} / {teacher_name}"
    return subject_name or teacher_name or "미입력"


def _derive_exception_location(subject_name: str | None, subject_teacher: str) -> str | None:
    haystack = f"{subject_name or ''} {subject_teacher}".replace(" ", "")
    for keyword, location in UPLOAD_EXCEPTION_RULES.items():
        if keyword in haystack:
            return location
    return None


def _parse_student_id(student_id: str | None) -> tuple[int | None, int | None]:
    if not student_id:
        return None, None
    digits = re.sub(r"\D", "", student_id)
    if len(digits) < 4:
        return None, None
    middle = digits[1:-2]
    if not middle:
        return None, None
    return int(middle), int(digits[-2:])


def _parse_class_from_homeroom(homeroom: str | None) -> int | None:
    if not homeroom:
        return None
    if "-" in homeroom:
        parts = re.findall(r"\d+", homeroom)
        if parts:
            return int(parts[-1])
    digits = re.findall(r"\d+", homeroom)
    if digits:
        return int(digits[0])
    return None


def _try_parse_special_student_excel(raw: bytes, default_grade: int) -> ParseResult | None:
    try:
        excel = pd.ExcelFile(io.BytesIO(raw))
    except Exception:
        return None

    # Some users re-save the workbook and sheet order changes.
    # Search every sheet instead of assuming "기초자료" is always the first sheet.
    preferred_sheets: list[str] = []
    other_sheets: list[str] = []
    for sheet_name in excel.sheet_names:
        if "기초자료" in str(sheet_name):
            preferred_sheets.append(sheet_name)
        else:
            other_sheets.append(sheet_name)

    for sheet_name in [*preferred_sheets, *other_sheets]:
        try:
            df = pd.read_excel(excel, sheet_name=sheet_name, header=None)
        except Exception:
            continue

        header_row = _find_special_student_header_row(df)
        if header_row is None:
            continue

        return _parse_special_student_layout(df, header_row=header_row, default_grade=default_grade)

    return None


def _find_special_student_header_row(df: pd.DataFrame) -> int | None:
    max_rows = min(len(df), 40)
    for idx in range(max_rows):
        raw_row = df.iloc[idx, :12].tolist()
        row = [clean_text(v) for v in raw_row]
        if len(row) < 12:
            continue

        left = [normalize_header(v) for v in row[0:8]]
        right = [normalize_header(v) for v in row[9:12]]
        if right != ["반", "번호", "이름"]:
            continue

        expected_left = ["본반", "이동반", "기초1", "기초2", "탐구1", "탐구2", "탐구3", "교양"]
        if left == expected_left:
            return idx

        # Allow minor label variation (e.g., "이동반교실", "탐1")
        if (
            len(left) == 8
            and left[0] == "본반"
            and left[1] in {"이동반", "이동반교실", "선택반", "선택반교실"}
            and left[2].startswith("기초1")
            and left[3].startswith("기초2")
            and left[4] in {"탐1", "탐구1"}
            and left[5] in {"탐2", "탐구2"}
            and left[6] in {"탐3", "탐구3"}
            and left[7].startswith("교양")
        ):
            return idx
    return None


def _parse_special_student_layout(df: pd.DataFrame, header_row: int, default_grade: int) -> ParseResult:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for row_idx in range(header_row + 1, len(df)):
        record = df.iloc[row_idx]
        student_name = clean_text(record.iloc[11]) if len(record) > 11 else None
        class_no = to_int(record.iloc[9]) if len(record) > 9 else None
        student_no = to_int(record.iloc[10]) if len(record) > 10 else None

        if not student_name and class_no is None and student_no is None:
            continue
        if not student_name or class_no is None or student_no is None:
            warnings.append(f"학생 행 {row_idx + 1}: 필수값 누락으로 제외")
            continue

        student_id = f"{default_grade}{class_no:02d}{student_no:02d}"
        if student_id in seen_ids:
            warnings.append(f"중복 학번 제외: {student_id}")
            continue
        seen_ids.add(student_id)

        rows.append(
            {
                "student_id": student_id,
                "student_name": student_name,
                "class_no": class_no,
                "student_no": student_no,
                "homeroom_location": clean_code_text(record.iloc[0]) if len(record) > 0 else None,
                "move_classroom": clean_code_text(record.iloc[1]) if len(record) > 1 else None,
                "basic1_classroom": clean_code_text(record.iloc[2]) if len(record) > 2 else None,
                "basic2_classroom": clean_code_text(record.iloc[3]) if len(record) > 3 else None,
                "inquiry1_classroom": clean_code_text(record.iloc[4]) if len(record) > 4 else None,
                "inquiry2_classroom": clean_code_text(record.iloc[5]) if len(record) > 5 else None,
                "inquiry3_classroom": clean_code_text(record.iloc[6]) if len(record) > 6 else None,
                "liberal_classroom": clean_code_text(record.iloc[7]) if len(record) > 7 else None,
            }
        )

    if not rows:
        raise ValueError("기초자료 시트에서 학생 데이터를 추출하지 못했습니다.")
    return ParseResult(rows=rows, warnings=warnings)


def parse_student_master(df: pd.DataFrame, default_grade: int = 2) -> ParseResult:
    if df.empty:
        raise ValueError("학생 파일이 비어 있습니다.")

    columns = {normalize_header(col): str(col) for col in df.columns}
    picked = {
        "student_id": _pick_column(columns, ["학번", "학생번호", "student_id", "studentid"]),
        "student_name": _pick_column(columns, ["이름", "성명", "학생명", "name"]),
        "homeroom_location": _pick_column(columns, ["본반", "본반교실", "homeroom"]),
        "class_no": _pick_column(columns, ["반", "학급", "class", "class_no"]),
        "student_no": _pick_column(columns, ["번호", "출석번호", "no", "num"]),
        "move_classroom": _pick_column(columns, ["이동반교실", "이동반", "선택반", "선택반교실"]),
        "basic1_classroom": _pick_column(columns, ["기초1교실", "기초1"]),
        "basic2_classroom": _pick_column(columns, ["기초2교실", "기초2"]),
        "inquiry1_classroom": _pick_column(columns, ["탐구1교실", "탐1교실", "탐구1", "탐1"]),
        "inquiry2_classroom": _pick_column(columns, ["탐구2교실", "탐2교실", "탐구2", "탐2"]),
        "inquiry3_classroom": _pick_column(columns, ["탐구3교실", "탐3교실", "탐구3", "탐3"]),
        "liberal_classroom": _pick_column(columns, ["교양교실", "교양"]),
    }

    if not picked["student_name"]:
        raise ValueError("학생 파일에서 `이름` 컬럼을 찾지 못했습니다.")
    if not picked["student_id"] and not (picked["class_no"] and picked["student_no"]):
        raise ValueError("학생 파일에서 `학번` 또는 `반`+`번호` 컬럼을 찾지 못했습니다.")

    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for idx, item in df.iterrows():
        student_name = clean_text(item.get(picked["student_name"])) if picked["student_name"] else None
        if not student_name:
            continue

        student_id = clean_text(item.get(picked["student_id"])) if picked["student_id"] else None
        homeroom_location = (
            clean_code_text(item.get(picked["homeroom_location"])) if picked["homeroom_location"] else None
        )
        class_no = to_int(item.get(picked["class_no"])) if picked["class_no"] else None
        student_no = to_int(item.get(picked["student_no"])) if picked["student_no"] else None

        if student_id and (class_no is None or student_no is None):
            parsed_class, parsed_no = _parse_student_id(student_id)
            class_no = class_no if class_no is not None else parsed_class
            student_no = student_no if student_no is not None else parsed_no

        if class_no is None:
            class_no = _parse_class_from_homeroom(homeroom_location)

        if not student_id and class_no is not None and student_no is not None:
            student_id = f"{default_grade}{class_no:02d}{student_no:02d}"

        if not student_id:
            warnings.append(f"학생 행 {idx + 2}: 학번 생성 실패로 제외")
            continue

        student_id = re.sub(r"\D", "", student_id)
        if not student_id:
            warnings.append(f"학생 행 {idx + 2}: 학번 형식 오류로 제외")
            continue
        if student_id in seen_ids:
            warnings.append(f"중복 학번 제외: {student_id}")
            continue
        seen_ids.add(student_id)

        rows.append(
            {
                "student_id": student_id,
                "student_name": student_name,
                "class_no": class_no,
                "student_no": student_no,
                "homeroom_location": homeroom_location,
                "move_classroom": clean_code_text(item.get(picked["move_classroom"])) if picked["move_classroom"] else None,
                "basic1_classroom": clean_code_text(item.get(picked["basic1_classroom"])) if picked["basic1_classroom"] else None,
                "basic2_classroom": clean_code_text(item.get(picked["basic2_classroom"])) if picked["basic2_classroom"] else None,
                "inquiry1_classroom": clean_code_text(item.get(picked["inquiry1_classroom"])) if picked["inquiry1_classroom"] else None,
                "inquiry2_classroom": clean_code_text(item.get(picked["inquiry2_classroom"])) if picked["inquiry2_classroom"] else None,
                "inquiry3_classroom": clean_code_text(item.get(picked["inquiry3_classroom"])) if picked["inquiry3_classroom"] else None,
                "liberal_classroom": clean_code_text(item.get(picked["liberal_classroom"])) if picked["liberal_classroom"] else None,
            }
        )

    if not rows:
        raise ValueError("학생 파일에서 유효한 학생 데이터를 만들지 못했습니다.")
    return ParseResult(rows=rows, warnings=warnings)


def _infer_block_code_from_subject(subject_name: str | None) -> str:
    subject = normalize_block_code(subject_name) or ""
    if not subject:
        return "이동반"

    if subject.startswith("기1"):
        return "기초1"
    if subject.startswith("기2"):
        return "기초2"
    if subject.startswith("탐1"):
        return "탐1"
    if subject.startswith("탐2"):
        return "탐2"
    if subject.startswith("탐3"):
        return "탐3"
    if subject.startswith("정보") or subject.startswith("철학"):
        return "교양"
    if subject.startswith("동아리"):
        return "동아리"
    if subject.startswith("진로2"):
        return "진로2"
    if subject.startswith("스포츠"):
        return "스포츠"
    if subject.startswith("공강"):
        return "공강"
    return "이동반"


def _parse_sectioned_timetable_csv(raw: bytes, target_grade: int | None = 2) -> ParseResult:
    text = _decode_csv_text(raw)
    reader = csv.reader(io.StringIO(text))
    parsed_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    current_grade: int | None = None
    current_class: int | None = None
    seen: set[tuple[int, str, int]] = set()

    for line_no, row in enumerate(reader, start=1):
        if not row:
            continue

        first = (row[0] or "").strip()
        if not first:
            continue

        if "시간표" in first and "반" in first:
            title_match = re.search(r"(\d+)\s*학년\s*(\d+)\s*반", first)
            if title_match:
                current_grade = int(title_match.group(1))
                current_class = int(title_match.group(2))
            else:
                nums = re.findall(r"\d+", first)
                if len(nums) >= 2:
                    current_grade = int(nums[0])
                    current_class = int(nums[1])
            continue

        if target_grade is not None and current_grade is not None and current_grade != target_grade:
            continue

        if current_class is None:
            continue

        if "교시" not in first or not first[:1].isdigit():
            continue

        period_nums = re.findall(r"\d+", first)
        if not period_nums:
            warnings.append(f"시간표 행 {line_no}: 교시 파싱 실패")
            continue
        period = int(period_nums[0])
        if period < 1 or period > 7:
            continue

        for col_idx, weekday in enumerate(WEEKDAYS, start=1):
            if col_idx >= len(row):
                continue
            cell = clean_text(row[col_idx])
            if not cell:
                continue

            subject_name, teacher_name = _split_subject_teacher(cell)
            subject_teacher = _build_subject_teacher(subject_name, teacher_name)
            block_code = _infer_block_code_from_subject(subject_name or cell)
            exception_location = _derive_exception_location(subject_name, subject_teacher)

            key = (current_class, weekday, period)
            if key in seen:
                warnings.append(f"중복 시간표 키 제외: {current_class}반 {weekday} {period}교시")
                continue
            seen.add(key)

            parsed_rows.append(
                {
                    "class_no": current_class,
                    "weekday": weekday,
                    "period": period,
                    "block_code": block_code,
                    "subject_name": subject_name or cell,
                    "teacher_name": teacher_name,
                    "subject_teacher": subject_teacher,
                    "exception_location": exception_location,
                }
            )

    if not parsed_rows:
        raise ValueError("섹션형 시간표 CSV에서 유효한 시간표를 추출하지 못했습니다.")
    return ParseResult(rows=parsed_rows, warnings=warnings)


def parse_timetable_pattern(df: pd.DataFrame) -> ParseResult:
    if df.empty:
        raise ValueError("시간표 파일이 비어 있습니다.")

    columns = {normalize_header(col): str(col) for col in df.columns}
    picked = {
        "class_no": _pick_column(columns, ["반", "학급", "class", "class_no"]),
        "weekday": _pick_column(columns, ["요일", "day", "weekday"]),
        "period": _pick_column(columns, ["교시", "period"]),
        "block_code": _pick_column(columns, ["수업블록", "블록", "block", "block_code"]),
        "subject_teacher": _pick_column(columns, ["과목명/교사", "과목교사", "subject_teacher"]),
        "subject_name": _pick_column(columns, ["과목명", "과목", "subject"]),
        "teacher_name": _pick_column(columns, ["교사", "담당교사", "선생님", "teacher"]),
        "exception_location": _pick_column(columns, ["예외장소", "exception_location"]),
    }

    missing = [key for key in ("class_no", "weekday", "period", "block_code") if not picked[key]]
    if missing:
        raise ValueError(f"시간표 파일 필수 컬럼 누락: {', '.join(missing)}")
    if not picked["subject_teacher"] and not picked["subject_name"]:
        raise ValueError("시간표 파일에서 `과목명/교사` 또는 `과목명` 컬럼을 찾지 못했습니다.")

    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_keys: set[tuple[int, str, int]] = set()

    for idx, item in df.iterrows():
        class_no = to_int(item.get(picked["class_no"]))
        weekday = normalize_weekday(item.get(picked["weekday"]))
        period = to_int(item.get(picked["period"]))
        block_code = normalize_block_code(item.get(picked["block_code"]))

        if class_no is None or weekday is None or period is None or not block_code:
            warnings.append(f"시간표 행 {idx + 2}: 필수값 누락으로 제외")
            continue

        subject_teacher_raw = (
            clean_text(item.get(picked["subject_teacher"])) if picked["subject_teacher"] else None
        )
        subject_name = clean_text(item.get(picked["subject_name"])) if picked["subject_name"] else None
        teacher_name = clean_text(item.get(picked["teacher_name"])) if picked["teacher_name"] else None

        if subject_teacher_raw and (not subject_name or not teacher_name):
            parsed_subject, parsed_teacher = _split_subject_teacher(subject_teacher_raw)
            subject_name = subject_name or parsed_subject
            teacher_name = teacher_name or parsed_teacher

        subject_teacher = _build_subject_teacher(subject_name, teacher_name)
        explicit_exception = (
            clean_text(item.get(picked["exception_location"])) if picked["exception_location"] else None
        )
        exception_location = explicit_exception or _derive_exception_location(subject_name, subject_teacher)

        key = (class_no, weekday, period)
        if key in seen_keys:
            warnings.append(f"중복 시간표 키 제외: {class_no}반 {weekday} {period}교시")
            continue
        seen_keys.add(key)

        rows.append(
            {
                "class_no": class_no,
                "weekday": weekday,
                "period": period,
                "block_code": block_code,
                "subject_name": subject_name,
                "teacher_name": teacher_name,
                "subject_teacher": subject_teacher,
                "exception_location": exception_location,
            }
        )

    if not rows:
        raise ValueError("시간표 파일에서 유효한 시간표 데이터를 만들지 못했습니다.")
    return ParseResult(rows=rows, warnings=warnings)
