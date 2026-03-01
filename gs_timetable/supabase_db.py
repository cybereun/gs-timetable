from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import requests

from . import database

DEFAULT_SUPABASE_URL = "https://bcwubnsoyqsftuetbnit.supabase.co"
TABLE_STUDENT = "student_master"
TABLE_TIMETABLE = "timetable_pattern"
TABLE_META = "app_meta"


@dataclass(frozen=True)
class SupabaseSettings:
    base_url: str
    api_key: str
    schema: str = "public"


def _read_secret(secrets: Mapping[str, Any] | None, key: str) -> str | None:
    if not secrets:
        return None
    value = secrets.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_settings(secrets: Mapping[str, Any] | None = None) -> SupabaseSettings | None:
    base_url = (os.getenv("SUPABASE_URL") or _read_secret(secrets, "SUPABASE_URL") or "").strip()
    api_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or _read_secret(secrets, "SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or _read_secret(secrets, "SUPABASE_KEY")
        or ""
    ).strip()
    schema = (os.getenv("SUPABASE_DB_SCHEMA") or _read_secret(secrets, "SUPABASE_DB_SCHEMA") or "public").strip()

    if not base_url and not api_key:
        return None

    if not base_url:
        base_url = DEFAULT_SUPABASE_URL
    if not api_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) is required.")

    return SupabaseSettings(base_url=base_url.rstrip("/"), api_key=api_key, schema=schema or "public")


def _resolve_required_settings(secrets: Mapping[str, Any] | None = None) -> SupabaseSettings:
    settings = _resolve_settings(secrets=secrets)
    if settings is None:
        raise RuntimeError(
            "Supabase DB settings are not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return settings


def _headers(settings: SupabaseSettings, *, json_body: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "apikey": settings.api_key,
        "Accept-Profile": settings.schema,
        "Content-Profile": settings.schema,
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _table_url(settings: SupabaseSettings, table_name: str) -> str:
    return f"{settings.base_url}/rest/v1/{table_name}"


def _chunks(rows: Sequence[Mapping[str, Any]], chunk_size: int = 500) -> list[Sequence[Mapping[str, Any]]]:
    return [rows[i : i + chunk_size] for i in range(0, len(rows), chunk_size)]


def _delete_all_rows(
    session: requests.Session,
    *,
    settings: SupabaseSettings,
    table_name: str,
    not_null_filter_column: str,
) -> None:
    resp = session.delete(
        _table_url(settings, table_name),
        headers=_headers(settings),
        params={not_null_filter_column: "not.is.null"},
        timeout=40,
    )
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"Failed to clear '{table_name}': {resp.status_code} {resp.text}")


def _insert_rows(
    session: requests.Session,
    *,
    settings: SupabaseSettings,
    table_name: str,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    if not rows:
        return
    for chunk in _chunks(rows, chunk_size=500):
        resp = session.post(
            _table_url(settings, table_name),
            headers={**_headers(settings, json_body=True), "Prefer": "return=minimal"},
            json=list(chunk),
            timeout=60,
        )
        if resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"Failed to insert into '{table_name}': {resp.status_code} {resp.text}")


def _fetch_all_rows(
    session: requests.Session,
    *,
    settings: SupabaseSettings,
    table_name: str,
) -> list[dict[str, Any]]:
    resp = session.get(
        _table_url(settings, table_name),
        headers=_headers(settings),
        params={"select": "*"},
        timeout=40,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch '{table_name}': {resp.status_code} {resp.text}")

    payload = resp.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected response for '{table_name}'.")
    return [row for row in payload if isinstance(row, dict)]


def replace_all_data(
    *,
    student_rows: Sequence[Mapping[str, Any]],
    timetable_rows: Sequence[Mapping[str, Any]],
    last_updated_at: str,
    secrets: Mapping[str, Any] | None = None,
) -> None:
    settings = _resolve_required_settings(secrets=secrets)

    with requests.Session() as session:
        _delete_all_rows(
            session,
            settings=settings,
            table_name=TABLE_STUDENT,
            not_null_filter_column="student_id",
        )
        _delete_all_rows(
            session,
            settings=settings,
            table_name=TABLE_TIMETABLE,
            not_null_filter_column="class_no",
        )
        _delete_all_rows(
            session,
            settings=settings,
            table_name=TABLE_META,
            not_null_filter_column="meta_key",
        )

        _insert_rows(session, settings=settings, table_name=TABLE_STUDENT, rows=student_rows)
        _insert_rows(session, settings=settings, table_name=TABLE_TIMETABLE, rows=timetable_rows)
        _insert_rows(
            session,
            settings=settings,
            table_name=TABLE_META,
            rows=[{"meta_key": "last_updated_at", "meta_value": last_updated_at}],
        )


def clear_all_data(*, secrets: Mapping[str, Any] | None = None) -> None:
    settings = _resolve_required_settings(secrets=secrets)
    with requests.Session() as session:
        _delete_all_rows(
            session,
            settings=settings,
            table_name=TABLE_STUDENT,
            not_null_filter_column="student_id",
        )
        _delete_all_rows(
            session,
            settings=settings,
            table_name=TABLE_TIMETABLE,
            not_null_filter_column="class_no",
        )
        _delete_all_rows(
            session,
            settings=settings,
            table_name=TABLE_META,
            not_null_filter_column="meta_key",
        )


def sync_sqlite_from_supabase(
    conn,
    *,
    secrets: Mapping[str, Any] | None = None,
) -> bool:
    settings = _resolve_settings(secrets=secrets)
    if settings is None:
        return False

    with requests.Session() as session:
        student_rows = _fetch_all_rows(session, settings=settings, table_name=TABLE_STUDENT)
        timetable_rows = _fetch_all_rows(session, settings=settings, table_name=TABLE_TIMETABLE)
        meta_rows = _fetch_all_rows(session, settings=settings, table_name=TABLE_META)

    database.clear_all_data(conn)

    if student_rows:
        database.replace_student_master(conn, student_rows)
    if timetable_rows:
        database.replace_timetable_patterns(conn, timetable_rows)
    for row in meta_rows:
        key = str(row.get("meta_key") or "").strip()
        if not key:
            continue
        value = str(row.get("meta_value") or "")
        database.set_meta(conn, key, value)

    return bool(student_rows or timetable_rows or meta_rows)
