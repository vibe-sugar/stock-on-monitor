import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd

# ── 한국 종목 전체 목록 캐시 ──────────────────────────
_KR_STOCK_LIST = None

def _get_kr_stock_list() -> pd.DataFrame:
    """KRX 전체 종목 목록 (코스피 + 코스닥) 캐시 로드"""
    global _KR_STOCK_LIST
    if _KR_STOCK_LIST is None:
        try:
            kospi  = fdr.StockListing("KOSPI")[["Code", "Name"]]
            kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Name"]]
            _KR_STOCK_LIST = pd.concat([kospi, kosdaq], ignore_index=True)
        except Exception:
            _KR_STOCK_LIST = pd.DataFrame(columns=["Code", "Name"])
    return _KR_STOCK_LIST


def to_ticker(market: str, code: str) -> str:
    """종목코드 → 야후 파이낸스 티커 변환"""
    if market == "KR":
        return f"{code}.KS"
    return code.upper()


def search_stocks(query: str, market: str) -> list:
    """
    종목코드 또는 종목명으로 검색
    - KR: FinanceDataReader KRX 목록에서 검색
    - US: yfinance 직접 조회
    반환: [{"code": ..., "name": ..., "market": ..., "price": ...}, ...]
    """
    results = []
    query   = query.strip()

    if market == "KR":
        df = _get_kr_stock_list()
        if df.empty:
            return []

        # 코드 또는 종목명 부분 일치 검색 (대소문자 무시)
        q_upper = query.upper()
        matched = df[
            df["Code"].str.upper().str.contains(q_upper, na=False) |
            df["Name"].str.contains(query, case=False, na=False)
        ].head(10)  # 최대 10건

        for _, row in matched.iterrows():
            code = row["Code"]
            name = row["Name"]
            try:
                ticker = to_ticker("KR", code)
                price  = yf.Ticker(ticker).fast_info.last_price
                if price and price > 0:
                    results.append({
                        "code"  : code,
                        "name"  : name,
                        "market": "KR",
                        "price" : price,
                    })
            except Exception:
                # 가격 조회 실패 종목은 건너뜀
                continue

    else:
        # 미국 종목: 코드 직접 조회
        try:
            tk    = yf.Ticker(query.upper())
            info  = tk.info
            price = tk.fast_info.last_price
            name  = info.get("longName") or info.get("shortName") or query.upper()
            if price and price > 0:
                results.append({
                    "code"  : query.upper(),
                    "name"  : name,
                    "market": "US",
                    "price" : price,
                })
        except Exception:
            pass

    return results


def fetch_price(market: str, code: str) -> dict | None:
    """
    현재가, 전일종가 반환
    실패 시 None 반환
    """
    try:
        ticker = to_ticker(market, code)
        tk     = yf.Ticker(ticker)
        info   = tk.fast_info

        current    = float(info.last_price)
        prev_close = float(info.previous_close)

        if not current or not prev_close:
            return None

        return {
            "current"   : current,
            "prev_close": prev_close,
            "change"    : current - prev_close,
            "change_pct": (current - prev_close) / prev_close * 100,
        }
    except Exception:
        return None
