import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 다이얼로그 닫아도 종료 안 됨

    # ── 현재 실행 경로를 데이터 디렉토리로 사용 ────────
    data_dir = os.path.dirname(os.path.abspath(__file__))

    # ── 설정 / 종목 로드 ────────────────────────────────
    try:
        from core.config import load_config, load_stocks
        cfg    = load_config(data_dir)
        stocks = load_stocks(data_dir)
    except Exception as e:
        # 설정 파일 로드 실패 - 오류 표시 후 종료
        QMessageBox.critical(
            None,
            "프로그램 오류",
            f"필요한 파일을 찾을 수 없습니다:\n{e}"
        )
        sys.exit(1)

    # ── 플로팅 위젯 실행 ────────────────────────────────
    try:
        from floating import FloatingWidget
        widget = FloatingWidget(data_dir, cfg, stocks)
        widget.show()
    except Exception as e:
        # 위젯 실행 실패 - 오류 표시 후 종료
        QMessageBox.critical(
            None,
            "프로그램 오류",
            f"프로그램을 실행할 수 없습니다:\n{e}"
        )
        sys.exit(1)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
