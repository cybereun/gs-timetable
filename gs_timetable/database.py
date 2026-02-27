from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping

from .constants import DB_PATH


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS student_master (
            student_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            class_no INTEGER,
            student_no INTEGER,
            homeroom_location TEXT,
            move_classroom TEXT,
            basic1_classroom TEXT,
            basic2_classroom TEXT,
            inquiry1_classroom TEXT,
            inquiry2_classroom TEXT,
            inquiry3_classroom TEXT,
            liberal_classroom TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_student_master_class_no_student_no
            ON student_master(class_no, student_no);

        CREATE TABLE IF NOT EXISTS timetable_pattern (
            class_no INTEGER NOT NULL,
            weekday TEXT NOT NULL,
            period INTEGER NOT NULL,
            block_code TEXT NOT NULL,
            subject_name TEXT,
            teacher_name TEXT,
            subject_teacher TEXT NOT NULL,
            exception_location TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (class_no, weekday, period)
        );

        CREATE INDEX IF NOT EXISTS idx_timetable_pattern_lookup
            ON timetable_pattern(class_no, weekday, period);

        CREATE TABLE IF NOT EXISTS app_meta (
            meta_key TEXT PRIMARY KEY,
            meta_value TEXT NOT NULL
        );
        """
    )
    conn.commit()


def replace_student_master(conn: sqlite3.Connection, rows: Iterable[Mapping[str, object]]) -> int:
    rows = list(rows)
    with conn:
        conn.execute("DELETE FROM student_master")
        conn.executemany(
            """
            INSERT INTO student_master (
                student_id, student_name, class_no, student_no, homeroom_location,
                move_classroom, basic1_classroom, basic2_classroom,
                inquiry1_classroom, inquiry2_classroom, inquiry3_classroom, liberal_classroom
            ) VALUES (
                :student_id, :student_name, :class_no, :student_no, :homeroom_location,
                :move_classroom, :basic1_classroom, :basic2_classroom,
                :inquiry1_classroom, :inquiry2_classroom, :inquiry3_classroom, :liberal_classroom
            )
            """,
            rows,
        )
    return len(rows)


def replace_timetable_patterns(conn: sqlite3.Connection, rows: Iterable[Mapping[str, object]]) -> int:
    rows = list(rows)
    with conn:
        conn.execute("DELETE FROM timetable_pattern")
        conn.executemany(
            """
            INSERT INTO timetable_pattern (
                class_no, weekday, period, block_code,
                subject_name, teacher_name, subject_teacher, exception_location
            ) VALUES (
                :class_no, :weekday, :period, :block_code,
                :subject_name, :teacher_name, :subject_teacher, :exception_location
            )
            """,
            rows,
        )
    return len(rows)


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    with conn:
        conn.execute(
            """
            INSERT INTO app_meta(meta_key, meta_value)
            VALUES (?, ?)
            ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
            """,
            (key, value),
        )


def get_stats(conn: sqlite3.Connection) -> dict[str, object]:
    student_count = conn.execute("SELECT COUNT(*) FROM student_master").fetchone()[0]
    timetable_count = conn.execute("SELECT COUNT(*) FROM timetable_pattern").fetchone()[0]
    updated_at_row = conn.execute(
        "SELECT meta_value FROM app_meta WHERE meta_key = 'last_updated_at'"
    ).fetchone()
    return {
        "student_count": student_count,
        "timetable_count": timetable_count,
        "last_updated_at": updated_at_row[0] if updated_at_row else None,
    }


def clear_all_data(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("DELETE FROM student_master")
        conn.execute("DELETE FROM timetable_pattern")
        conn.execute("DELETE FROM app_meta")

