# GS-Timetable (monetable)

로컬 SQLite + Streamlit 기반 학생 이동 시간표 앱 MVP입니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run antigravity.py
```

## 기능

- 관리자: 학생 정보(엑셀/CSV), 학급시간표(CSV) 업로드 후 DB 갱신
- 학생: 학번 또는 `[반]-[번호]`로 검색 후 요일별 이동 장소 확인
- 로컬 DB: `antigravity.db` (SQLite)

## 기대 입력 형식 (권장)

### 학생 파일 (CSV/XLSX)
- 필수: `학번`, `이름`
- 권장 컬럼:
  - `본반`
  - `이동반교실`
  - `기초1교실`, `기초2교실`
  - `탐구1교실`, `탐구2교실`, `탐구3교실`
  - `교양교실`

### 시간표 파일 (CSV)
- 권장 컬럼:
  - `반`, `요일`, `교시`, `수업블록`
  - `과목명/교사` (또는 `과목명`, `교사`)
  - `예외장소` (선택)

## 예외 규칙 (업로드 시 자동 적용)

- `동아리` -> `본인 선택반` (`이동반교실`)
- `진로2` -> `본반`
- `스포츠` -> `체육관`
- `공강` -> `본반`

## Supabase DB (persistent data)

This app now syncs parsed data to Supabase Database tables only.
No original CSV/XLSX file is stored.

Required secrets/env:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_KEY`)
- Optional: `SUPABASE_DB_SCHEMA` (default: `public`)

Create tables in Supabase SQL Editor:

```sql
create table if not exists public.student_master (
  student_id text primary key,
  student_name text not null,
  class_no integer,
  student_no integer,
  homeroom_location text,
  move_classroom text,
  basic1_classroom text,
  basic2_classroom text,
  inquiry1_classroom text,
  inquiry2_classroom text,
  inquiry3_classroom text,
  liberal_classroom text,
  updated_at timestamptz default now()
);

create index if not exists idx_student_master_class_no_student_no
  on public.student_master(class_no, student_no);

create table if not exists public.timetable_pattern (
  class_no integer not null,
  weekday text not null,
  period integer not null,
  block_code text not null,
  subject_name text,
  teacher_name text,
  subject_teacher text not null,
  exception_location text,
  updated_at timestamptz default now(),
  primary key (class_no, weekday, period)
);

create index if not exists idx_timetable_pattern_lookup
  on public.timetable_pattern(class_no, weekday, period);

create table if not exists public.app_meta (
  meta_key text primary key,
  meta_value text not null
);
```
