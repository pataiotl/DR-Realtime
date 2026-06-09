"""
DR80 PySide6 GUI
================
Premium dark-themed desktop application for real-time DR80 theoretical
price calculations. Features a sortable/filterable table, FX rate ribbon,
auto-refresh, and exchange-based color coding.
"""

from datetime import datetime

import pandas as pd
from PySide6.QtCore import (
    QAbstractTableModel,
    QSortFilterProxyModel,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from dr80_data import get_unique_exchanges
from dr80_fetcher import DR80FetcherWorker


# ═══════════════════════════════════════════════════════════════════════════
# Color palette
# ═══════════════════════════════════════════════════════════════════════════
COLORS = {
    "bg_primary":       "#0a0e17",
    "bg_secondary":     "#111827",
    "bg_card":          "#1a2235",
    "bg_card_hover":    "#1f2a40",
    "bg_input":         "#0f1629",
    "border":           "#2a3550",
    "border_focus":     "#4f8aff",
    "text_primary":     "#e8ecf4",
    "text_secondary":   "#8899b8",
    "text_muted":       "#5a6a85",
    "accent_blue":      "#4f8aff",
    "accent_cyan":      "#00d4ff",
    "accent_green":     "#00e09e",
    "accent_amber":     "#ffb347",
    "accent_red":       "#ff5c6c",
    "accent_purple":    "#a78bfa",
    "gradient_start":   "#4f8aff",
    "gradient_end":     "#00d4ff",
}

# Exchange → accent color for row tinting
EXCHANGE_COLORS = {
    "NASDAQ":            QColor("#4f8aff"),
    "NYSE":              QColor("#00e09e"),
    "NYSE Arca":         QColor("#00d4ff"),
    "HKEX":              QColor("#ff5c6c"),
    "Shanghai":          QColor("#ffb347"),
    "Shenzhen":          QColor("#ffb347"),
    "TYO":               QColor("#f472b6"),
    "Euronext Paris":    QColor("#a78bfa"),
    "Euronext Milan":    QColor("#a78bfa"),
    "Nasdaq Copenhagen": QColor("#34d399"),
    "SGX":               QColor("#fbbf24"),
}


# ═══════════════════════════════════════════════════════════════════════════
# Table Model
# ═══════════════════════════════════════════════════════════════════════════
class DR80TableModel(QAbstractTableModel):
    """Custom model to display DR80 data in a QTableView."""

    COLUMNS = [
        "DR Symbol", "Underlying", "Exchange", "Currency",
        "Live Price", "FX Rate", "Ratio", "DR Price (THB)", "Status"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: pd.DataFrame = pd.DataFrame(columns=self.COLUMNS)

    def update_data(self, df: pd.DataFrame):
        self.beginResetModel()
        self._data = df.reset_index(drop=True)
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        col_name = self.COLUMNS[col]
        value = self._data.iloc[row][col_name]

        if role == Qt.DisplayRole:
            if value is None:
                return "—"
            if col_name == "Live Price":
                return f"{value:,.4f}"
            if col_name == "FX Rate":
                return f"{value:,.4f}"
            if col_name == "DR Price (THB)":
                return f"{value:,.2f}"
            if col_name == "Ratio":
                return f"1:{value:,}"
            return str(value)

        if role == Qt.TextAlignmentRole:
            if col_name in ("Live Price", "FX Rate", "Ratio", "DR Price (THB)"):
                return Qt.AlignRight | Qt.AlignVCenter
            if col_name == "Status":
                return Qt.AlignCenter | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.ForegroundRole:
            if col_name == "DR Price (THB)" and value is not None:
                return QBrush(QColor(COLORS["accent_cyan"]))
            if col_name == "Status":
                if value == "✓":
                    return QBrush(QColor(COLORS["accent_green"]))
                else:
                    return QBrush(QColor(COLORS["accent_red"]))
            if col_name == "DR Symbol":
                return QBrush(QColor(COLORS["text_primary"]))
            return QBrush(QColor(COLORS["text_secondary"]))

        if role == Qt.BackgroundRole:
            exchange = self._data.iloc[row].get("Exchange", "")
            color = EXCHANGE_COLORS.get(exchange, QColor("#1a2235"))
            # Very subtle tint
            bg = QColor(COLORS["bg_card"])
            tinted = QColor(
                min(255, bg.red() + color.red() // 15),
                min(255, bg.green() + color.green() // 15),
                min(255, bg.blue() + color.blue() // 15),
            )
            if row % 2 == 0:
                return QBrush(tinted)
            else:
                return QBrush(tinted.darker(110))

        if role == Qt.FontRole:
            if col_name in ("DR Symbol", "DR Price (THB)"):
                f = QFont("Segoe UI", 10)
                f.setBold(True)
                return f

        # Sort role — return raw values for proper sorting
        if role == Qt.UserRole:
            if value is None:
                return float('-inf')
            return value

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Sort/Filter Proxy
# ═══════════════════════════════════════════════════════════════════════════
class DR80FilterProxy(QSortFilterProxyModel):
    """Proxy model with text search and exchange filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._exchange_filter = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortRole(Qt.UserRole)

    def set_exchange_filter(self, exchange: str):
        self._exchange_filter = exchange
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        # Text search on DR Symbol and Underlying
        search_text = self.filterRegularExpression().pattern()
        if search_text:
            dr_sym = str(model.data(model.index(source_row, 0), Qt.DisplayRole) or "")
            underlying = str(model.data(model.index(source_row, 1), Qt.DisplayRole) or "")
            if (search_text.lower() not in dr_sym.lower()
                    and search_text.lower() not in underlying.lower()):
                return False

        # Exchange filter
        if self._exchange_filter:
            exchange = str(model.data(model.index(source_row, 2), Qt.DisplayRole) or "")
            if exchange != self._exchange_filter:
                return False

        return True


# ═══════════════════════════════════════════════════════════════════════════
# FX Rate Badge Widget
# ═══════════════════════════════════════════════════════════════════════════
class FXBadge(QFrame):
    """Small badge displaying a single FX rate."""

    def __init__(self, currency: str, parent=None):
        super().__init__(parent)
        self.currency = currency
        self.setObjectName("fxBadge")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(1)

        self.label_name = QLabel(f"{currency}/THB")
        self.label_name.setObjectName("fxBadgeName")
        self.label_name.setAlignment(Qt.AlignCenter)

        self.label_rate = QLabel("—")
        self.label_rate.setObjectName("fxBadgeRate")
        self.label_rate.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label_name)
        layout.addWidget(self.label_rate)

    def set_rate(self, rate: float):
        self.label_rate.setText(f"{rate:.4f}")


# ═══════════════════════════════════════════════════════════════════════════
# Main Window
# ═══════════════════════════════════════════════════════════════════════════
class DR80MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DR80 Theoretical Price Calculator")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        self._worker: DR80FetcherWorker | None = None
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._on_refresh)
        self._error_log: list[str] = []

        self._setup_ui()
        self._apply_stylesheet()

        # Initial fetch on launch
        QTimer.singleShot(300, self._on_refresh)

    # ── UI Construction ─────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 16, 20, 12)
        main_layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 12)
        header_layout.setSpacing(4)

        title = QLabel("DR80 Theoretical Price Calculator")
        title.setObjectName("headerTitle")
        header_layout.addWidget(title)

        subtitle = QLabel("Real-time theoretical prices for Krungthai Bank DR80 depository receipts")
        subtitle.setObjectName("headerSubtitle")
        header_layout.addWidget(subtitle)

        main_layout.addWidget(header)

        # ── FX Rate Ribbon ──────────────────────────────────────────────
        fx_frame = QFrame()
        fx_frame.setObjectName("fxRibbon")
        fx_layout = QHBoxLayout(fx_frame)
        fx_layout.setContentsMargins(12, 8, 12, 8)
        fx_layout.setSpacing(8)

        fx_label = QLabel("FX Rates ›")
        fx_label.setObjectName("fxRibbonLabel")
        fx_layout.addWidget(fx_label)

        self._fx_badges: dict[str, FXBadge] = {}
        for cur in ["USD", "HKD", "CNY", "JPY", "EUR", "DKK", "SGD"]:
            badge = FXBadge(cur)
            self._fx_badges[cur] = badge
            fx_layout.addWidget(badge)

        fx_layout.addStretch()

        self._last_update_label = QLabel("Last update: —")
        self._last_update_label.setObjectName("lastUpdate")
        fx_layout.addWidget(self._last_update_label)

        main_layout.addWidget(fx_frame)

        # ── Controls Bar ────────────────────────────────────────────────
        controls = QFrame()
        controls.setObjectName("controlsBar")
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)
        ctrl_layout.setSpacing(12)

        # Search
        search_icon = QLabel("🔍")
        ctrl_layout.addWidget(search_icon)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("searchInput")
        self._search_input.setPlaceholderText("Search DR symbol or ticker...")
        self._search_input.setMinimumWidth(220)
        self._search_input.textChanged.connect(self._on_search)
        ctrl_layout.addWidget(self._search_input)

        # Exchange filter
        ctrl_layout.addWidget(QLabel("Exchange:"))
        self._exchange_combo = QComboBox()
        self._exchange_combo.setObjectName("exchangeCombo")
        self._exchange_combo.addItem("All Exchanges", "")
        for ex in get_unique_exchanges():
            self._exchange_combo.addItem(ex, ex)
        self._exchange_combo.currentIndexChanged.connect(self._on_exchange_filter)
        self._exchange_combo.setMinimumWidth(160)
        ctrl_layout.addWidget(self._exchange_combo)

        ctrl_layout.addStretch()

        # Auto-refresh
        self._auto_check = QPushButton("Auto-Refresh: OFF")
        self._auto_check.setObjectName("autoRefreshBtn")
        self._auto_check.setCheckable(True)
        self._auto_check.clicked.connect(self._on_auto_toggle)
        ctrl_layout.addWidget(self._auto_check)

        ctrl_layout.addWidget(QLabel("Interval (s):"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setObjectName("intervalSpin")
        self._interval_spin.setRange(30, 600)
        self._interval_spin.setValue(60)
        self._interval_spin.setSuffix("s")
        ctrl_layout.addWidget(self._interval_spin)

        # Refresh button
        self._refresh_btn = QPushButton("⟳  Refresh Now")
        self._refresh_btn.setObjectName("refreshBtn")
        self._refresh_btn.clicked.connect(self._on_refresh)
        ctrl_layout.addWidget(self._refresh_btn)

        main_layout.addWidget(controls)

        # ── Progress Bar ────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setObjectName("progressBar")
        self._progress.setMaximum(100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setMaximumHeight(3)
        self._progress.hide()
        main_layout.addWidget(self._progress)

        # ── Table ───────────────────────────────────────────────────────
        self._table_model = DR80TableModel()
        self._proxy_model = DR80FilterProxy()
        self._proxy_model.setSourceModel(self._table_model)

        self._table = QTableView()
        self._table.setObjectName("drTable")
        self._table.setModel(self._proxy_model)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(False)  # We handle this in the model
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setDefaultSectionSize(34)

        # Column sizing
        header_view = self._table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # DR Symbol
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Underlying
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)          # Exchange
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Currency
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Live Price
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # FX Rate
        header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Ratio
        header_view.setSectionResizeMode(7, QHeaderView.Stretch)          # DR Price (THB)
        header_view.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Status

        main_layout.addWidget(self._table, stretch=1)

        # ── Status Bar ──────────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label, 1)
        self._count_label = QLabel("")
        self._status_bar.addPermanentWidget(self._count_label)

    # ── Event Handlers ──────────────────────────────────────────────────
    def _on_refresh(self):
        if self._worker and self._worker.isRunning():
            return  # Already fetching

        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("⏳  Fetching...")
        self._progress.show()
        self._progress.setValue(0)
        self._status_label.setText("Fetching data from yfinance...")
        self._error_log.clear()

        self._worker = DR80FetcherWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.fx_rates_ready.connect(self._on_fx_rates)
        self._worker.error.connect(self._on_error)
        self._worker.fatal_error.connect(self._on_fatal_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_progress(self, value: int):
        self._progress.setValue(value)

    def _on_data_ready(self, df: pd.DataFrame):
        self._table_model.update_data(df)
        success = len(df[df["Status"] == "✓"])
        total = len(df)
        self._count_label.setText(f"  {success}/{total} assets loaded  ")
        self._last_update_label.setText(
            f"Last update: {datetime.now().strftime('%H:%M:%S')}"
        )

        if self._error_log:
            self._status_label.setText(
                f"✓ Updated with {len(self._error_log)} warning(s)"
            )
        else:
            self._status_label.setText("✓ All data fetched successfully")

    def _on_fx_rates(self, rates: dict):
        for cur, badge in self._fx_badges.items():
            if cur in rates:
                badge.set_rate(rates[cur])

    def _on_error(self, msg: str):
        self._error_log.append(msg)

    def _on_fatal_error(self, msg: str):
        self._status_label.setText(f"✗ Error: {msg}")
        self._progress.hide()
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("⟳  Refresh Now")

    def _on_worker_done(self):
        self._progress.hide()
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("⟳  Refresh Now")

    def _on_search(self, text: str):
        self._proxy_model.setFilterFixedString(text)

    def _on_exchange_filter(self, index: int):
        exchange = self._exchange_combo.currentData()
        self._proxy_model.set_exchange_filter(exchange)

    def _on_auto_toggle(self, checked: bool):
        if checked:
            interval_ms = self._interval_spin.value() * 1000
            self._auto_timer.start(interval_ms)
            self._auto_check.setText("Auto-Refresh: ON")
            self._auto_check.setObjectName("autoRefreshBtnOn")
        else:
            self._auto_timer.stop()
            self._auto_check.setText("Auto-Refresh: OFF")
            self._auto_check.setObjectName("autoRefreshBtn")
        # Re-apply style for the toggled state
        self._auto_check.style().unpolish(self._auto_check)
        self._auto_check.style().polish(self._auto_check)

    # ── Stylesheet ──────────────────────────────────────────────────────
    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            /* ── Global ──────────────────────────────────────────── */
            QMainWindow {{
                background-color: {COLORS['bg_primary']};
            }}
            QWidget {{
                color: {COLORS['text_primary']};
                font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
                font-size: 13px;
            }}
            QLabel {{
                color: {COLORS['text_secondary']};
            }}

            /* ── Header ─────────────────────────────────────────── */
            #header {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['bg_card']},
                    stop:1 #1a2845
                );
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            #headerTitle {{
                color: {COLORS['text_primary']};
                font-size: 22px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            #headerSubtitle {{
                color: {COLORS['text_muted']};
                font-size: 13px;
                font-weight: 400;
            }}

            /* ── FX Ribbon ───────────────────────────────────────── */
            #fxRibbon {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            #fxRibbonLabel {{
                color: {COLORS['accent_blue']};
                font-weight: 600;
                font-size: 13px;
            }}
            #fxBadge {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                min-width: 80px;
            }}
            #fxBadge:hover {{
                border-color: {COLORS['accent_blue']};
                background-color: {COLORS['bg_card_hover']};
            }}
            #fxBadgeName {{
                color: {COLORS['text_muted']};
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            #fxBadgeRate {{
                color: {COLORS['accent_cyan']};
                font-size: 13px;
                font-weight: 700;
            }}
            #lastUpdate {{
                color: {COLORS['text_muted']};
                font-size: 11px;
            }}

            /* ── Controls Bar ────────────────────────────────────── */
            #controlsBar {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            #searchInput {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            #searchInput:focus {{
                border-color: {COLORS['border_focus']};
            }}
            #exchangeCombo {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 10px;
                color: {COLORS['text_primary']};
                min-height: 28px;
            }}
            #exchangeCombo::drop-down {{
                border: none;
                width: 24px;
            }}
            #exchangeCombo QAbstractItemView {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['accent_blue']};
            }}
            #intervalSpin {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                color: {COLORS['text_primary']};
                min-width: 70px;
            }}

            /* ── Buttons ─────────────────────────────────────────── */
            #refreshBtn {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['gradient_start']},
                    stop:1 {COLORS['gradient_end']}
                );
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            #refreshBtn:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a9fff,
                    stop:1 #33dfff
                );
            }}
            #refreshBtn:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
            #autoRefreshBtn {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }}
            #autoRefreshBtn:hover {{
                border-color: {COLORS['accent_blue']};
            }}
            #autoRefreshBtnOn {{
                background-color: rgba(79, 138, 255, 0.15);
                color: {COLORS['accent_blue']};
                border: 1px solid {COLORS['accent_blue']};
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }}

            /* ── Progress Bar ────────────────────────────────────── */
            #progressBar {{
                background-color: {COLORS['bg_secondary']};
                border: none;
                border-radius: 2px;
            }}
            #progressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['gradient_start']},
                    stop:1 {COLORS['gradient_end']}
                );
                border-radius: 2px;
            }}

            /* ── Table ───────────────────────────────────────────── */
            #drTable {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: transparent;
            }}
            #drTable::item {{
                padding: 4px 10px;
                border-bottom: 1px solid rgba(42, 53, 80, 0.5);
            }}
            #drTable::item:selected {{
                background-color: rgba(79, 138, 255, 0.15);
                color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_muted']};
                border: none;
                border-bottom: 2px solid {COLORS['border']};
                padding: 8px 10px;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QHeaderView::section:hover {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_card']};
            }}

            /* ── Status Bar ──────────────────────────────────────── */
            QStatusBar {{
                background-color: {COLORS['bg_secondary']};
                border-top: 1px solid {COLORS['border']};
                color: {COLORS['text_muted']};
                font-size: 12px;
            }}

            /* ── Scrollbar ───────────────────────────────────────── */
            QScrollBar:vertical {{
                background-color: {COLORS['bg_primary']};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent_blue']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {COLORS['bg_primary']};
                height: 8px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {COLORS['border']};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {COLORS['accent_blue']};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
