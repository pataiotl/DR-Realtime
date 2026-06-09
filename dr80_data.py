"""
DR80 Asset Definitions
======================
Complete list of all 89 DR80 depository receipts issued by Krungthai Bank (KTB),
with corrected yfinance tickers, ratios, exchange info, and currency mappings.

Source: https://exchangerate.krungthai.com/dr-drx
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Exchange → Currency → FX ticker mappings
# ---------------------------------------------------------------------------
EXCHANGE_CURRENCY_MAP = {
    "NASDAQ":             "USD",
    "NYSE":               "USD",
    "NYSE Arca":          "USD",
    "HKEX":               "HKD",
    "Shanghai":           "CNY",
    "Shenzhen":           "CNY",
    "TYO":                "JPY",
    "Euronext Paris":     "EUR",
    "Euronext Milan":     "EUR",
    "Nasdaq Copenhagen":  "DKK",
    "SGX":                "SGD",
}

# Direct FX tickers (XXX → THB)
FX_DIRECT_TICKERS = {
    "USD": "USDTHB=X",
    "HKD": "HKDTHB=X",
    "CNY": "CNYTHB=X",
    "JPY": "JPYTHB=X",
    "EUR": "EURTHB=X",
    "DKK": "DKKTHB=X",
    "SGD": "SGDTHB=X",
}

# Fallback: USD-based pairs for computing XXX→THB via USD intermediary
# XXX_to_THB = USDTHB / USDXXX
FX_USD_FALLBACK_TICKERS = {
    "HKD": "USDHKD=X",
    "CNY": "USDCNY=X",
    "JPY": "USDJPY=X",
    "EUR": "EURUSD=X",   # special: EUR is quoted as EURUSD, so THB = USDTHB * EURUSD
    "DKK": "USDDKK=X",
    "SGD": "USDSGD=X",
}


@dataclass
class DR80Asset:
    """Single DR80 depository receipt definition."""
    dr_symbol: str            # e.g. "AAPL80"
    underlying_ticker: str    # corrected yfinance ticker, e.g. "AAPL"
    ratio: int                # e.g. 1000  (1:1,000 means ratio = 1000)
    exchange: str             # e.g. "NASDAQ"

    @property
    def currency(self) -> str:
        return EXCHANGE_CURRENCY_MAP.get(self.exchange, "USD")

    @property
    def fx_direct_ticker(self) -> str:
        return FX_DIRECT_TICKERS.get(self.currency, "USDTHB=X")

    @property
    def fx_fallback_ticker(self) -> str | None:
        return FX_USD_FALLBACK_TICKERS.get(self.currency)


# ---------------------------------------------------------------------------
# All 89 DR80 Assets
# ---------------------------------------------------------------------------
DR80_ASSETS: list[DR80Asset] = [
    # ── US Stocks (NASDAQ) ──────────────────────────────────────────────
    DR80Asset("AAPL80",     "AAPL",       1000,   "NASDAQ"),
    DR80Asset("AMD80",      "AMD",        5000,   "NASDAQ"),
    DR80Asset("AMZN80",     "AMZN",       4000,   "NASDAQ"),
    DR80Asset("AVGO80",     "AVGO",       5000,   "NASDAQ"),
    DR80Asset("BKNG80",     "BKNG",       2000,   "NASDAQ"),
    DR80Asset("COIN80",     "COIN",       1000,   "NASDAQ"),
    DR80Asset("CRWD80",     "CRWD",       1000,   "NASDAQ"),
    DR80Asset("GOOG80",     "GOOG",       2000,   "NASDAQ"),
    DR80Asset("GRAB80",     "GRAB",       10,     "NASDAQ"),
    DR80Asset("HOOD80",     "HOOD",       1000,   "NASDAQ"),
    DR80Asset("META80",     "META",       8000,   "NASDAQ"),
    DR80Asset("MICRON80",   "MU",         1000,   "NASDAQ"),
    DR80Asset("MRVL80",     "MRVL",       1000,   "NASDAQ"),
    DR80Asset("MSFT80",     "MSFT",       2000,   "NASDAQ"),
    DR80Asset("NFLX80",     "NFLX",       1000,   "NASDAQ"),
    DR80Asset("NVDA80",     "NVDA",       200,    "NASDAQ"),
    DR80Asset("PANW80",     "PANW",       1000,   "NASDAQ"),
    DR80Asset("PEP80",      "PEP",        5000,   "NASDAQ"),
    DR80Asset("RKLB80",     "RKLB",       1000,   "NASDAQ"),
    DR80Asset("SBUX80",     "SBUX",       2000,   "NASDAQ"),
    DR80Asset("SNDK80",     "SNDK",       10000,  "NASDAQ"),
    DR80Asset("TSLA80",     "TSLA",       5000,   "NASDAQ"),

    # ── US Stocks (NYSE) ────────────────────────────────────────────────
    DR80Asset("ABBV80",     "ABBV",       1000,   "NYSE"),
    DR80Asset("ANET80",     "ANET",       1000,   "NYSE"),       # HTML had "ANET80" as ticker
    DR80Asset("BOEING80",   "BA",         1000,   "NYSE"),
    DR80Asset("BRKB80",     "BRK-B",      10000,  "NYSE"),
    DR80Asset("CRM80",      "CRM",        1000,   "NYSE"),
    DR80Asset("ESTEE80",    "EL",         3000,   "NYSE"),
    DR80Asset("GEV80",      "GEV",        1000,   "NYSE"),
    DR80Asset("KO80",       "KO",         1000,   "NYSE"),
    DR80Asset("LLY80",      "LLY",        20000,  "NYSE"),
    DR80Asset("MA80",       "MA",         10000,  "NYSE"),
    DR80Asset("MP80",       "MP",         100,    "NYSE"),       # HTML had "MP80" as ticker
    DR80Asset("NEE80",      "NEE",        1000,   "NYSE"),
    DR80Asset("NIKE80",     "NKE",        2000,   "NYSE"),
    DR80Asset("VISA80",     "V",          8000,   "NYSE"),

    # ── US ETFs (NYSE Arca) ─────────────────────────────────────────────
    DR80Asset("GOLDUS80",   "GLD",        1000,   "NYSE Arca"),
    DR80Asset("SP500US80",  "SPYM",       1000,   "NYSE Arca"),
    DR80Asset("SPBOND80",   "SPAB",       100,    "NYSE Arca"),
    DR80Asset("SPCOM80",    "XLC",        1000,   "NYSE Arca"),
    DR80Asset("SPENGY80",   "XLE",        500,    "NYSE Arca"),
    DR80Asset("SPFIN80",    "XLF",        100,    "NYSE Arca"),
    DR80Asset("SPHLTH80",   "XLV",        1000,   "NYSE Arca"),
    DR80Asset("SPTECH80",   "XLK",        500,    "NYSE Arca"),

    # ── Hong Kong (HKEX) ────────────────────────────────────────────────
    DR80Asset("BABA80",     "9988.HK",    100,    "HKEX"),
    DR80Asset("BIDU80",     "9888.HK",    100,    "HKEX"),
    DR80Asset("BYDCOM80",   "1211.HK",    1000,   "HKEX"),
    DR80Asset("CATL80",     "3750.HK",    100,    "HKEX"),
    DR80Asset("GEELY80",    "0175.HK",    10,     "HKEX"),
    DR80Asset("JD80",       "9618.HK",    100,    "HKEX"),
    DR80Asset("JLMAG80",    "6680.HK",    10,     "HKEX"),
    DR80Asset("KUAISH80",   "1024.HK",    100,    "HKEX"),
    DR80Asset("MAOGEP80",   "1318.HK",    100,    "HKEX"),
    DR80Asset("MEITUAN80",  "3690.HK",    100,    "HKEX"),
    DR80Asset("MIDEA80",    "0300.HK",    100,    "HKEX"),
    DR80Asset("MIXUE80",    "2097.HK",    100,    "HKEX"),
    DR80Asset("MNSO80",     "9896.HK",    10,     "HKEX"),
    DR80Asset("MONTAGE80",  "6809.HK",    100,    "HKEX"),
    DR80Asset("NETEASE80",  "9999.HK",    100,    "HKEX"),
    DR80Asset("NONGFU80",   "9633.HK",    100,    "HKEX"),
    DR80Asset("PETROCN80",  "0857.HK",    10,     "HKEX"),
    DR80Asset("PINGAN80",   "2318.HK",    100,    "HKEX"),
    DR80Asset("POPMART80",  "9992.HK",    100,    "HKEX"),
    DR80Asset("SUNNY80",    "2382.HK",    100,    "HKEX"),
    DR80Asset("TENCENT80",  "0700.HK",    100,    "HKEX"),
    DR80Asset("TRIPCOM80",  "9961.HK",    1000,   "HKEX"),
    DR80Asset("WUXIAT80",   "2359.HK",    100,    "HKEX"),
    DR80Asset("XIAOMI80",   "1810.HK",    10,     "HKEX"),
    DR80Asset("ZIJIN80",    "2899.HK",    10,     "HKEX"),

    # ── China A-Shares (Shanghai) ───────────────────────────────────────
    DR80Asset("CAMBRI80",   "688256.SS",  1000,   "Shanghai"),
    DR80Asset("CNRE80",     "600111.SS",  100,    "Shanghai"),
    DR80Asset("CYPC80",     "600900.SS",  10,     "Shanghai"),
    DR80Asset("MOUTAI80",   "600519.SS",  1000,   "Shanghai"),

    # ── China A-Shares (Shenzhen) ───────────────────────────────────────
    DR80Asset("IFLYTEK80",  "002230.SZ",  100,    "Shenzhen"),
    DR80Asset("NAURA80",    "002371.SZ",  100,    "Shenzhen"),
    DR80Asset("ZJINNO80",   "300308.SZ",  1000,   "Shenzhen"),

    # ── Japan (Tokyo) ──────────────────────────────────────────────────
    DR80Asset("NIKKEI80",   "1321.T",     1000,   "TYO"),
    DR80Asset("SANRIO80",   "8136.T",     20,     "TYO"),
    DR80Asset("SOFTBANK80", "9984.T",     100,    "TYO"),
    DR80Asset("SONY80",     "6758.T",     200,    "TYO"),
    DR80Asset("TEL80",      "8035.T",     1000,   "TYO"),
    DR80Asset("TOYOTA80",   "7203.T",     100,    "TYO"),
    DR80Asset("UNIQLO80",   "9983.T",     1000,   "TYO"),

    # ── Europe (Euronext Paris) ─────────────────────────────────────────
    DR80Asset("HERMES80",   "RMS.PA",     10000,  "Euronext Paris"),
    DR80Asset("LOREAL80",   "OR.PA",      10000,  "Euronext Paris"),
    DR80Asset("SANOFI80",   "SAN.PA",     1000,   "Euronext Paris"),

    # ── Europe (Euronext Milan) ─────────────────────────────────────────
    DR80Asset("FERRARI80",  "RACE.MI",    10000,  "Euronext Milan"),

    # ── Denmark (Nasdaq Copenhagen) ─────────────────────────────────────
    DR80Asset("NOVOB80",    "NOVO-B.CO",  1000,   "Nasdaq Copenhagen"),

    # ── Singapore (SGX) ────────────────────────────────────────────────
    DR80Asset("SINGTEL80",  "Z74.SI",     10,     "SGX"),
]


def get_all_underlying_tickers() -> list[str]:
    """Return a deduplicated list of all underlying yfinance tickers."""
    return list(dict.fromkeys(a.underlying_ticker for a in DR80_ASSETS))


def get_all_fx_tickers() -> list[str]:
    """Return a deduplicated list of all FX tickers needed (direct + fallback)."""
    tickers = set()
    currencies_needed = set()
    for asset in DR80_ASSETS:
        cur = asset.currency
        currencies_needed.add(cur)
        tickers.add(asset.fx_direct_ticker)

    # Always include USDTHB for fallback calculations
    tickers.add("USDTHB=X")

    # Add fallback USD pairs for non-USD currencies
    for cur in currencies_needed:
        fb = FX_USD_FALLBACK_TICKERS.get(cur)
        if fb:
            tickers.add(fb)

    return list(tickers)


def get_unique_exchanges() -> list[str]:
    """Return a sorted list of unique exchange names."""
    return sorted(set(a.exchange for a in DR80_ASSETS))
