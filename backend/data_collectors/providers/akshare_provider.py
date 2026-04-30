from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import requests

import akshare as ak

from backend.config import settings
from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


def _full_stock_code(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"{code}.SH"
    return f"{code}.SZ"


def _exchange_from_code(code: str) -> str:
    return "SH" if code.endswith(".SH") else "SZ"


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("-", "", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class AkshareProvider(BaseMarketDataProvider):
    provider_name = "akshare"
    market_cap_url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    market_cap_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "close",
    }
    market_cap_batch_size = 200

    def _load_spot(self):
        try:
            return ak.stock_zh_a_spot()
        except Exception as exc:  # pragma: no cover - depends on external service
            raise ProviderError(f"akshare spot fetch failed: {exc}") from exc

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_industry_map() -> dict[str, str]:
        industry_map: dict[str, str] = {}
        try:
            sz_frame = ak.stock_info_sz_name_code(symbol="A股列表")
            for _, row in sz_frame.iterrows():
                code = str(row.get("A股代码", "")).strip().zfill(6)
                industry = str(row.get("所属行业", "")).strip()
                if code and industry:
                    industry_map[f"{code}.SZ"] = industry
        except Exception:
            pass

        sh_headers = {
            "Host": "query.sse.com.cn",
            "Pragma": "no-cache",
            "Referer": "https://www.sse.com.cn/assortment/stock/list/share/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/81.0.4044.138 Safari/537.36"
            ),
        }
        sh_base_params = {
            "REG_PROVINCE": "",
            "CSRC_CODE": "",
            "STOCK_CODE": "",
            "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
            "COMPANY_STATUS": "2,4,5,7,8",
            "type": "inParams",
            "isPagination": "true",
            "pageHelp.cacheSize": "1",
            "pageHelp.beginPage": "1",
            "pageHelp.pageSize": "10000",
            "pageHelp.pageNo": "1",
            "pageHelp.endPage": "1",
        }
        for stock_type in ("1", "8"):
            try:
                response = requests.get(
                    "https://query.sse.com.cn/sseQuery/commonQuery.do",
                    params=sh_base_params | {"STOCK_TYPE": stock_type},
                    headers=sh_headers,
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                for row in payload.get("result", []):
                    code = str(row.get("A_STOCK_CODE", "")).strip().zfill(6)
                    industry = str(row.get("CSRC_CODE_DESC", "")).strip()
                    if code and industry:
                        industry_map[f"{code}.SH"] = industry
            except Exception:
                continue
        return industry_map

    @staticmethod
    def _concept_cache_path() -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return settings.data_dir / f"concept_map_{today}.json"

    @staticmethod
    def _market_cap_cache_path() -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return settings.data_dir / f"market_cap_map_{today}.json"

    @classmethod
    def _load_cached_concept_map(cls) -> dict[str, str] | None:
        cache_path = cls._concept_cache_path()
        if not cache_path.exists():
            return None
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if payload.get("date") != datetime.now().strftime("%Y-%m-%d"):
            return None
        concepts = payload.get("concepts")
        if not isinstance(concepts, dict):
            return None
        return {str(code): str(value) for code, value in concepts.items()}

    @classmethod
    def _save_concept_map(cls, concept_map: dict[str, str]) -> None:
        cache_path = cls._concept_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "concepts": concept_map,
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @classmethod
    @lru_cache(maxsize=1)
    def _load_concept_map(cls) -> dict[str, str]:
        cached = cls._load_cached_concept_map()
        if cached is not None:
            return cached

        concept_map: dict[str, list[str]] = {}
        try:
            concept_frame = ak.stock_sector_spot(indicator="概念")
        except Exception:
            return {}

        for _, row in concept_frame.iterrows():
            sector_label = str(row.get("label", "")).strip()
            sector_name = str(row.get("板块", "")).strip()
            if not sector_label or not sector_name:
                continue
            try:
                detail_frame = ak.stock_sector_detail(sector=sector_label)
            except Exception:
                continue
            for _, detail_row in detail_frame.iterrows():
                code = str(detail_row.get("code", "")).strip().zfill(6)
                if not code:
                    continue
                stock_code = _full_stock_code(code)
                concepts = concept_map.setdefault(stock_code, [])
                if sector_name not in concepts:
                    concepts.append(sector_name)

        flattened = {
            stock_code: ";".join(names[:10])
            for stock_code, names in concept_map.items()
        }
        cls._save_concept_map(flattened)
        return flattened

    @classmethod
    def _load_cached_market_cap_map(cls) -> dict[str, tuple[float, float]]:
        cache_path = cls._market_cap_cache_path()
        if not cache_path.exists():
            return {}
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if payload.get("date") != datetime.now().strftime("%Y-%m-%d"):
            return {}
        entries = payload.get("market_caps")
        if not isinstance(entries, dict):
            return {}
        market_caps: dict[str, tuple[float, float]] = {}
        for stock_code, values in entries.items():
            if not isinstance(values, dict):
                continue
            market_caps[str(stock_code)] = (
                _safe_float(values.get("market_cap")),
                _safe_float(values.get("float_market_cap")),
            )
        return market_caps

    @classmethod
    def _save_market_cap_map(cls, market_cap_map: dict[str, tuple[float, float]]) -> None:
        cache_path = cls._market_cap_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_caps": {
                stock_code: {
                    "market_cap": values[0],
                    "float_market_cap": values[1],
                }
                for stock_code, values in market_cap_map.items()
            },
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _secid_for_code(stock_code: str) -> str:
        code = stock_code.split(".")[0]
        market = "1" if stock_code.endswith(".SH") else "0"
        return f"{market}.{code}"

    @classmethod
    def _fetch_market_cap_batch(cls, stock_codes: list[str]) -> dict[str, tuple[float, float]]:
        if not stock_codes:
            return {}
        params = {
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fields": "f12,f20,f21",
            "secids": ",".join(cls._secid_for_code(stock_code) for stock_code in stock_codes),
        }
        response = requests.get(cls.market_cap_url, params=params, headers=cls.market_cap_headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        diff = payload.get("data", {}).get("diff", [])
        market_cap_map: dict[str, tuple[float, float]] = {}
        for row in diff:
            raw_code = str(row.get("f12", "")).strip().zfill(6)
            if not raw_code:
                continue
            stock_code = _full_stock_code(raw_code)
            market_cap_map[stock_code] = (
                _safe_float(row.get("f20")),
                _safe_float(row.get("f21")),
            )
        return market_cap_map

    @classmethod
    def _load_market_cap_map(cls, stock_codes: list[str]) -> dict[str, tuple[float, float]]:
        cached = cls._load_cached_market_cap_map()
        missing = [stock_code for stock_code in stock_codes if stock_code not in cached]
        if not missing:
            return cached

        enriched = dict(cached)
        for index in range(0, len(missing), cls.market_cap_batch_size):
            batch = missing[index : index + cls.market_cap_batch_size]
            try:
                enriched.update(cls._fetch_market_cap_batch(batch))
            except Exception:
                continue
        if enriched:
            cls._save_market_cap_map(enriched)
        return enriched

    def fetch_stock_basics(self) -> list[StockBasic]:
        frame = self._load_spot()
        industry_map = self._load_industry_map()
        concept_map = self._load_concept_map()
        stock_codes: list[str] = []
        normalized_rows: list[tuple[str, dict]] = []
        for _, row in frame.iterrows():
            raw_code = str(row["代码"]).strip()
            if raw_code.startswith(("sh", "sz", "bj")):
                code = raw_code[2:].zfill(6)
            else:
                code = raw_code.zfill(6)
            stock_code = _full_stock_code(code)
            stock_codes.append(stock_code)
            normalized_rows.append((stock_code, row))
        market_cap_map = self._load_market_cap_map(stock_codes)
        items: list[StockBasic] = []
        for code, row in normalized_rows:
            name = str(row["名称"])
            amount = _safe_float(row.get("成交额"))
            market_cap, float_market_cap = market_cap_map.get(
                code,
                (_safe_float(row.get("总市值")), _safe_float(row.get("流通市值"))),
            )
            items.append(
                StockBasic(
                    stock_code=code,
                    stock_name=name,
                    exchange=_exchange_from_code(code),
                    industry=industry_map.get(code, ""),
                    concepts=concept_map.get(code, ""),
                    market_cap=market_cap,
                    float_market_cap=float_market_cap,
                    is_st="ST" in name.upper(),
                    list_date="2000-01-01",
                    status="active" if _safe_float(row.get("最新价")) > 0 else "halted",
                    avg_amount_20d=amount,
                    is_suspended=_safe_float(row.get("最新价")) <= 0,
                )
            )
        if not items:
            raise ProviderError("akshare returned empty stock basics")
        return items

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        frame = self._load_spot()
        lookup = {}
        for _, row in frame.iterrows():
            raw_code = str(row["代码"]).strip()
            if raw_code.startswith(("sh", "sz", "bj")):
                normalized = _full_stock_code(raw_code[2:].zfill(6))
            else:
                normalized = _full_stock_code(raw_code.zfill(6))
            lookup[normalized] = row
        quotes: list[DailyQuote] = []
        for stock_code in stock_codes:
            row = lookup.get(stock_code)
            if row is None:
                continue
            close = _safe_float(row.get("最新价"))
            open_price = _safe_float(row.get("今开"), close)
            high = _safe_float(row.get("最高"), close)
            low = _safe_float(row.get("最低"), close)
            quotes.append(
                DailyQuote(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    open=open_price or close,
                    high=high or close,
                    low=low or close,
                    close=close,
                    volume=_safe_float(row.get("成交量")),
                    amount=_safe_float(row.get("成交额")),
                    turnover_rate=_safe_float(row.get("换手率")),
                    pct_chg=_safe_float(row.get("涨跌幅")),
                    ma5=close,
                    ma10=close,
                    ma20=close,
                    ma60=close,
                )
            )
        if not quotes:
            raise ProviderError("akshare returned empty daily quotes")
        return quotes

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        snapshots: list[FundamentalSnapshot] = []
        today = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%Y%m%d")
        for stock_code in stock_codes[:50]:
            symbol = stock_code.split(".")[0]
            try:
                frame = ak.stock_financial_analysis_indicator(symbol=symbol)
            except Exception:
                continue
            if frame.empty:
                continue
            row = frame.iloc[0]
            snapshots.append(
                FundamentalSnapshot(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    revenue_yoy=_safe_float(row.get("主营业务收入增长率(%)"), None),
                    net_profit_yoy=_safe_float(row.get("净利润增长率(%)"), None),
                    roe=_safe_float(row.get("净资产收益率(%)"), None),
                    gross_margin=_safe_float(row.get("销售毛利率(%)"), None),
                    debt_ratio=_safe_float(row.get("资产负债率(%)"), None),
                    operating_cashflow=_safe_float(row.get("每股经营性现金流(元)"), None),
                    goodwill=None,
                    source_status="fresh" if today else "fresh",
                )
            )
        return snapshots
