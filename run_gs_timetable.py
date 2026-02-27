from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _resource_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def _working_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _setup_file_log() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None

    log_path = _working_dir() / "gs-timetable-launch.log"
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file

    def _excepthook(exc_type, exc, tb):
        print("=== Unhandled Exception ===")
        traceback.print_exception(exc_type, exc, tb)

    sys.excepthook = _excepthook
    return log_path


def main() -> None:
    log_path = _setup_file_log()
    # Import를 main 내부로 내려 초기화 실패 시 로그 파일에 기록되게 한다.
    import gs_timetable  # noqa: F401
    import streamlit.config as st_config
    from streamlit.web import bootstrap

    app_path = _resource_base_dir() / "antigravity.py"
    os.chdir(_working_dir())

    if log_path:
        print("=== GS-Timetable Launcher Start ===")
        print("cwd:", os.getcwd())
        print("app_path:", app_path)
        print("resource_base:", _resource_base_dir())
        print("sys.executable:", sys.executable)

    if not app_path.exists():
        raise FileNotFoundError(f"Streamlit app not found: {app_path}")

    # 기본 포트/주소를 고정해 실행 즉시 접속 가능하게 한다.
    # PyInstaller 환경에서는 Streamlit이 dev mode로 오인될 수 있어 직접 끈다.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    st_config.set_option("global.developmentMode", False, "<gs-launcher>")
    flag_options = {
        "global.developmentMode": False,
        "server.headless": False,
        "browser.gatherUsageStats": False,
        "server.address": "0.0.0.0",
        "server.port": 8501,
    }
    if log_path:
        print("config global.developmentMode:", st_config.get_option("global.developmentMode"))
        print("flag_options:", flag_options)
        print("bootstrap.run starting...")
    bootstrap.run(str(app_path), is_hello=False, args=[], flag_options=flag_options)


if __name__ == "__main__":
    main()
