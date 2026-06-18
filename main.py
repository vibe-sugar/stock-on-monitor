"""
StockOnMonitor — 메인 엔트리
모든 데이터 파일은 <실행파일 위치>/data/ 폴더 아래에 생성됩니다.
  data/config.json   — 환경 설정
  data/stocks.json   — 종목 정보
  data/debug.bin     — "1" 이면 로그 활성화, "0" 이면 비활성화
  data/debug.log     — 로그 파일 (debug.bin == "1" 일 때만 생성)
"""

import sys
import os
import subprocess
import importlib


# ── PyQtWebEngine 사전 설치 ─────────────────────────────────────────────────
# QApplication 생성 전에 처리해야 pip 이후 재import 가 정상 동작함
def _ensure_webengine() -> bool:
    """PyQtWebEngine 이 없으면 pip install 후 True 반환, 이미 있으면 False 반환."""
    try:
        import PyQt5.QtWebEngineWidgets  # noqa: F401
        return True   # 이미 설치됨
    except ImportError:
        pass
    try:
        print("[INFO] PyQtWebEngine 설치 중...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "PyQtWebEngine"],
        )
        # 설치 후 sys.path 에 새 패키지가 잡히도록 site-packages 재스캔
        import site
        importlib.invalidate_caches()
        for sp in site.getsitepackages():
            if sp not in sys.path:
                sys.path.insert(0, sp)
        import PyQt5.QtWebEngineWidgets  # noqa: F401  — 설치 확인
        print("[INFO] PyQtWebEngine 설치 완료", flush=True)
        return True
    except Exception as e:
        print(f"[WARN] PyQtWebEngine 설치 실패: {e}", file=sys.stderr, flush=True)
        return False


_WEBENGINE_OK = _ensure_webengine()


def _exe_dir() -> str:
    """실행 파일(또는 스크립트)이 위치한 디렉토리 반환"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    from PyQt5.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # 다이얼로그만 닫혀도 앱 종료 안 됨

    # ── data 폴더 경로 확정 ──────────────────────────────────────────────────
    data_dir = os.path.join(_exe_dir(), "data")
    os.makedirs(data_dir, exist_ok=True)

    # ── 로거 초기화 (debug.bin 읽기) ─────────────────────────────────────────
    try:
        import core.logger as logger
        logger.init(data_dir)
        logger.info(f"App starting.  data_dir={data_dir}")
    except Exception as e:
        print(f"[WARN] logger init failed: {e}", file=sys.stderr)

    # ── 설정 / 종목 로드 ─────────────────────────────────────────────────────
    try:
        from core.config import load_config, load_stocks
        cfg    = load_config(data_dir)
        stocks = load_stocks(data_dir)
    except Exception as e:
        logger.exception(f"config/stocks load failed: {e}")
        QMessageBox.critical(
            None,
            "초기화 오류",
            f"설정 파일을 불러오는 중 오류가 발생했습니다.\n\n{e}"
        )
        sys.exit(1)

    # ── 플로팅 위젯 실행 ─────────────────────────────────────────────────────
    try:
        from floating import FloatingWidget
        widget = FloatingWidget(data_dir, cfg, stocks)
        widget.show()
        logger.info("FloatingWidget launched")
    except Exception as e:
        logger.exception(f"FloatingWidget launch failed: {e}")
        QMessageBox.critical(
            None,
            "실행 오류",
            f"프로그램을 시작할 수 없습니다.\n\n{e}"
        )
        sys.exit(1)

    # ── 광고 팝업 (프로그램 시작 시 1회만) ──────────────────────────────────
    _ad_popup = None
    if _WEBENGINE_OK:
        try:
            from ad_popup import AdPopup
            _ad_popup = AdPopup()
            _ad_popup.show()
            logger.info("AdPopup launched")
        except Exception as e:
            logger.warning(f"AdPopup launch failed (non-fatal): {e}")
    else:
        logger.warning("AdPopup skipped: PyQtWebEngine unavailable")

    code = app.exec_()
    logger.info(f"App exiting with code {code}")
    sys.exit(code)


if __name__ == "__main__":
    main()
