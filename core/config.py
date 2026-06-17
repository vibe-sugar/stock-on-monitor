"""
설정 / 종목 로드·저장 모듈
모든 파일은 data_dir (= <실행파일위치>/data/) 아래에만 생성됩니다.
"""

import json
import os
from core.constants import CONFIG_FILENAME, STOCKS_FILENAME
import core.logger as logger


# ── 경로 헬퍼 ──────────────────────────────────────────────────────────────

def _config_path(data_dir: str) -> str:
    return os.path.join(data_dir, CONFIG_FILENAME)

def _stocks_path(data_dir: str) -> str:
    return os.path.join(data_dir, STOCKS_FILENAME)


# ── config ──────────────────────────────────────────────────────────────────

def load_config(data_dir: str) -> dict:
    path = _config_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 누락 키를 기본값으로 보완
            merged = default_config()
            merged.update(cfg)
            logger.debug(f"config loaded: {path}")
            return merged
        except Exception as e:
            logger.error(f"config load failed ({path}): {e}")
    logger.info("config not found, using defaults")
    return default_config()


def save_config(data_dir: str, cfg: dict):
    os.makedirs(data_dir, exist_ok=True)
    path = _config_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        logger.info(f"config saved: {path}")
    except Exception as e:
        logger.error(f"config save failed ({path}): {e}")
        raise


def default_config() -> dict:
    return {
        "bg_color"        : "#0d0d0d",   # 거의 검정
        "bg_alpha"        : 220,
        "font_size"       : 9,
        "font_color"      : "#b0b0b0",   # 밝은 회색
        "always_on_top"   : True,
        "use_change_color": True,
        "invert_color"    : False,
        "show_name"       : True,
        "show_code"       : False,
        "show_change_pct" : True,
        "show_change_amt" : False,
        "show_profit_amt" : True,
        "show_profit_pct" : False,
        "show_total"      : False,
        "show_summary"    : False,
        "interval_ms"     : 10000,
        "border_width"    : 0,           # 0 = 테두리 없음
        "border_color"    : "#1e3a4a",
    }


# ── stocks ──────────────────────────────────────────────────────────────────

def load_stocks(data_dir: str) -> list:
    path = _stocks_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                stocks = json.load(f)
            logger.debug(f"stocks loaded: {len(stocks)} items from {path}")
            return stocks
        except Exception as e:
            logger.error(f"stocks load failed ({path}): {e}")
    logger.info("stocks not found, starting empty")
    return []


def save_stocks(data_dir: str, stocks: list):
    os.makedirs(data_dir, exist_ok=True)
    path = _stocks_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        logger.info(f"stocks saved: {len(stocks)} items to {path}")
    except Exception as e:
        logger.error(f"stocks save failed ({path}): {e}")
        raise
