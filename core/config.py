import json
import os
from core.constants import CONFIG_FILENAME, STOCKS_FILENAME, INSTALL_FILENAME

def get_install_info():
    base = _exe_dir()
    path = os.path.join(base, INSTALL_FILENAME)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_install_info(data_dir: str):
    base = _exe_dir()
    path = os.path.join(base, INSTALL_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"data_dir": data_dir}, f, ensure_ascii=False, indent=2)

def load_config(data_dir: str) -> dict:
    path = os.path.join(data_dir, CONFIG_FILENAME)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_config()

def save_config(data_dir: str, cfg: dict):
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, CONFIG_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def default_config() -> dict:
    return {
        "bg_color"           : "#111111",   # 검정에 가까운 어두운 배경
        "bg_alpha"           : 210,          # 약간 투명
        "font_size"          : 9,
        "font_color"         : "#aaaaaa",   # 중간 회색
        "use_change_color"   : True,
        "invert_color"       : False,
        "show_current_price" : True,
        "show_code"          : False,
        "show_name"          : False,
        "show_change_amt"    : False,
        "show_change_pct"    : True,
        "show_profit_amt"    : True,
        "show_profit_pct"    : False,
        "show_total"         : False,
        "show_summary"       : False,
        "interval_ms"        : 10000,
    }

def load_stocks(data_dir: str) -> list:
    path = os.path.join(data_dir, STOCKS_FILENAME)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_stocks()

def save_stocks(data_dir: str, stocks: list):
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, STOCKS_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)

def default_stocks() -> list:
    return []

def _exe_dir() -> str:
    if getattr(__import__("sys"), "frozen", False):
        return os.path.dirname(__import__("sys").executable)
    return os.path.dirname(os.path.abspath(__import__("sys").argv[0]))
