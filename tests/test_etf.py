#!/usr/bin/env python3
"""
ETF / 주식 조회 디버깅 테스트 프로그램
실행: python tests/test_etf.py [--verbose] [--market KR|KR_ETF|US] [--query 검색어]

옵션 없이 실행하면 사전 정의된 테스트 케이스 전체를 실행합니다.
"""

import sys
import os
import argparse
import time

# 프로젝트 루트를 sys.path 에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 로거 초기화 (data 폴더)
import core.logger as logger
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
logger.init(DATA_DIR)

from core.fetcher import (
    search_stocks,
    fetch_price,
    _get_kr_stock_list,
    _get_kr_etf_list,
    to_ticker,
    clear_cache,
)

# ── ANSI 색상 ────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}[PASS]{RESET} {msg}")
def fail(msg): print(f"  {RED}[FAIL]{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}[WARN]{RESET} {msg}")
def info(msg): print(f"  {CYAN}[INFO]{RESET} {msg}")
def sep(title=""):
    width = 60
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{BOLD}{'─'*pad} {title} {'─'*pad}{RESET}")
    else:
        print(f"\n{'─'*width}")


# ── 테스트 케이스 정의 ────────────────────────────────────────────────────────
FETCH_CASES = [
    # (market, code, 종목명 힌트)
    ("KR",     "005930", "삼성전자"),
    ("KR",     "000660", "SK하이닉스"),
    ("KR",     "035720", "카카오"),
    ("KR_ETF", "069500", "KODEX 200"),
    ("KR_ETF", "114800", "KODEX 인버스"),
    ("KR_ETF", "122630", "KODEX 레버리지"),
    ("KR_ETF", "229200", "KODEX 코스닥150"),
    ("KR_ETF", "102110", "TIGER 200"),
    ("KR_ETF", "133690", "TIGER 미국나스닥100"),
    ("KR_ETF", "360750", "TIGER 미국S&P500"),
    ("KR_ETF", "379800", "KODEX 미국S&P500"),
    ("KR_ETF", "305720", "KODEX 2차전지산업"),
    ("KR_ETF", "091160", "KODEX 반도체"),
    ("US",     "AAPL",  "Apple"),
    ("US",     "SPY",   "SPDR S&P500 ETF"),
    ("US",     "QQQ",   "Invesco QQQ"),
    ("US",     "TSLA",  "Tesla"),
]

SEARCH_CASES = [
    # (market, query, 예상 최소 결과 수)
    ("KR",     "삼성전자",    1),
    ("KR",     "005930",     1),
    ("KR",     "하이닉스",    1),
    ("KR_ETF", "KODEX 200",  1),
    ("KR_ETF", "069500",     1),
    ("KR_ETF", "TIGER",      3),
    ("KR_ETF", "레버리지",    1),
    ("KR_ETF", "반도체",      1),
    ("KR_ETF", "나스닥",      1),
    ("US",     "AAPL",       1),
    ("US",     "SPY",        1),
]


# ── 캐시 로드 테스트 ────────────────────────────────────────────────────────

def test_cache_load():
    sep("캐시 로드 테스트")
    clear_cache()

    t0 = time.time()
    df_stock = _get_kr_stock_list()
    t1 = time.time()
    if len(df_stock) > 0:
        ok(f"KR 주식 목록: {len(df_stock):,}개  ({t1-t0:.1f}s)")
    else:
        fail(f"KR 주식 목록 로드 실패 (0건)")

    t0 = time.time()
    df_etf = _get_kr_etf_list()
    t1 = time.time()
    if len(df_etf) > 0:
        ok(f"KR ETF 목록:  {len(df_etf):,}개  ({t1-t0:.1f}s)")
        info(f"컬럼: {list(df_etf.columns)}")
    else:
        fail(f"KR ETF 목록 로드 실패 (0건)")

    # 2nd call: 캐시 히트
    t0 = time.time()
    _get_kr_etf_list()
    t1 = time.time()
    if (t1 - t0) < 0.01:
        ok(f"캐시 히트 확인  ({(t1-t0)*1000:.1f}ms)")
    else:
        warn(f"캐시 히트가 느림  ({t1-t0:.3f}s)")

    return len(df_stock) > 0 and len(df_etf) > 0


# ── fetch_price 테스트 ─────────────────────────────────────────────────────

