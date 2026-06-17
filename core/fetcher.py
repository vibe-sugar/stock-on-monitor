"""
주식/ETF 가격 조회 모듈

지원 시장:
  KR   — 한국 주식 (코스피 + 코스닥)
  KR_ETF — 한국 ETF  (ETF/KR)
  US   — 미국 주식/ETF (yfinance 직접 조회)

캐시 전략:
  _KR_STOCK_LIST  : KOSPI + KOSDAQ 합산 (Code, Name)
  _KR_ETF_LIST    : ETF/KR 전체   (Symbol→Code, Name)
  두 목록은 첫 조회 시 1회 로드 후 프로세스 종료까지 재사용

가격 취득:
  모든 KR/KR_ETF 가격은 yfinance (.KS suffix) 로 실시간 조회
  ETF/KR StockListing 의 Price 컬럼은 검색 결과 미리보기용으로만 사용
"""

from __future__ import annotations

import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd

import core.logger as logger

# ── 캐시 ────────────────────────────────────────────────────────────────────
_KR_STOCK_LIST: pd.DataFrame | None = None   # columns: Code, Name
_KR_ETF_LIST  : pd.DataFrame | None = None   # columns: Code, Name, Price


def _get_kr_stock_list() -> pd.DataFrame:
    """KOSPI + KOSDAQ 합산 종목 목록 (캐시)"""
    global _KR_STOCK_LIST
    if _KR_STOCK_LIST is None:
        logger.info("KR stock list loading (KOSPI + KOSDAQ)...")
        try:
            kospi  = fdr.StockListing("KOSPI")[["Code", "Name"]]
            kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Name"]]
            _KR_STOCK_LIST = pd.concat([kospi, kosdaq], ignore_index=True)
            logger.info(f"KR stock list loaded: {len(_KR_STOCK_LIST)} items")
        except Exception as e:
            logger.error(f"KR stock list fetch failed: {e}")
            _KR_STOCK_LIST = pd.DataFrame(columns=["Code", "Name"])
    return _KR_STOCK_LIST


def _get_kr_etf_list() -> pd.DataFrame:
    """한국 ETF 전체 목록 (캐시)  columns: Code, Name, Price"""
    global _KR_ETF_LIST
    if _KR_ETF_LIST is None:
        logger.info("KR ETF list loading (ETF/KR)...")
        try:
            raw = fdr.StockListing("ETF/KR")
            # Symbol → Code, Price 유지
            df = raw[["Symbol", "Name", "Price"]].rename(columns={"Symbol": "Code"})
            df = df.copy()
            df["Code"] = df["Code"].astype(str).str.strip()
            _KR_ETF_LIST = df.reset_index(drop=True)
            logger.info(f"KR ETF list loaded: {len(_KR_ETF_LIST)} items")
        except Exception as e:
            logger.error(f"KR ETF list fetch failed: {e}")
            _KR_ETF_LIST = pd.DataFrame(columns=["Code", "Name", "Price"])
    return _KR_ETF_LIST


# ── 티커 변환 ────────────────────────────────────────────────────────────────

def to_ticker(market: str, code: str) -> str:
    """종목코드 → yfinance 티커 변환"""
    if market in ("KR", "KR_ETF"):
        return f"{code}.KS"
    return code.upper()


# ── 검색 ─────────────────────────────────────────────────────────────────────

def search_stocks(query: str, market: str) -> list:
    """
    종목/ETF 검색
    market: "KR" | "KR_ETF" | "US"
    반환: [{"code", "name", "market", "price"}, ...]
    """
    query = query.strip()
    if not query:
        return []

    logger.info(f"search_stocks: market={market}, query={query!r}")

    # ── 한국 주식 ──────────────────────────────────────────────────────────
    if market == "KR":
        df      = _get_kr_stock_list()
        results = _search_kr_df(df, query, "Code", "Name", "KR")
        return results

    # ── 한국 ETF ───────────────────────────────────────────────────────────
    elif market == "KR_ETF":
        df      = _get_kr_etf_list()
        results = _search_kr_df(df, query, "Code", "Name", "KR_ETF", price_col="Price")
        return results

    # ── 미국 주식/ETF ──────────────────────────────────────────────────────
    else:
        return _search_us(query)


def _search_kr_df(
    df: pd.DataFrame,
    query: str,
    code_col: str,
    name_col: str,
    market_label: str,
    price_col: str | None = None,
) -> list:
    """KR / KR_ETF 공용 검색 헬퍼"""
    if df.empty:
        return []

    q_upper = query.upper()
    matched = df[
        df[code_col].str.upper().str.contains(q_upper, na=False) |
        df[name_col].str.contains(query, case=False, na=False)
    ].head(15)

    results = []
    for _, row in matched.iterrows():
        code = str(row[code_col])
        name = str(row[name_col])

        # FDR 가격 컬럼이 있으면 빠른 미리보기로 사용,
        # 없으면 yfinance 실시간 조회
        if price_col and price_col in row.index:
            try:
                fdr_price = float(row[price_col])
                if fdr_price > 0:
                    results.append({
                        "code"  : code,
                        "name"  : name,
                        "market": market_label,
                        "price" : fdr_price,
                    })
                    logger.debug(f"  {code} ({name}): {fdr_price:,.0f} [FDR]")
                    continue
            except Exception:
                pass

        # yfinance 로 가격 조회
        try:
            tk    = yf.Ticker(to_ticker(market_label, code))
            price = tk.fast_info.last_price
            if price and price > 0:
                results.append({
                    "code"  : code,
                    "name"  : name,
                    "market": market_label,
                    "price" : float(price),
                })
                logger.debug(f"  {code} ({name}): {price:,.0f} [YF]")
        except Exception as e:
            logger.debug(f"  skip {code}: {e}")

    logger.info(f"search result: {len(results)} items")
    return results


def _search_us(query: str) -> list:
    """미국 종목 검색 (yfinance 직접 조회)"""
    results = []
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
                "price" : float(price),
            })
            logger.debug(f"  US {query.upper()} ({name}): {price:,.2f}")
    except Exception as e:
        logger.error(f"US search failed ({query}): {e}")
    return results


# ── 가격 갱신 ────────────────────────────────────────────────────────────────

def fetch_price(market: str, code: str) -> dict | None:
    """
    현재가 / 전일종가 실시간 조회 (yfinance)
    반환: {"current", "prev_close", "change", "change_pct"} 또는 None
    """
    ticker = to_ticker(market, code)
    logger.debug(f"fetch_price: {ticker} (market={market})")
    try:
        info = yf.Ticker(ticker).fast_info

        current    = float(info.last_price)
        prev_close = float(info.previous_close)

        if not current or not prev_close:
            logger.warning(f"fetch_price: invalid data {ticker} cur={current} prev={prev_close}")
            return None

        result = {
            "current"   : current,
            "prev_close": prev_close,
            "change"    : current - prev_close,
            "change_pct": (current - prev_close) / prev_close * 100,
        }
        logger.debug(f"  {ticker}: {current:,.2f}  ({result['change_pct']:+.2f}%)")
        return result

    except Exception as e:
        logger.error(f"fetch_price error ({ticker}): {e}")
        return None


# ── 캐시 강제 초기화 (필요 시 외부에서 호출) ────────────────────────────────

def clear_cache():
    """캐시를 비워 다음 조회 시 재로드하도록 강제"""
    global _KR_STOCK_LIST, _KR_ETF_LIST
    _KR_STOCK_LIST = None
    _KR_ETF_LIST   = None
    logger.info("fetcher cache cleared")
