from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from gs_timetable import database, etl, service
from gs_timetable.constants import APP_TITLE, WEEKDAYS

TARGET_GRADE = 2
MODE_STUDENT = "학생 화면"
MODE_ADMIN = "관리자"
MODE_OPTIONS = [MODE_STUDENT, MODE_ADMIN]
MOBILE_UA_KEYWORDS = ("android", "iphone", "ipad", "ipod", "mobile", "windows phone", "opera mini")


st.set_page_config(page_title=APP_TITLE, page_icon="📚", layout="wide", initial_sidebar_state="expanded")


@st.cache_resource
def get_db():
    conn = database.get_connection()
    database.initialize_database(conn)
    return conn


def is_mobile_client() -> bool:
    if str(st.query_params.get("is_mobile", "")).lower() == "true":
        return True

    user_agent = ""
    context = getattr(st, "context", None)
    if context is not None:
        headers = getattr(context, "headers", None)
        if headers:
            user_agent = str(headers.get("user-agent", "")).lower()

    return any(keyword in user_agent for keyword in MOBILE_UA_KEYWORDS)


def render_header() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Jua&display=swap');
        :root {
            --gs-bg-1: #fff7fb;
            --gs-bg-2: #f2fbff;
            --gs-paper: rgba(255,255,255,0.75);
            --gs-line: rgba(255,255,255,0.55);
            --gs-text: #213047;
            --gs-sub: #5b6b84;
            --gs-pink: #ff7fb8;
            --gs-pink-2: #ffb4d6;
            --gs-mint: #79e4d3;
            --gs-blue: #73b8ff;
            --gs-ink: #23314b;
            --gs-shadow: 0 18px 40px rgba(45, 67, 105, 0.12);
        }
        .stApp {
            background:
                radial-gradient(circle at 8% 6%, rgba(255, 140, 193, 0.22), transparent 34%),
                radial-gradient(circle at 91% 8%, rgba(120, 231, 214, 0.20), transparent 35%),
                radial-gradient(circle at 88% 82%, rgba(115, 184, 255, 0.18), transparent 32%),
                linear-gradient(180deg, var(--gs-bg-1) 0%, var(--gs-bg-2) 100%);
            color: var(--gs-text);
            font-family: "Gowun Dodum", "Malgun Gothic", sans-serif;
        }
        div.block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }
        [data-testid="stToolbar"] {
            display: none;
        }
        #MainMenu {
            display: none;
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stHeaderActionElements"] {
            display: none;
        }
        section[data-testid="stSidebar"] > div {
            background:
                radial-gradient(circle at 12% 10%, rgba(255,255,255,0.15), transparent 40%),
                linear-gradient(180deg, #233049 0%, #2e3f5d 50%, #2a3853 100%);
            color: #f6fbff;
        }
        section[data-testid="stSidebar"] {
            min-width: 18rem !important;
            max-width: 18rem !important;
        }
        section[data-testid="stSidebar"] > div {
            width: 18rem !important;
        }
        /* Safety net: keep sidebar visible even if Streamlit internally marks collapsed */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            min-width: 18rem !important;
            max-width: 18rem !important;
            transform: translateX(0) !important;
            margin-left: 0 !important;
        }
        section[data-testid="stSidebar"][aria-expanded="false"] > div {
            width: 18rem !important;
        }
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        section[data-testid="stSidebar"] * {
            color: inherit;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] .stCaption {
            color: rgba(246, 251, 255, 0.86) !important;
        }
        section[data-testid="stSidebar"] .stRadio > label,
        section[data-testid="stSidebar"] .stSelectbox > label,
        section[data-testid="stSidebar"] .stTextInput > label {
            color: rgba(255,255,255,0.92) !important;
            font-weight: 700;
        }
        .gs-side-title {
            font-family: "Jua", "Gowun Dodum", sans-serif;
            font-size: 1.1rem;
            letter-spacing: 0.02em;
            margin-bottom: 0.3rem;
        }
        .gs-side-note {
            font-size: 0.82rem;
            opacity: 0.9;
            margin-bottom: 0.35rem;
        }
        .gs-sidebar-card {
            margin-top: 0.5rem;
            border-radius: 18px;
            padding: 14px 14px 10px 14px;
            background: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
            border: 1px solid rgba(255,255,255,0.18);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
        }
        .gs-sidebar-card-title {
            font-family: "Jua", "Gowun Dodum", sans-serif;
            font-size: 0.98rem;
            margin-bottom: 0.45rem;
        }
        .gs-help-foot {
            margin-top: 0.65rem;
            padding-top: 0.65rem;
            border-top: 1px dashed rgba(255,255,255,0.18);
            font-size: 0.78rem;
            color: var(--gs-sub);
        }
        .gs-hero {
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            padding: 20px 22px 18px 22px;
            margin-bottom: 14px;
            background:
                radial-gradient(circle at 88% 15%, rgba(255,255,255,0.65), transparent 34%),
                linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.74));
            border: 1px solid rgba(255,255,255,0.82);
            box-shadow: var(--gs-shadow);
            backdrop-filter: blur(12px);
        }
        .gs-hero::before,
        .gs-hero::after {
            content: "";
            position: absolute;
            border-radius: 999px;
            filter: blur(0.5px);
        }
        .gs-hero::before {
            width: 140px; height: 140px;
            right: -20px; top: -34px;
            background: radial-gradient(circle, rgba(255,127,184,0.34), rgba(255,127,184,0.0) 70%);
        }
        .gs-hero::after {
            width: 120px; height: 120px;
            left: -20px; bottom: -36px;
            background: radial-gradient(circle, rgba(121,228,211,0.30), rgba(121,228,211,0.0) 72%);
        }
        .gs-hero-title {
            font-family: "Jua", "Gowun Dodum", sans-serif;
            font-size: 1.7rem;
            color: var(--gs-ink);
            margin: 0 0 4px 0;
            letter-spacing: 0.01em;
        }
        .gs-hero-sub {
            color: var(--gs-sub);
            font-size: 0.95rem;
            margin-bottom: 10px;
        }
        .gs-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .gs-chip {
            border-radius: 999px;
            padding: 6px 11px;
            font-size: 0.78rem;
            font-weight: 700;
            border: 1px solid rgba(255,255,255,0.75);
            color: #29405f;
            background: rgba(255,255,255,0.76);
        }
        .gs-chip.pink { background: rgba(255, 193, 221, 0.55); }
        .gs-chip.mint { background: rgba(177, 245, 232, 0.55); }
        .gs-chip.blue { background: rgba(186, 222, 255, 0.58); }
        .gs-section-title {
            font-family: "Jua", "Gowun Dodum", sans-serif;
            color: #29395a;
            font-size: 1.18rem;
            margin: 0 0 2px 0;
        }
        .gs-section-sub {
            color: var(--gs-sub);
            margin-bottom: 10px;
            font-size: 0.9rem;
        }
        .gs-subpanel {
            border: 1px solid rgba(255,255,255,0.72);
            background: linear-gradient(180deg, rgba(255,255,255,0.86), rgba(255,255,255,0.68));
            border-radius: 20px;
            padding: 12px 14px;
            margin-bottom: 10px;
            box-shadow: 0 10px 25px rgba(44,67,103,0.08);
            backdrop-filter: blur(10px);
        }
        .gs-card {
            display: grid;
            grid-template-columns: 86px 1fr auto;
            gap: 12px;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.9);
            border-radius: 20px;
            padding: 12px 14px;
            background:
                linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,255,255,0.76));
            margin-bottom: 10px;
            box-shadow: 0 12px 24px rgba(44, 67, 103, 0.08);
        }
        .gs-period-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 14px;
            padding: 10px 8px;
            background: linear-gradient(135deg, rgba(255, 127, 184, 0.16), rgba(115, 184, 255, 0.14));
            border: 1px solid rgba(255,255,255,0.9);
            color: #2d4164;
            font-weight: 800;
            font-size: 0.95rem;
        }
        .gs-card-main {
            min-width: 0;
        }
        .gs-card-title {
            color: var(--gs-text);
            font-weight: 800;
            font-size: 0.98rem;
            margin-bottom: 4px;
            line-height: 1.32;
            word-break: keep-all;
        }
        .gs-meta-row {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }
        .gs-meta {
            color: #576985;
            font-size: 0.82rem;
        }
        .gs-mini-chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 0.72rem;
            font-weight: 700;
            color: #355078;
            background: rgba(115, 184, 255, 0.15);
            border: 1px solid rgba(115, 184, 255, 0.16);
        }
        .gs-dest-pill {
            border-radius: 999px;
            padding: 9px 12px;
            background: linear-gradient(135deg, rgba(121,228,211,0.23), rgba(255,198,226,0.22));
            border: 1px solid rgba(255,255,255,0.9);
            color: #244864;
            font-weight: 800;
            white-space: nowrap;
            font-size: 0.92rem;
        }
        .stMetric {
            background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,255,255,0.75));
            border: 1px solid rgba(255,255,255,0.8);
            border-radius: 18px;
            padding: 10px 12px;
            box-shadow: 0 8px 20px rgba(44,67,103,0.07);
        }
        .stMetric label { font-weight: 700 !important; }
        .stTextInput > div > div,
        .stSelectbox > div > div,
        .stFileUploader {
            border-radius: 16px !important;
        }
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid rgba(169, 186, 214, 0.45) !important;
            color: #213047 !important;
            -webkit-text-fill-color: #213047 !important;
        }
        .stTextInput label, .stSelectbox label {
            color: #213047 !important;
        }
        .stTextInput input::placeholder {
            color: #8c9ba5 !important;
            -webkit-text-fill-color: #8c9ba5 !important;
        }
        .stButton > button {
            border-radius: 14px !important;
            border: 1px solid rgba(255,255,255,0.85) !important;
            font-weight: 800 !important;
            box-shadow: 0 8px 18px rgba(44,67,103,0.08);
            color: #213047 !important;
            -webkit-text-fill-color: #213047 !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #ff8dc3, #8bc4ff) !important;
            color: #1a2536 !important;
            -webkit-text-fill-color: #1a2536 !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg, rgba(255,127,184,0.23), rgba(115,184,255,0.23)) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            box-shadow: 0 8px 18px rgba(11, 18, 34, 0.16) !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: linear-gradient(135deg, #ff7fb8, #73b8ff) !important;
            color: #ffffff !important;
            border-color: rgba(255,255,255,0.30) !important;
            transform: translateY(-1px);
        }
        section[data-testid="stSidebar"] [data-testid="stPopover"] button {
            min-width: 44px !important;
            height: 44px !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #1f2a3d, #334561) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            box-shadow: 0 8px 18px rgba(8, 15, 31, 0.24) !important;
            transition: all 0.18s ease !important;
        }
        section[data-testid="stSidebar"] [data-testid="stPopover"] button:hover,
        section[data-testid="stSidebar"] [data-testid="stPopover"] button:focus-visible,
        section[data-testid="stSidebar"] [data-testid="stPopover"] button:active {
            background: linear-gradient(135deg, #ff4f67, #ff7a7a) !important;
            color: #ffffff !important;
            border-color: rgba(255,255,255,0.34) !important;
            box-shadow: 0 10px 24px rgba(123, 11, 24, 0.35) !important;
            transform: translateY(-1px);
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            gap: 0.4rem;
            flex-wrap: wrap;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            margin: 0 !important;
            background: rgba(255,255,255,0.78);
            border-radius: 999px;
            padding: 7px 12px;
            border: 1px solid rgba(255,255,255,0.9);
            box-shadow: 0 4px 14px rgba(44,67,103,0.05);
            transition: all 0.18s ease;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
            transform: translateY(-1px);
            background: rgba(255,255,255,0.96);
            border-color: rgba(138, 186, 255, 0.55);
            box-shadow: 0 8px 16px rgba(44,67,103,0.10);
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: linear-gradient(135deg, rgba(255, 141, 195, 0.23), rgba(121, 228, 211, 0.24));
            border-color: rgba(117, 174, 255, 0.55);
            box-shadow: 0 8px 18px rgba(84, 133, 210, 0.16);
            color: #243b5c;
            font-weight: 800;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
            display: none;
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            color: rgba(246, 251, 255, 0.95);
            box-shadow: none;
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
            background: linear-gradient(135deg, rgba(255,141,195,0.18), rgba(115,184,255,0.20));
            border-color: rgba(255,255,255,0.28);
            color: #ffffff;
            box-shadow: 0 8px 18px rgba(8, 15, 31, 0.22);
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: linear-gradient(135deg, #ff7fb8, #7cbcff);
            border-color: rgba(255,255,255,0.35);
            color: #ffffff;
            box-shadow: 0 10px 22px rgba(9, 14, 29, 0.28);
        }
        .stDataFrame, [data-testid="stExpander"] {
            border-radius: 16px;
        }
        @media (max-width: 720px) {
            .gs-card {
                grid-template-columns: 62px minmax(0, 1fr) auto;
                gap: 7px;
                align-items: center;
                padding: 9px 10px;
            }
            .gs-dest-pill {
                max-width: 34vw;
                width: auto;
                padding: 7px 9px;
                font-size: 0.8rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .gs-period-pill {
                width: 100%;
                padding: 7px 6px;
                font-size: 0.82rem;
            }
            .gs-card-title {
                font-size: 0.9rem;
                margin-bottom: 2px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .gs-meta-row {
                gap: 4px;
            }
            .gs-mini-chip {
                padding: 2px 6px;
                font-size: 0.68rem;
            }
            .gs-meta {
                font-size: 0.74rem;
            }
            .gs-hero-title {
                font-size: 1.38rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if is_mobile_client():
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] {
                min-width: 0 !important;
                max-width: 0 !important;
                width: 0 !important;
                transform: translateX(-110%) !important;
                margin-left: -18rem !important;
            }
            section[data-testid="stSidebar"] > div {
                width: 0 !important;
                min-width: 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_hero() -> None:
    st.markdown(
        """
        <div id="gs-hero-anchor" class="gs-hero">
          <div class="gs-hero-title">📚 GS-Timetable</div>
          <div class="gs-hero-sub">학생 이동 시간표를 빠르게 찾는 교내 전용 스케줄 앱</div>
          <div class="gs-chip-row">
            <span class="gs-chip pink">2학년 전용</span>
            <span class="gs-chip mint">로컬 SQLite 저장</span>
            <span class="gs-chip blue">CSV/XLSX</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def focus_hero_on_mobile_first_load() -> None:
    if not is_mobile_client():
        return
    if st.session_state.get("mobile_hero_focused_once", False):
        return

    st.session_state.mobile_hero_focused_once = True
    components.html(
        """
        <script>
        function scrollToHero() {
          const hero = window.parent.document.getElementById("gs-hero-anchor");
          if (hero) {
            hero.scrollIntoView({ block: "start", behavior: "auto" });
          }
        }
        scrollToHero();
        setTimeout(scrollToHero, 120);
        </script>
        """,
        height=0,
    )


def _render_help_content() -> None:
    st.markdown("### GS-Timetable 사용 안내")
    st.markdown(
        """
        **사용방법**
        1. `관리자` 화면에서 학급시간표 CSV와 학생정보 엑셀/CSV를 업로드합니다.
        2. `DB 업데이트 실행`을 눌러 최신 학기 데이터로 교체합니다.
        3. `학생 화면`에서 학번 또는 반/번호로 학생을 조회합니다.
        4. 요일을 선택하면 해당 요일의 이동 장소와 과목/교사를 바로 확인할 수 있습니다.

        **장점**
        - 인터넷을 사용하여 빠르게 사용가능
        - 파일만 교체하면 새 학기 데이터 반영 가능
        - 학생별 이동반/탐구/교양 선택을 자동 매핑
        - 로컬 DB 저장 방식이라 관리가 간단하고 안정적
        """
    )
    st.markdown("---")
    st.caption("개발자: 은준욱 (2026.02.26), V1.0.0")


def _render_sidebar_help() -> None:
    with st.sidebar.popover("⚙️", use_container_width=False):
        _render_help_content()


def _render_mobile_menu(conn) -> str:
    if "mobile_mode" not in st.session_state:
        st.session_state.mobile_mode = st.session_state.get("sidebar_mode", MODE_STUDENT)

    st.markdown('<div class="gs-section-sub">메뉴를 선택하면 화면이 즉시 전환됩니다.</div>', unsafe_allow_html=True)

    mode = st.session_state.mobile_mode
    student_col, admin_col, help_col = st.columns([1.35, 1.15, 0.35], gap="small")
    with student_col:
        if st.button(
            "학생화면",
            key="mobile_mode_student_btn",
            use_container_width=True,
            type="primary" if mode == MODE_STUDENT else "secondary",
        ):
            mode = MODE_STUDENT
    with admin_col:
        if st.button(
            MODE_ADMIN,
            key="mobile_mode_admin_btn",
            use_container_width=True,
            type="primary" if mode == MODE_ADMIN else "secondary",
        ):
            mode = MODE_ADMIN
    with help_col:
        with st.popover("⚙️"):
            _render_help_content()

    st.session_state.mobile_mode = mode
    st.session_state.sidebar_mode = mode

    stats = database.get_stats(conn)
    with st.expander("DB 상태 / 사용 안내", expanded=False):
        st.write(f"학생 수: {stats['student_count']}")
        st.write(f"시간표 행 수: {stats['timetable_count']}")
        st.caption(stats["last_updated_at"] or "최근 업데이트 없음")
        st.markdown("---")
        st.markdown("학생 화면: 학번 또는 반/번호로 시간표를 조회합니다.")
        st.markdown("관리자: CSV/XLSX 업로드 후 DB 업데이트를 실행합니다.")
    st.markdown("---")

    return mode


def render_navigation(conn) -> str:
    if "sidebar_mode" not in st.session_state:
        st.session_state.sidebar_mode = MODE_STUDENT

    if is_mobile_client():
        return _render_mobile_menu(conn)

    st.sidebar.markdown('<div class="gs-side-title">메뉴</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="gs-side-note">학생 조회 / 관리자 데이터 업데이트</div>', unsafe_allow_html=True)
    mode = st.sidebar.radio(
        "화면 선택",
        MODE_OPTIONS,
        index=0 if st.session_state.sidebar_mode == MODE_STUDENT else 1,
        key="sidebar_mode",
    )
    st.session_state.sidebar_mode = mode
    _render_sidebar_help()

    stats = database.get_stats(conn)
    st.sidebar.markdown("---")
    last_updated = stats["last_updated_at"] or "최근 업데이트 없음"
    st.sidebar.markdown(
        f"""
        <div class="gs-sidebar-card">
          <div class="gs-sidebar-card-title">DB 상태</div>
          <div>학생 수: <strong>{stats['student_count']}</strong></div>
          <div>시간표 행 수: <strong>{stats['timetable_count']}</strong></div>
          <div style="margin-top:6px; font-size:0.8rem; opacity:0.9;">{last_updated}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return mode


def _render_weekly_print_preview(
    student_info: dict,
    weekly_schedule: dict[str, list[dict]],
    preview_nonce: int = 0,
) -> None:
    day_headers = "".join(f"<th>{escape(day)}요일</th>" for day in WEEKDAYS)

    body_rows: list[str] = []
    for period in range(1, 8):
        cells: list[str] = []
        for day in WEEKDAYS:
            rows = weekly_schedule.get(day, [])
            row = next((item for item in rows if int(item.get("교시", 0)) == period), None)
            if row is None:
                subject = "-"
                destination = "-"
                block = "-"
                basis = "-"
            else:
                subject = str(row.get("과목명(교사)", "-") or "-")
                destination = str(row.get("이동할 장소📍", "-") or "-")
                block = str(row.get("수업블록", "-") or "-")
                basis = str(row.get("기준반", "-") or "-")

            cells.append(
                f"""
                <td>
                  <div class="cell-main">{escape(subject)}</div>
                  <div class="cell-dest">이동: {escape(destination)}</div>
                  <div class="cell-meta">{escape(block)} · 기준반 {escape(basis)}</div>
                </td>
                """
            )
        body_rows.append(f"<tr><th>{period}교시</th>{''.join(cells)}</tr>")

    student_name = escape(str(student_info.get("이름", "")))
    student_id = escape(str(student_info.get("학번", "")))
    class_no = student_info.get("반")
    student_no = student_info.get("번호")
    class_text = "-" if class_no in (None, "") else f"{class_no}반"
    no_text = "-" if student_no in (None, "") else f"{student_no}번"
    homeroom_text = escape(str(student_info.get("본반") or "-"))
    generated_at = escape(datetime.now().strftime("%Y-%m-%d %H:%M"))

    html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="preview-nonce" content="{preview_nonce}" />
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 12px;
          background: #eef3fb;
          font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
          color: #22314a;
        }}
        .toolbar {{
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-bottom: 10px;
        }}
        .print-btn {{
          border: none;
          border-radius: 12px;
          padding: 10px 14px;
          background: linear-gradient(135deg, #ff6d8d, #ff8f73);
          color: #fff;
          font-weight: 700;
          cursor: pointer;
          box-shadow: 0 8px 18px rgba(160, 49, 70, 0.25);
        }}
        .print-btn:hover {{
          filter: brightness(0.98);
        }}
        .close-btn {{
          border: none;
          border-radius: 12px;
          padding: 10px 14px;
          background: linear-gradient(135deg, #2b3950, #425674);
          color: #fff;
          font-weight: 700;
          cursor: pointer;
          box-shadow: 0 8px 18px rgba(31, 45, 72, 0.22);
        }}
        .close-btn:hover {{
          filter: brightness(1.03);
        }}
        .closed-note {{
          display: none;
          margin: 0 auto;
          max-width: 210mm;
          border-radius: 12px;
          padding: 10px 12px;
          background: #f6f9ff;
          border: 1px solid #d8e2f2;
          color: #334a6b;
          font-size: 12px;
        }}
        .page {{
          width: 210mm;
          min-height: 297mm;
          margin: 0 auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 16px 35px rgba(31, 45, 72, 0.18);
          padding: 10mm;
        }}
        .header {{
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 10px;
          margin-bottom: 8px;
        }}
        .title {{
          font-size: 18px;
          font-weight: 800;
          margin-bottom: 4px;
        }}
        .subtitle {{
          font-size: 11px;
          color: #5a6b84;
        }}
        .student-chip {{
          border-radius: 12px;
          border: 1px solid #d9e2f3;
          background: linear-gradient(180deg, #f8fbff, #f1f5fd);
          padding: 8px 10px;
          font-size: 11px;
          text-align: right;
          line-height: 1.5;
          white-space: nowrap;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
          font-size: 10px;
        }}
        thead th {{
          background: linear-gradient(180deg, #dfe8f8, #d4def3);
          color: #1f2f4a;
          border: 1px solid #bfcce4;
          padding: 7px 4px;
          font-weight: 800;
          text-align: center;
        }}
        thead th.corner {{
          width: 62px;
          background: linear-gradient(180deg, #c9d7f1, #bdccea);
        }}
        tbody th {{
          border: 1px solid #bfcce4;
          background: linear-gradient(180deg, #edf2fb, #e7edf9);
          color: #233550;
          font-weight: 800;
          text-align: center;
          padding: 6px 2px;
          width: 62px;
        }}
        tbody td {{
          border: 1px solid #d0daeb;
          vertical-align: top;
          padding: 5px 5px 4px 5px;
          height: 32mm;
          background:
            linear-gradient(180deg, rgba(226,235,250,0.38), rgba(255,255,255,0.0) 42%),
            #ffffff;
        }}
        tbody tr:nth-child(even) td {{
          background:
            linear-gradient(180deg, rgba(243,247,255,0.55), rgba(255,255,255,0.0) 42%),
            #ffffff;
        }}
        .cell-main {{
          font-weight: 700;
          color: #1f2f4a;
          line-height: 1.28;
          margin-bottom: 4px;
          word-break: keep-all;
        }}
        .cell-dest {{
          display: inline-block;
          border-radius: 999px;
          padding: 2px 7px;
          background: #eff8f7;
          border: 1px solid #d6efea;
          color: #225b54;
          font-weight: 700;
          line-height: 1.2;
          margin-bottom: 4px;
        }}
        .cell-meta {{
          color: #6a7890;
          line-height: 1.2;
        }}
        .foot {{
          margin-top: 6px;
          display: flex;
          justify-content: space-between;
          gap: 8px;
          font-size: 10px;
          color: #6d7b92;
        }}
        @page {{
          size: A4 portrait;
          margin: 10mm;
        }}
        @media print {{
          body {{ background: white; padding: 0; }}
          .toolbar {{ display: none !important; }}
          .page {{
            width: auto;
            min-height: auto;
            margin: 0;
            border-radius: 0;
            box-shadow: none;
            padding: 0;
          }}
        }}
      </style>
      <script>
        const DEFAULT_FRAME_HEIGHT = '1280px';

        function restorePreviewFrameHeight() {{
          try {{
            if (window.frameElement) {{
              window.frameElement.style.height = DEFAULT_FRAME_HEIGHT;
            }}
          }} catch (e) {{}}
        }}

        function closePreview() {{
          const page = document.querySelector('.page');
          const toolbar = document.querySelector('.toolbar');
          const note = document.querySelector('.closed-note');
          if (page) page.style.display = 'none';
          if (toolbar) toolbar.style.display = 'none';
          if (note) note.style.display = 'block';
          try {{
            if (window.frameElement) {{
              window.frameElement.style.height = '64px';
            }}
          }} catch (e) {{}}
        }}

        window.addEventListener('load', restorePreviewFrameHeight);
        setTimeout(restorePreviewFrameHeight, 0);
      </script>
    </head>
    <body>
      <div class="toolbar" data-preview-nonce="{preview_nonce}">
        <button class="print-btn" onclick="window.print()">인쇄</button>
        <button class="close-btn" onclick="closePreview()">창닫기</button>
      </div>
      <div class="closed-note">인쇄 미리보기를 닫았습니다. 다시 보려면 상단의 <strong>인쇄미리보기</strong> 버튼을 눌러주세요.</div>
      <div class="page">
        <div class="header">
          <div>
            <div class="title">GS-Timetable 주간 시간표</div>
            <div class="subtitle">월요일~금요일 · 1교시~7교시 · 학생 이동 장소 포함</div>
          </div>
          <div class="student-chip">
            <div><strong>{student_name}</strong> ({student_id})</div>
            <div>{escape(class_text)} / {escape(no_text)}</div>
            <div>본반: {homeroom_text}</div>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th class="corner">교시</th>
              {day_headers}
            </tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
        <div class="foot">
          <div>인쇄 팁: 브라우저 인쇄 옵션에서 배율 `기본` 또는 `맞춤 95~100%` 권장</div>
          <div>생성 시각 {generated_at}</div>
        </div>
      </div>
    </body>
    </html>
    """
    st.markdown(
        '<div class="gs-subpanel"><strong>인쇄 미리보기</strong> 아래 A4 미리보기에서 <strong>인쇄</strong> 버튼을 누르면 바로 인쇄창이 열립니다.</div>',
        unsafe_allow_html=True,
    )
    components.html(html, height=1280, scrolling=True)


def render_admin(conn) -> None:
    if is_mobile_client():
        if not st.session_state.get("admin_authenticated", False):
            st.markdown('<div class="gs-section-title">관리자 인증</div>', unsafe_allow_html=True)
            st.markdown('<div class="gs-section-sub">이 기기(모바일)에서 접근하려면 4자리 비밀번호가 필요합니다.</div>', unsafe_allow_html=True)
            pin = st.text_input("비밀번호", type="password")
            if st.button("확인"):
                if pin == "0114":
                    st.session_state.admin_authenticated = True
                    st.rerun()
                elif pin != "":
                    st.error("비밀번호가 일치하지 않습니다.")
            return

    st.markdown('<div class="gs-section-title">관리자 데이터 업로드</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="gs-section-sub">업로드 시 기존 SQLite 데이터를 덮어씁니다. (2학년 전용)</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="gs-subpanel"><strong>안내</strong> 업로드 가능한 파일 형식과 컬럼 예시는 아래 접기 패널에서 확인하세요.</div>',
        unsafe_allow_html=True,
    )
    with st.expander("지원 컬럼 안내", expanded=False):
        st.markdown(
            """
            - 학생 파일: `학번`, `이름` (권장: `본반`, `이동반교실`, `기초1교실`, `기초2교실`, `탐구1교실`, `탐구2교실`, `탐구3교실`, `교양교실`)
            - 시간표 파일: `반`, `요일`, `교시`, `수업블록`, `과목명/교사` (또는 `과목명`, `교사`), `예외장소`
            """
        )

    col1, col2 = st.columns(2)
    with col1:
        timetable_file = st.file_uploader("1) 학급시간표 CSV", type=["csv"], key="timetable_file")
    with col2:
        student_file = st.file_uploader(
            "2) 학생 정보 파일 (CSV/XLSX/XLS)", type=["csv", "xlsx", "xls"], key="student_file"
        )

    st.info("현재 앱은 2학년 전용으로 설정되어 있습니다. 업로드 시 2학년 데이터만 반영됩니다.")

    action_left, action_right = st.columns([2, 1])
    update_clicked = action_left.button("DB 업데이트 실행", type="primary", use_container_width=True)
    clear_clicked = action_right.button("DB 초기화", use_container_width=True)

    if clear_clicked:
        database.clear_all_data(conn)
        st.success("데이터베이스를 초기화했습니다.")
        st.rerun()

    if not update_clicked:
        return

    if not timetable_file or not student_file:
        st.error("시간표 파일과 학생 파일을 모두 업로드해 주세요.")
        return

    try:
        student_result = etl.parse_student_master_file(student_file, default_grade=TARGET_GRADE)
        timetable_result = etl.parse_timetable_pattern_file(
            timetable_file, target_grade=TARGET_GRADE
        )

        database.replace_student_master(conn, student_result.rows)
        database.replace_timetable_patterns(conn, timetable_result.rows)
        database.set_meta(conn, "last_updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        stats = database.get_stats(conn)
        st.success("데이터베이스가 성공적으로 업데이트되었습니다.")
        s1, s2 = st.columns(2)
        s1.metric("전체 학생 수", stats["student_count"])
        s2.metric("시간표 로드 개수", stats["timetable_count"])

        warnings = student_result.warnings + timetable_result.warnings
        if warnings:
            with st.expander(f"검증/제외 로그 ({len(warnings)}건)"):
                for line in warnings:
                    st.write(f"- {line}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"업로드 처리 실패: {exc}")
        st.exception(exc)


def _student_picker(conn):
    if "selected_student_id" not in st.session_state:
        st.session_state.selected_student_id = ""
    if "student_id_search_input" not in st.session_state:
        st.session_state.student_id_search_input = st.session_state.selected_student_id
    pending_search_input = st.session_state.pop("_pending_student_id_search_input", None)
    if pending_search_input is not None:
        st.session_state.student_id_search_input = pending_search_input
    if "_search_by_id_enter" not in st.session_state:
        st.session_state._search_by_id_enter = False

    def _mark_search_by_id_enter():
        st.session_state._search_by_id_enter = True

    class_options = service.list_classes(conn)
    if is_mobile_client():
        student_id_input = st.text_input(
            "학번 입력",
            placeholder="예: 20115",
            key="student_id_search_input",
            on_change=_mark_search_by_id_enter,
        )
        search_by_id_clicked = st.button("학번으로 조회", type="primary", use_container_width=True)

        class_col, no_col = st.columns(2)
        with class_col:
            class_no = st.selectbox(
                "반",
                options=class_options if class_options else [None],
                format_func=lambda value: "-" if value is None else f"{value}반",
                key="search_class_no",
            )
        with no_col:
            student_numbers = service.list_student_numbers(conn, class_no)
            student_no = st.selectbox(
                "번호",
                options=student_numbers if student_numbers else [None],
                format_func=lambda value: "-" if value is None else f"{value}번",
                key="search_student_no",
            )
        search_by_class_clicked = st.button("반/번호로 조회", type="primary", use_container_width=True)
    else:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            student_id_input = st.text_input(
                "학번 입력",
                placeholder="예: 20115",
                key="student_id_search_input",
                on_change=_mark_search_by_id_enter,
            )
        with col2:
            class_no = st.selectbox(
                "반",
                options=class_options if class_options else [None],
                format_func=lambda value: "-" if value is None else f"{value}반",
                key="search_class_no",
            )
        with col3:
            student_numbers = service.list_student_numbers(conn, class_no)
            student_no = st.selectbox(
                "번호",
                options=student_numbers if student_numbers else [None],
                format_func=lambda value: "-" if value is None else f"{value}번",
                key="search_student_no",
            )

        search_col1, search_col2 = st.columns(2)
        with search_col1:
            search_by_id_clicked = st.button("학번으로 조회", type="primary", use_container_width=True)
        with search_col2:
            search_by_class_clicked = st.button("반/번호로 조회", type="primary", use_container_width=True)

    if st.session_state._search_by_id_enter:
        search_by_id_clicked = True
        st.session_state._search_by_id_enter = False

    student = None
    if search_by_id_clicked:
        if student_id_input.strip():
            student = service.get_student_by_id(conn, student_id_input)
        else:
            st.warning("학번을 입력한 뒤 조회해 주세요.")
            return None

        if not student:
            st.error("학생을 찾지 못했습니다. 업로드 데이터를 확인해 주세요.")
            return None
        st.session_state.selected_student_id = str(student["student_id"])
        st.session_state._pending_student_id_search_input = str(student["student_id"])
        st.rerun()

    if search_by_class_clicked:
        if class_no is not None and student_no is not None:
            student = service.get_student_by_class_number(conn, int(class_no), int(student_no))
        else:
            st.warning("반/번호를 선택한 뒤 조회해 주세요.")
            return None

        if not student:
            st.error("학생을 찾지 못했습니다. 업로드 데이터를 확인해 주세요.")
            return None
        st.session_state.selected_student_id = str(student["student_id"])
        st.session_state._pending_student_id_search_input = str(student["student_id"])
        st.rerun()

    if st.session_state.selected_student_id:
        return service.get_student_by_id(conn, st.session_state.selected_student_id)

    return None


def render_student(conn) -> None:
    st.markdown('<div class="gs-section-title">학생 이동 시간표 조회</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="gs-section-sub">학번 또는 반/번호로 검색하고, 오늘 요일이 기본 선택됩니다.</div>',
        unsafe_allow_html=True,
    )

    stats = database.get_stats(conn)
    if stats["student_count"] == 0 or stats["timetable_count"] == 0:
        st.info("관리자 화면에서 학생 파일과 시간표 파일을 먼저 업로드해 주세요.")
        return

    st.markdown(
        '<div class="gs-subpanel"><strong>검색</strong> 학번 조회 또는 반/번호 조회 버튼을 각각 눌러 검색할 수 있습니다.</div>',
        unsafe_allow_html=True,
    )
    student = _student_picker(conn)
    if not student:
        return

    info = service.summarize_student(student)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("학번", info["학번"])
    m2.metric("이름", info["이름"])
    m3.metric("반", "-" if info["반"] is None else f"{info['반']}반")
    m4.metric("번호", "-" if info["번호"] is None else f"{info['번호']}번")
    if info["본반"]:
        st.caption(f"본반: {info['본반']}")

    today = service.get_today_weekday_ko()
    default_idx = WEEKDAYS.index(today) if today in WEEKDAYS else 0
    weekday_col, print_col = st.columns([6, 2])
    with weekday_col:
        weekday = st.radio("요일 선택", WEEKDAYS, index=default_idx, horizontal=True)
    with print_col:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        preview_clicked = st.button(
            "인쇄미리보기",
            key=f"print_preview_btn_{info['학번']}",
            type="primary",
            use_container_width=True,
        )
    if preview_clicked:
        st.session_state.print_preview_student_id = str(info["학번"])
        st.session_state.print_preview_nonce = int(st.session_state.get("print_preview_nonce", 0)) + 1

    st.markdown(f"### {weekday}요일 시간표")
    schedule = service.get_schedule_for_student(conn, student, weekday)
    for row in schedule:
        period_text = f"{row['교시']}교시"
        subject_text = escape(str(row["과목명(교사)"]))
        block_text = escape(str(row["수업블록"] or "-"))
        destination_text = escape(str(row["이동할 장소📍"]))
        basis_text = escape(str(row.get("기준반", "-")))
        st.markdown(
            f"""
            <div class="gs-card">
              <div class="gs-period-pill">{period_text}</div>
              <div class="gs-card-main">
                <div class="gs-card-title">{subject_text}</div>
                <div class="gs-meta-row">
                  <span class="gs-mini-chip">블록 {block_text}</span>
                  <span class="gs-meta">기준반 {basis_text}</span>
                </div>
              </div>
              <div class="gs-dest-pill">📍 {destination_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("표 형태로 보기"):
        st.dataframe(schedule, use_container_width=True, hide_index=True)

    if st.session_state.get("print_preview_student_id") == str(info["학번"]):
        weekly_schedule = {day: service.get_schedule_for_student(conn, student, day) for day in WEEKDAYS}
        _render_weekly_print_preview(
            info,
            weekly_schedule,
            preview_nonce=int(st.session_state.get("print_preview_nonce", 0)),
        )


def main() -> None:
    render_header()
    conn = get_db()
    mode = render_navigation(conn)
    render_hero()
    focus_hero_on_mobile_first_load()
    if mode == MODE_ADMIN:
        render_admin(conn)
    else:
        render_student(conn)


if __name__ == "__main__":
    main()