def test_fetch_price(verbose: bool = False):
    sep("fetch_price 테스트")
    passed = failed = 0

    for market, code, hint in FETCH_CASES:
        ticker = to_ticker(market, code)
        t0 = time.time()
        result = fetch_price(market, code)
        elapsed = time.time() - t0

        if result is None:
            fail(f"{ticker:<18} ({hint})  → None")
            failed += 1
        else:
            cur = result["current"]
            chg = result["change_pct"]
            arrow = "▲" if chg > 0 else ("▼" if chg < 0 else "─")
            msg = (
                f"{ticker:<18} ({hint:<20})  "
                f"현재가={cur:>10,.2f}  {arrow}{chg:+.2f}%  ({elapsed:.1f}s)"
            )
            ok(msg)
            passed += 1

            if verbose:
                info(f"  prev_close={result['prev_close']:,.2f}  change={result['change']:+,.2f}")

    sep()
    print(f"  fetch_price 결과:  {GREEN}{passed} 통과{RESET}  /  {RED}{failed} 실패{RESET}  (총 {passed+failed})")
    return failed == 0


# ── search_stocks 테스트 ────────────────────────────────────────────────────

def test_search(verbose: bool = False):
    sep("search_stocks 테스트")
    passed = failed = 0

    for market, query, min_count in SEARCH_CASES:
        t0 = time.time()
        results = search_stocks(query, market)
        elapsed = time.time() - t0

        if len(results) >= min_count:
            names = "  /  ".join(r["name"] for r in results[:3])
            ok(
                f"[{market:<8}] {query:<20}  {len(results):>2}건  ({elapsed:.1f}s)  "
                f"→ {names}"
            )
            passed += 1
            if verbose:
                for r in results:
                    price_str = f"{r['price']:,.2f}" if market == "US" else f"{r['price']:,.0f}"
                    info(f"  {r['code']}  {r['name']:<30}  {price_str}")
        else:
            fail(
                f"[{market:<8}] {query:<20}  {len(results)}건 (기대 ≥{min_count})  ({elapsed:.1f}s)"
            )
            failed += 1

    sep()
    print(f"  search_stocks 결과:  {GREEN}{passed} 통과{RESET}  /  {RED}{failed} 실패{RESET}  (총 {passed+failed})")
    return failed == 0


# ── 커스텀 단일 쿼리 테스트 ─────────────────────────────────────────────────

def test_custom(market: str, query: str, verbose: bool):
    sep(f"커스텀 검색: [{market}] {query!r}")
    results = search_stocks(query, market)
    if not results:
        fail("결과 없음")
        return
    print(f"\n  {len(results)}건 검색됨:\n")
    for r in results:
        price_str = f"{r['price']:,.2f}" if r["market"] == "US" else f"{r['price']:,.0f}"
        print(f"  {r['code']:<8}  {r['name']:<35}  {price_str}")

    # 첫 번째 결과로 fetch_price 도 실행
    if results:
        r = results[0]
        sep(f"fetch_price: {r['code']} ({r['name']})")
        data = fetch_price(r["market"], r["code"])
        if data:
            ok(
                f"현재가={data['current']:,.2f}  "
                f"전일종가={data['prev_close']:,.2f}  "
                f"변동={data['change']:+,.2f}  ({data['change_pct']:+.2f}%)"
            )
        else:
            fail("fetch_price 실패")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ETF/주식 조회 디버깅 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python tests/test_etf.py                        # 전체 테스트
  python tests/test_etf.py --verbose              # 상세 출력
  python tests/test_etf.py --market KR_ETF --query KODEX
  python tests/test_etf.py --market KR     --query 삼성
  python tests/test_etf.py --market US     --query SPY
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력")
    parser.add_argument("--market",  "-m", default=None, help="KR / KR_ETF / US")
    parser.add_argument("--query",   "-q", default=None, help="검색어")
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*60}")
    print(f"  StockOnMonitor — ETF/주식 조회 테스트")
    print(f"  Python {sys.version.split()[0]}   ROOT={ROOT}")
    print(f"{'='*60}{RESET}\n")

    # 커스텀 쿼리 모드
    if args.market and args.query:
        test_custom(args.market, args.query, args.verbose)
        return

    # 전체 테스트 모드
    all_pass = True
    all_pass &= test_cache_load()
    all_pass &= test_fetch_price(args.verbose)
    all_pass &= test_search(args.verbose)

    sep("최종 결과")
    if all_pass:
        print(f"\n  {GREEN}{BOLD}✓  모든 테스트 통과{RESET}\n")
    else:
        print(f"\n  {RED}{BOLD}✗  일부 테스트 실패 — 위 로그를 확인하세요{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
