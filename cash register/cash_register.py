from __future__ import annotations
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import excel_manager
from PySide6.QtCore import QEventLoop, QRegularExpression, QTimer, Qt, Signal
from PySide6.QtGui import QFont, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


# Reusable module-level variable with the last submitted report.
LAST_SUBMISSION: dict[str, Any] | None = None


def parse_money(value: str) -> Decimal:
    text = value.strip().replace(" ", "").replace(",", ".")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"Invalid number: {value!r}") from error


def format_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):,.2f}".replace(",", " ")


def format_money_input_text(raw_text: str) -> str:
    text = raw_text.strip().replace(" ", "").replace(",", ".")
    if not text:
        return ""

    cleaned: list[str] = []
    dot_used = False
    for char in text:
        if char.isdigit():
            cleaned.append(char)
        elif char == "." and not dot_used:
            cleaned.append(char)
            dot_used = True

    normalized = "".join(cleaned)
    if not normalized:
        return ""

    has_decimal_separator = "." in normalized
    if has_decimal_separator:
        whole, fraction = normalized.split(".", 1)
        fraction = "".join(ch for ch in fraction if ch.isdigit())[:2]
    else:
        whole, fraction = normalized, ""

    if whole:
        grouped_whole = f"{int(whole):,}".replace(",", " ")
    else:
        grouped_whole = "0" if fraction else ""

    if fraction:
        return f"{grouped_whole}.{fraction}"
    if has_decimal_separator:
        return f"{grouped_whole}."
    return grouped_whole


def load_cashier_names(file_name: str = "cashiers.txt") -> list[str]:
    file_path = Path(__file__).resolve().parent / file_name
    if not file_path.exists():
        return []

    with file_path.open("r", encoding="utf-8") as stream:
        return [line.strip() for line in stream if line.strip()]


