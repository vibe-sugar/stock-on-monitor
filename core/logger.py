"""
debug.bin 기반 로거 시스템
- data/debug.bin 에 "1" 이 있으면 로그 활성화
- data/debug.bin 에 "0" 이 있으면 로그 비활성화 (기본)
- 로그 파일: data/debug.log
"""

import os
import sys
import logging
import datetime

# 전역 logger 인스턴스
_logger: logging.Logger | None = None
_debug_enabled: bool = False
_data_dir: str = ""


def init(data_dir: str):
    """앱 시작 시 1회 호출. data_dir = data 폴더 경로"""
    global _logger, _debug_enabled, _data_dir
    _data_dir = data_dir
    os.makedirs(data_dir, exist_ok=True)

    debug_bin = os.path.join(data_dir, "debug.bin")

    # debug.bin 없으면 기본값 "0" 으로 생성
    if not os.path.exists(debug_bin):
        with open(debug_bin, "w", encoding="utf-8") as f:
            f.write("0")

    # 파일 내용 읽어서 활성화 여부 결정
    try:
        with open(debug_bin, "r", encoding="utf-8") as f:
            content = f.read().strip()
        _debug_enabled = (content == "1")
    except Exception:
        _debug_enabled = False

    if _debug_enabled:
        log_path = os.path.join(data_dir, "debug.log")
        _logger = logging.getLogger("StockOnMonitor")
        _logger.setLevel(logging.DEBUG)
        _logger.handlers.clear()

        # 파일 핸들러 (UTF-8, append)
        fh = logging.FileHandler(log_path, encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-7s %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(fmt)
        _logger.addHandler(fh)

        # 콘솔 핸들러
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(fmt)
        _logger.addHandler(ch)

        _logger.info("=" * 60)
        _logger.info(f"Debug logging started  ({datetime.datetime.now():%Y-%m-%d %H:%M:%S})")
        _logger.info(f"data_dir = {data_dir}")
        _logger.info("=" * 60)
    else:
        # 비활성화 시 NullHandler
        _logger = logging.getLogger("StockOnMonitor")
        _logger.handlers.clear()
        _logger.addHandler(logging.NullHandler())


def is_debug() -> bool:
    return _debug_enabled


def debug(msg: str):
    if _logger:
        _logger.debug(msg)


def info(msg: str):
    if _logger:
        _logger.info(msg)


def warning(msg: str):
    if _logger:
        _logger.warning(msg)


def error(msg: str):
    if _logger:
        _logger.error(msg)


def exception(msg: str):
    if _logger:
        _logger.exception(msg)
