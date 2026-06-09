# DR80 Theoretical Price Calculator

A PySide6-based desktop application that calculates the real-time theoretical prices of Thai DR80 depository receipts issued by Krungthai Bank (KTB). It fetches live stock prices and exchange rates from Yahoo Finance (`yfinance`) and displays the data in a cleanly formatted, sortable table.

## Features
- **Live Data Fetching**: Retrieves real-time stock prices and exchange rates for all 89 DR80 assets across 11 global exchanges.
- **Multi-Currency Support**: Automatically handles FX conversions for USD, HKD, CNY, JPY, EUR, DKK, and SGD to THB, utilizing fallback strategies for less reliable currency pairs.
- **Premium GUI**: Features a dark-themed user interface built with PySide6, complete with an FX rate ribbon, auto-refresh functionality, text search, and exchange-based filtering.
- **Console Output**: Prints a formatted table to the console simultaneously on every data refresh.

## Prerequisites
- Python 3.10 or higher
- Windows OS (for the `run_app.bat` script)

## Installation
1. Ensure Python is installed and added to your system PATH.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Required packages: `PySide6`, `yfinance`, `pandas`)*

## Usage
Launch the application by double-clicking the included batch script:
- **`run_app.bat`**

Alternatively, you can run the Python script directly from your terminal:
```bash
python dr80_calculator.py
```

### UI Controls
- **Refresh Now**: Manually trigger a data fetch.
- **Auto-Refresh**: Toggle automatic data fetching based on the specified interval (default 60 seconds).
- **Search Input**: Filter the table by DR symbol or underlying ticker.
- **Exchange Dropdown**: Filter to view assets from specific exchanges only.
