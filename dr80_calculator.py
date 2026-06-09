"""
DR80 Theoretical Price Calculator
==================================
Main entry point for the PySide6 desktop application.

Calculates real-time theoretical prices for Thai DR80 depository receipts
issued by Krungthai Bank, using live market data from yfinance.

Usage:
    python dr80_calculator.py
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from dr80_ui import DR80MainWindow


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("DR80 Calculator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AntiGravity")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create and show main window
    window = DR80MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
