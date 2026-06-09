"""
DR80 Data Fetcher
=================
Handles fetching live stock prices and exchange rates via yfinance,
with FX fallback through USD intermediary for unreliable currency pairs.
Runs in a QThread to keep the UI responsive.
"""

import traceback
from datetime import datetime

import pandas as pd
import yfinance as yf
from PySide6.QtCore import QThread, Signal

from dr80_data import (
    DR80_ASSETS,
    FX_USD_FALLBACK_TICKERS,
    get_all_fx_tickers,
    get_all_underlying_tickers,
)


class DR80FetcherWorker(QThread):
    """
    Background worker that fetches all stock prices and FX rates,
    then computes theoretical DR prices in THB.

    Signals
    -------
    data_ready : pd.DataFrame
        Emitted with the full results table when fetching is complete.
    progress : int
        Emitted with 0-100 progress percentage.
    error : str
        Emitted when a non-fatal error occurs (individual asset failures).
    fatal_error : str
        Emitted when the entire fetch fails.
    fx_rates_ready : dict
        Emitted with {currency: rate_to_thb} for the FX rate ribbon.
    """

    data_ready = Signal(object)       # pd.DataFrame
    progress = Signal(int)
    error = Signal(str)
    fatal_error = Signal(str)
    fx_rates_ready = Signal(object)   # dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        self._is_cancelled = False
        try:
            self._do_fetch()
        except Exception as e:
            self.fatal_error.emit(f"Fatal error: {e}\n{traceback.format_exc()}")

    def _do_fetch(self):
        # ── Step 1: Gather all tickers ──────────────────────────────────
        self.progress.emit(5)
        stock_tickers = get_all_underlying_tickers()
        fx_tickers = get_all_fx_tickers()
        all_tickers = stock_tickers + fx_tickers

        if self._is_cancelled:
            return

        # ── Step 2: Batch download via yfinance ─────────────────────────
        self.progress.emit(10)
        try:
            # Use period="5d" to handle weekends/holidays gracefully
            data = yf.download(
                tickers=all_tickers,
                period="5d",
                group_by="ticker",
                progress=False,
                threads=True,
            )
        except Exception as e:
            self.fatal_error.emit(f"Failed to download data from yfinance: {e}")
            return

        if self._is_cancelled:
            return

        self.progress.emit(50)

        # ── Step 3: Extract last known prices ───────────────────────────
        prices = {}
        for ticker in all_tickers:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    # Multi-ticker download: columns are (Ticker, Field)
                    if ticker in data.columns.get_level_values(0):
                        close_series = data[(ticker, "Close")].dropna()
                        if not close_series.empty:
                            prices[ticker] = float(close_series.iloc[-1])
                else:
                    # Single-ticker download (rare): columns are just fields
                    if "Close" in data.columns:
                        close_series = data["Close"].dropna()
                        if not close_series.empty:
                            prices[ticker] = float(close_series.iloc[-1])
            except (KeyError, TypeError, IndexError):
                pass  # Will be handled as missing price below

        self.progress.emit(65)

        # ── Step 4: Resolve FX rates (with fallback) ────────────────────
        fx_rates = {}  # currency -> rate to THB
        usd_thb = prices.get("USDTHB=X")

        if usd_thb is None:
            self.fatal_error.emit(
                "Critical: Could not fetch USD/THB exchange rate. "
                "Check your internet connection."
            )
            return

        fx_rates["USD"] = usd_thb

        # Resolve other currencies
        for currency, direct_ticker in [
            ("HKD", "HKDTHB=X"),
            ("CNY", "CNYTHB=X"),
            ("JPY", "JPYTHB=X"),
            ("EUR", "EURTHB=X"),
            ("DKK", "DKKTHB=X"),
            ("SGD", "SGDTHB=X"),
        ]:
            direct_rate = prices.get(direct_ticker)
            if direct_rate and direct_rate > 0:
                fx_rates[currency] = direct_rate
            else:
                # Fallback via USD intermediary
                fallback_ticker = FX_USD_FALLBACK_TICKERS.get(currency)
                if fallback_ticker:
                    fallback_rate = prices.get(fallback_ticker)
                    if fallback_rate and fallback_rate > 0:
                        if currency == "EUR":
                            # EURUSD means 1 EUR = X USD, so EUR→THB = EURUSD * USDTHB
                            fx_rates[currency] = fallback_rate * usd_thb
                        else:
                            # USDXXX means 1 USD = X XXX, so XXX→THB = USDTHB / USDXXX
                            fx_rates[currency] = usd_thb / fallback_rate
                    else:
                        self.error.emit(
                            f"Could not resolve FX rate for {currency} "
                            f"(tried {direct_ticker} and {fallback_ticker})"
                        )
                else:
                    self.error.emit(f"No fallback defined for {currency}")

        self.fx_rates_ready.emit(fx_rates)
        self.progress.emit(75)

        if self._is_cancelled:
            return

        # ── Step 5: Calculate theoretical DR prices ─────────────────────
        rows = []
        error_count = 0

        for asset in DR80_ASSETS:
            stock_price = prices.get(asset.underlying_ticker)
            fx_rate = fx_rates.get(asset.currency)

            if stock_price is None:
                self.error.emit(
                    f"{asset.dr_symbol}: Could not fetch price for "
                    f"{asset.underlying_ticker}"
                )
                error_count += 1
                rows.append({
                    "DR Symbol": asset.dr_symbol,
                    "Underlying": asset.underlying_ticker,
                    "Exchange": asset.exchange,
                    "Currency": asset.currency,
                    "Live Price": None,
                    "FX Rate": fx_rate,
                    "Ratio": asset.ratio,
                    "DR Price (THB)": None,
                    "Status": "⚠ No Price",
                })
                continue

            if fx_rate is None:
                error_count += 1
                rows.append({
                    "DR Symbol": asset.dr_symbol,
                    "Underlying": asset.underlying_ticker,
                    "Exchange": asset.exchange,
                    "Currency": asset.currency,
                    "Live Price": stock_price,
                    "FX Rate": None,
                    "Ratio": asset.ratio,
                    "DR Price (THB)": None,
                    "Status": "⚠ No FX",
                })
                continue

            # Theoretical Price = (Stock Price * FX Rate) / Ratio
            dr_price = (stock_price * fx_rate) / asset.ratio

            rows.append({
                "DR Symbol": asset.dr_symbol,
                "Underlying": asset.underlying_ticker,
                "Exchange": asset.exchange,
                "Currency": asset.currency,
                "Live Price": round(stock_price, 4),
                "FX Rate": round(fx_rate, 4),
                "Ratio": asset.ratio,
                "DR Price (THB)": round(dr_price, 2),
                "Status": "✓",
            })

        self.progress.emit(95)

        df = pd.DataFrame(rows)
        self.data_ready.emit(df)
        self.progress.emit(100)

        # Console output
        self._print_console_table(df, fx_rates)

    def _print_console_table(self, df: pd.DataFrame, fx_rates: dict):
        """Print a formatted table to the console."""
        import sys

        print("\n" + "=" * 100)
        print(f"  DR80 Theoretical Price Calculator — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

        # FX rates summary
        print("\n  Exchange Rates to THB:")
        for cur, rate in sorted(fx_rates.items()):
            print(f"    {cur}/THB = {rate:.4f}")
        sys.stdout.flush()

        print("\n" + "-" * 100)
        print(
            f"  {'DR Symbol':<14} {'Underlying':<12} {'Exchange':<18} "
            f"{'Price':>10} {'FX Rate':>10} {'Ratio':>8} {'DR Price (THB)':>15} {'Status':>8}"
        )
        print("-" * 100)

        for _, row in df.iterrows():
            price_str = f"{row['Live Price']:.4f}" if row['Live Price'] is not None else "N/A"
            fx_str = f"{row['FX Rate']:.4f}" if row['FX Rate'] is not None else "N/A"
            dr_str = f"{row['DR Price (THB)']:.2f}" if row['DR Price (THB)'] is not None else "N/A"

            print(
                f"  {row['DR Symbol']:<14} {row['Underlying']:<12} {row['Exchange']:<18} "
                f"{price_str:>10} {fx_str:>10} {row['Ratio']:>8,} {dr_str:>15} {row['Status']:>8}"
            )

        print("=" * 100)
        success = len(df[df["Status"] == "✓"])
        print(f"  Total: {len(df)} assets | Success: {success} | Errors: {len(df) - success}")
        print("=" * 100 + "\n")
        sys.stdout.flush()
