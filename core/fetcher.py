"""
주식 가격 조회 모듈
- yfinance 로 현재가 / 전일 종가 취득
- FinanceDataReader 로 KR 종목 목록 조회 (캐시 포함)
- 로그는 core.logger 를 통해 출력
"""

import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd

import core.logger as logger

# ── KR 종목 목록 캐시 ──────────────────────────────────────────────────────
_KR_STOCK_LIST: pd.DataFrame | None = None


def _get_kr_stock_list() -> pd.DataFrame:
    """KRX 전체 종목 목록 (코스피 + 코스닥) 캐시 로드"""
    global _KR_STOCK_LIST
    if _KR_STOCK_LIST is None:
        logger.info("KR stock list fetching...")
        try:
            kospi  = fdr.StockListing("KOSPI")[["Code", "Name"]]
            kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Name"]]
            _KR_STOCK_LIST = pd.concat([kospi, kosdaq], ignore_index=True)
            logger.info(f"KR stock list loaded: {len(_KR_STOCK_LIST)} items")
        except Exception as e:
            logger.error(f"KR stock list fetch failed: {e}")
            _KR_STOCK_LIST = pd.DataFrame(columns=["Code", "Name"])
    return _KR_STOCK_LIST


def to_ticker(market: str, code: str) -> str:
    """종목코드 → 야후 파이낸스 티커 변환"""
    if market == "KR":
        # 코스닥은 .KQ, 코스피는 .KS  (단순히 .KS 로 시도, 실패 시 .KQ 도 허용)
        return f"{code}.KS"
    return code.upper()


def search_stocks(query: str, market: str) -> list:
    """
    종목 검색
    - KR: FinanceDataReader KRX 목록에서 부분 일치 검색
    - US: yfinance 직접 조회
    반환: [{"code", "name", "market", "price"}, ...]
    """
    results = []
    query = query.strip()
    if not query:
        return results

    logger.info(f"search_stocks: market={market}, query={query!r}")

    if market == "KR":
        df = _get_kr_stock_list()
        if df.empty:
            return []

        q_upper = query.upper()
        matched = df[
            df["Code"].str.upper().str.contains(q_upper, na=False) |
            df["Name"].str.contains(query, case=False, na=False)
        ].head(10)

        for _, row in matched.iterrows():
            code = str(row["Code"])
            name = str(row["Name"])
            try:
                ticker = to_ticker("KR", code)
                tk     = yf.Ticker(ticker)
                price  = tk.fast_info.last_price
                if price and price > 0:
                    results.append({"code": code, "name": name, "market": "KR", "price": float(price)})
                    logger.debug(f"  found KR: {code} {name} @ {price:,.0f}")
            except Exception as e:
                logger.debug(f"  skip {code}: {e}")
                continue

    else:  # US
        try:
            tk    = yf.Ticker(query.upper())
            info  = tk.info
            price = tk.fast_info.last_price
            name  = info.get("longName") or info.get("shortName") or query.upper()
            if price and price > 0:
                results.append({"code": query.upper(), "name": name, "market": "US", "price": float(price)})
                logger.debug(f"  found US: {query.upper()} {name} @ {price:,.2f}")
        except Exception as e:
            logger.error(f"US search failed ({query}): {e}")

    logger.info(f"search_stocks result: {len(results)} items")
    return results


def fetch_price(market: str, code: str) -> dict | None:
    """
    현재가, 전일종가 반환.  실패 시 None.
    반환: {"current", "prev_close", "change", "change_pct"}
    """
    ticker = to_ticker(market, code)
    logger.debug(f"fetch_price: {ticker}")
    try:
        tk   = yf.Ticker(ticker)
        info = tk.fast_info

        current    = float(info.last_price)
        prev_close = float(info.previous_close)

        if not current or not prev_close:
            logger.warning(f"fetch_price: invalid data for {ticker} (current={current}, prev={prev_close})")
            return None

        result = {
            "current"   : current,
            "prev_close": prev_close,
            "change"    : current - prev_close,
            "change_pct": (current - prev_close) / prev_close * 100,
        }
        logger.debug(f"  {ticker}: {current:,.2f} ({result['change_pct']:+.2f}%)")
        return result

    except Exception as e:
        logger.error(f"fetch_price error ({ticker}): {e}")
        return None