class CashRegisterWindow(QMainWindow):
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Cash Register Report")
        self.setMinimumSize(630, 800)

        self.cashier_names = load_cashier_names()
        self.expenses: list[dict[str, Any]] = []
        self.submitted_data: dict[str, Any] | None = None

        self._build_ui()
        self._setup_clock()
        self.refresh_totals()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f2f5f7;
            }
            QFrame#Card {
                background: #ffffff;
                border: 1px solid #dde5ec;
                border-radius: 14px;
            }
            QLabel#Title {
                color: #0b1f33;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#Clock {
                color: #105f59;
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#Section {
                color: #102a43;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#Value {
                color: #334e68;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#FieldName {
                color: #1f3b4d;
                font-size: 13px;
                font-weight: 700;
            }
            QLineEdit, QPlainTextEdit, QListWidget {
                background: #fcfdff;
                border: 1px solid #cbd6e2;
                border-radius: 10px;
                padding: 7px 9px;
                font-size: 13px;
                color: #102a43;
                selection-background-color: #0f8b8d;
                selection-color: #ffffff;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #11998e;
            }
            QComboBox {
                background: #fcfdff;
                border: 1px solid #cbd6e2;
                border-radius: 10px;
                padding: 7px 9px;
                font-size: 13px;
                color: #102a43;
            }
            QComboBox:focus {
                border: 1px solid #11998e;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #102a43;
                selection-background-color: #0f8b8d;
                selection-color: #ffffff;
                border: 1px solid #cbd6e2;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 8px;
            }
            QListWidget::item:hover {
                background: #e7f4f4;
            }
            QListWidget::item:selected {
                background: #0f8b8d;
                color: #ffffff;
            }
            QListWidget::item:selected:!active {
                background: #3f9ca0;
                color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 10px;
                padding: 9px 14px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#Primary {
                background: #0f8b8d;
                color: #ffffff;
            }
            QPushButton#Primary:disabled {
                background: #b5c6cd;
                color: #eff5f7;
            }
            QPushButton#Secondary {
                background: #e7eef3;
                color: #1f3b4d;
            }
            QPushButton#Danger {
                background: #c44536;
                color: #ffffff;
            }
            QCheckBox {
                color: #1f3b4d;
                font-size: 13px;
                font-weight: 600;
            }
            """
        )

        root_widget = QWidget(self)
        self.setCentralWidget(root_widget)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        header_card = self._card()
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(12, 9, 12, 9)
        title = QLabel("Daily Cash Register", header_card)
        title.setObjectName("Title")
        self.clock_label = QLabel(header_card)
        self.clock_label.setObjectName("Clock")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.clock_label)
        root_layout.addWidget(header_card)

        payment_card = self._card()
        payment_layout = QGridLayout(payment_card)
        payment_layout.setContentsMargins(12, 10, 12, 10)
        payment_layout.setHorizontalSpacing(12)
        payment_layout.setVerticalSpacing(7)

        payment_title = QLabel("Daromad manbalari", payment_card)
        payment_title.setObjectName("Section")
        payment_layout.addWidget(payment_title, 0, 0, 1, 3)

        cashier_label = QLabel("Kassir", payment_card)
        cashier_label.setObjectName("FieldName")
        self.cashier_combo = QComboBox(payment_card)
        if self.cashier_names:
            self.cashier_combo.addItems(self.cashier_names)
        else:
            self.cashier_combo.addItem("Cashier")

        self.humo_input = self._money_input("Summa...")
        self.uzcard_input = self._money_input("Summa...")
        self.naqd_input = self._money_input("Summa...")

        humo_label = QLabel("HUMO", payment_card)
        humo_label.setObjectName("FieldName")
        uzcard_label = QLabel("UZCARD", payment_card)
        uzcard_label.setObjectName("FieldName")
        naqd_label = QLabel("NAQD", payment_card)
        naqd_label.setObjectName("FieldName")

        payment_layout.addWidget(cashier_label, 1, 0)
        payment_layout.addWidget(self.cashier_combo, 1, 1, 1, 2)
        payment_layout.addWidget(humo_label, 2, 0)
        payment_layout.addWidget(uzcard_label, 2, 1)
        payment_layout.addWidget(naqd_label, 2, 2)
        payment_layout.addWidget(self.humo_input, 3, 0)
        payment_layout.addWidget(self.uzcard_input, 3, 1)
        payment_layout.addWidget(self.naqd_input, 3, 2)
        root_layout.addWidget(payment_card)

        expense_card = self._card()
        expense_layout = QVBoxLayout(expense_card)
        expense_layout.setContentsMargins(12, 10, 12, 10)
        expense_layout.setSpacing(8)

        expense_title = QLabel("RASXOD", expense_card)
        expense_title.setObjectName("Section")
        expense_layout.addWidget(expense_title)

        expense_form = QHBoxLayout()
        expense_form.setSpacing(6)
        self.expense_amount_input = self._money_input("Summa...")
        self.expense_reason_input = QLineEdit(expense_card)
        self.expense_reason_input.setPlaceholderText("Nima uchun sarflandi?")
        self.add_expense_button = QPushButton("Qo'shish", expense_card)
        self.add_expense_button.setObjectName("Primary")
        self.remove_expense_button = QPushButton("O'chirish", expense_card)
        self.remove_expense_button.setObjectName("Danger")
        expense_form.addWidget(self.expense_amount_input, 1)
        expense_form.addWidget(self.expense_reason_input, 3)
        expense_form.addWidget(self.add_expense_button)
        expense_form.addWidget(self.remove_expense_button)
        expense_layout.addLayout(expense_form)

        self.expense_list = QListWidget(expense_card)
        expense_layout.addWidget(self.expense_list)

        self.rasxod_total_label = QLabel("Total RASXOD: 0.00", expense_card)
        self.rasxod_total_label.setObjectName("Value")
        expense_layout.addWidget(self.rasxod_total_label)
        root_layout.addWidget(expense_card, 1)

        description_card = self._card()
        description_layout = QVBoxLayout(description_card)
        description_layout.setContentsMargins(12, 10, 12, 10)
        description_layout.setSpacing(6)
        description_title = QLabel("Izoh", description_card)
        description_title.setObjectName("Section")
        self.description_input = QPlainTextEdit(description_card)
        self.description_input.setPlaceholderText("Izoh qoldiring...")
        self.description_input.setFixedHeight(74)
        description_layout.addWidget(description_title)
        description_layout.addWidget(self.description_input)
        root_layout.addWidget(description_card)

        summary_card = self._card()
        summary_layout = QGridLayout(summary_card)
        summary_layout.setContentsMargins(12, 9, 12, 9)
        summary_layout.setHorizontalSpacing(12)

        self.jami_summa_label = QLabel(summary_card)
        self.jami_summa_label.setObjectName("Value")
        summary_layout.addWidget(self.jami_summa_label, 0, 0)
        root_layout.addWidget(summary_card)

        submit_card = self._card()
        submit_layout = QHBoxLayout(submit_card)
        submit_layout.setContentsMargins(12, 9, 12, 9)

        self.confirm_checkbox = QCheckBox(
            "Men bu malumotlar to'g'rligini tasdiqlayman", submit_card
        )
        self.submit_button = QPushButton("Kiritish", submit_card)
        self.submit_button.setObjectName("Primary")
        self.submit_button.setEnabled(False)
        self.cancel_button = QPushButton("Yopish", submit_card)
        self.cancel_button.setObjectName("Secondary")

        submit_layout.addWidget(self.confirm_checkbox)
        submit_layout.addStretch(1)
        submit_layout.addWidget(self.cancel_button)
        submit_layout.addWidget(self.submit_button)
        root_layout.addWidget(submit_card)

        for field in (self.humo_input, self.uzcard_input, self.naqd_input):
            field.textChanged.connect(self.refresh_totals)
            field.textChanged.connect(self._on_required_fields_changed)

        for field in (
            self.humo_input,
            self.uzcard_input,
            self.naqd_input,
            self.expense_amount_input,
        ):
            field.textEdited.connect(
                lambda _text, current_field=field: self._format_money_field(current_field)
            )

        self.add_expense_button.clicked.connect(self.add_expense)
        self.remove_expense_button.clicked.connect(self.remove_selected_expense)
        self.cashier_combo.currentTextChanged.connect(self._on_required_fields_changed)
        self.confirm_checkbox.clicked.connect(self.on_confirm_checkbox_clicked)
        self.submit_button.clicked.connect(self.submit_report)
        self.cancel_button.clicked.connect(self.close)
        self._on_required_fields_changed()

    def _setup_clock(self) -> None:
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self.update_clock)
        self._clock_timer.start(1000)
        self.update_clock()

    def _card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("Card")
        return card

    def _money_input(self, placeholder: str) -> QLineEdit:
        money_input = QLineEdit(self)
        money_input.setPlaceholderText(placeholder)
        money_input.setClearButtonEnabled(True)
        money_input.setFont(QFont("Trebuchet MS", 10))
        validator = QRegularExpressionValidator(
            QRegularExpression(r"^[\d\s]*([.,]\d{0,2})?$"), self
        )
        money_input.setValidator(validator)
        return money_input

    def _format_money_field(self, field: QLineEdit) -> None:
        formatted = format_money_input_text(field.text())
        if formatted == field.text():
            return

        field.blockSignals(True)
        field.setText(formatted)
        field.blockSignals(False)
        field.setCursorPosition(len(formatted))

    def _missing_required_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.cashier_combo.currentText().strip():
            missing.append("Kassir")
        if not self.humo_input.text().strip():
            missing.append("HUMO")
        if not self.uzcard_input.text().strip():
            missing.append("UZCARD")
        if not self.naqd_input.text().strip():
            missing.append("NAQD")
        return missing

    def _is_required_data_filled(self) -> bool:
        return not self._missing_required_fields()

    def _on_required_fields_changed(self) -> None:
        valid = self._is_required_data_filled()
        if self.confirm_checkbox.isChecked() and not valid:
            self.confirm_checkbox.blockSignals(True)
            self.confirm_checkbox.setChecked(False)
            self.confirm_checkbox.blockSignals(False)
        self.submit_button.setEnabled(self.confirm_checkbox.isChecked() and valid)

    def on_confirm_checkbox_clicked(self, checked: bool) -> None:
        if not checked:
            self.submit_button.setEnabled(False)
            return

        missing_fields = self._missing_required_fields()
        if missing_fields:
            self.confirm_checkbox.blockSignals(True)
            self.confirm_checkbox.setChecked(False)
            self.confirm_checkbox.blockSignals(False)
            self.submit_button.setEnabled(False)
            QMessageBox.information(
                self,
                "Majburiy maydonlar",
                "Avval quyidagi maydonlarni to'ldiring:\n- "
                + "\n- ".join(missing_fields),
            )
            return

        self.submit_button.setEnabled(True)

    def update_clock(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

    def get_money_value(self, field: QLineEdit) -> Decimal:
        return parse_money(field.text())

    def add_expense(self) -> None:
        try:
            amount = self.get_money_value(self.expense_amount_input)
        except ValueError:
            QMessageBox.warning(self, "Invalid Amount", "Malumotni tekshirib qaytadan kiriting.")
            return

        reason = self.expense_reason_input.text().strip()
        if amount <= 0:
            QMessageBox.warning(
                self, "Invalid Amount", "Malumotni tekshirib qaytadan kiriting."
            )
            return
        if not reason:
            QMessageBox.warning(
                self, "Missing Description", "Izoh qoldiring."
            )
            return

        entry = {"reason": reason, "amount": amount}
        self.expenses.append(entry)
        self.expense_list.addItem(
            f"{len(self.expenses):02d}. {reason}   |   {format_money(amount)}"
        )
        self.expense_amount_input.clear()
        self.expense_reason_input.clear()
        self.refresh_totals()

    def remove_selected_expense(self) -> None:
        selected_row = self.expense_list.currentRow()
        if selected_row < 0:
            QMessageBox.information(
                self,
                "Select Expense",
                "Malumotni o'chirish uchun ro'yxatdan biror narsani tanlang.",
            )
            return

        self.expense_list.takeItem(selected_row)
        del self.expenses[selected_row]

        # Rebuild labels to keep numbering consistent.
        self.expense_list.clear()
        for index, entry in enumerate(self.expenses, start=1):
            self.expense_list.addItem(
                f"{index:02d}. {entry['reason']}   |   {format_money(entry['amount'])}"
            )
        self.refresh_totals()

    def refresh_totals(self) -> None:
        expenses_total = sum(
            (entry["amount"] for entry in self.expenses), start=Decimal("0")
        )
        income_total = Decimal("0")
        for field in (self.humo_input, self.uzcard_input, self.naqd_input):
            try:
                income_total += self.get_money_value(field)
            except ValueError:
                pass

        self.rasxod_total_label.setText(f"Jami Rasxot: {format_money(expenses_total)}")
        self.jami_summa_label.setText(f"Jami Summa: {format_money(income_total)}")

    def build_submission_payload(self) -> dict[str, Any]:
        humo = self.get_money_value(self.humo_input)
        uzcard = self.get_money_value(self.uzcard_input)
        naqd = self.get_money_value(self.naqd_input)
        rasxod_total = sum(
            (entry["amount"] for entry in self.expenses), start=Decimal("0")
        )

        return {
            "submitted_at_local": datetime.now().isoformat(timespec="seconds"),
            "cashier": self.cashier_combo.currentText().strip(),
            "humo": float(humo),
            "uzcard": float(uzcard),
            "naqd": float(naqd),
            "rasxod_items": [
                {"reason": entry["reason"], "amount": float(entry["amount"])}
                for entry in self.expenses
            ],
            "rasxod_total": float(rasxod_total),
            "description": self.description_input.toPlainText().strip(),
        }

    def submit_report(self) -> None:
        try:
            submission = self.build_submission_payload()
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Malumotlarni tekshirib qaytadan kiriting.",
            )
            return

        try:
            excel_manager.append_to_excel(submission)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Excel Error",
                f"Ma'lumotlarni Excelga yozishda xatolik:\n{e}",
            )
            return

        global LAST_SUBMISSION
        LAST_SUBMISSION = submission
        self.submitted_data = submission
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closed.emit()
        super().closeEvent(event)


def run_cash_register_app() -> dict[str, Any] | None:
    """
    Reusable function: opens the cash register form and returns submitted data.
    Returns `None` when the window is closed without pressing Submit.
    """
    app = QApplication.instance()
    created_app = app is None
    if created_app:
        app = QApplication(sys.argv)

    window = CashRegisterWindow()
    window.show()

    if created_app:
        app.exec()
    else:
        loop = QEventLoop()
        window.closed.connect(loop.quit)
        loop.exec()

    return window.submitted_data


if __name__ == "__main__":
    result = run_cash_register_app()
    if result is not None:
        print("Submitted data:", result)
