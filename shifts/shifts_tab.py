# shifts/shifts_tab.py
import os
import json
import uuid
from datetime import datetime
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QMessageBox, QMenu,
    QHBoxLayout, QInputDialog, QShortcut, QSplitter, QLineEdit, QFileDialog
)
from PyQt5.QtGui import QFont, QKeySequence, QTextCursor, QTextCharFormat, QTextDocument
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.Qt import QApplication

from shifts.shift_report import generate_shift_report
from shifts.shift_details_dialog import show_shift_details_dialog
from config.paths import PATHS
from utils.logger import logger
from config.settings import settings


class ShiftsTab(QWidget):
    AUTO_SAVE_INTERVAL_MS = settings.AUTO_SAVE_INTERVAL

    KEYWORD_PATTERNS = [
        r"тревог", r"тревога", r"трев",
        r"демонт", r"демонтаж",
        r"выезд",
        r"рф", r"границ", r"граница",
        r"казахстан", r"грузия", r"азербайджан", r"турция",
        r"нет\s*связ",
        r"полиция",
        r"рг",
        r"изъят", r"изъятие",
        r"договор",
        r"наруш"
    ]

    def __init__(self, alarm_manager=None, on_shift_started=None):
        super().__init__()
        self.alarm_manager = alarm_manager
        self.on_shift_started = on_shift_started
        self.data_file = PATHS["shifts"]
        self.shifts = self.load_shifts()
        self.active_shift = self.get_active_shift()
        self.current_shift_id = self.active_shift["id"] if self.active_shift else None

        self._editor_dirty = False
        self._last_saved_text = ""
        self._last_save_time = None

        layout = QVBoxLayout()

        self.status_label = QLabel()
        self.status_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.status_label)

        btns = QHBoxLayout()
        self.start_button = QPushButton("▶️ Начать смену")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.start_button.clicked.connect(self.start_shift)
        btns.addWidget(self.start_button)

        self.end_button = QPushButton("⏹️ Завершить смену")
        self.end_button.setStyleSheet("background-color: #e53935; color: white;")
        self.end_button.clicked.connect(self.end_shift)
        btns.addWidget(self.end_button)
        self.end_button.setEnabled(bool(self.active_shift))

        layout.addLayout(btns)

        splitter = QSplitter(Qt.Vertical)

        journal_container = QVBoxLayout()
        journal_container.addWidget(QLabel("🗒️ Журнал смены:"))
        
        self.journal_editor = QTextEdit()
        self.journal_editor.setFont(QFont("Arial", 11))
        self.journal_editor.setPlaceholderText("Ведите журнал смены. Автосохранение каждые 30 сек. Ctrl+S — сохранить вручную.")
        self.journal_editor.textChanged.connect(self.on_editor_text_changed)
        
        journal_controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по журналу (Enter)")
        self.search_input.returnPressed.connect(self.search_in_journal)
        journal_controls.addWidget(self.search_input)

        self.search_btn = QPushButton("🔍 Найти")
        self.search_btn.clicked.connect(self.search_in_journal)
        journal_controls.addWidget(self.search_btn)

        self.copy_btn = QPushButton("📋 Копировать")
        self.copy_btn.clicked.connect(self.copy_journal_text)
        journal_controls.addWidget(self.copy_btn)

        self.export_txt_btn = QPushButton("TXT")
        self.export_txt_btn.clicked.connect(self.export_txt)
        journal_controls.addWidget(self.export_txt_btn)

        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        journal_controls.addWidget(self.export_pdf_btn)

        journal_container.addWidget(self.journal_editor)
        journal_container.addLayout(journal_controls)

        journal_widget = QWidget()
        journal_widget.setLayout(journal_container)

        history_container = QVBoxLayout()
        history_container.addWidget(QLabel("📜 История смен:"))
        
        self.shift_list = QListWidget()
        self.shift_list.itemDoubleClicked.connect(self.show_shift_report)
        self.shift_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.shift_list.customContextMenuRequested.connect(self.show_context_menu)
        history_container.addWidget(self.shift_list)

        history_widget = QWidget()
        history_widget.setLayout(history_container)

        splitter.addWidget(journal_widget)
        splitter.addWidget(history_widget)
        splitter.setSizes([400, 200])

        layout.addWidget(splitter)

        self.save_status = QLabel("")
        self.save_status.setStyleSheet("color: green; font-size: 10pt;")
        layout.addWidget(self.save_status)

        self._clear_status_timer = QTimer(self)
        self._clear_status_timer.setSingleShot(True)
        self._clear_status_timer.timeout.connect(lambda: self.save_status.setText(""))

        self.setLayout(layout)
        self.refresh_ui()

        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self.save_journal_text)

        QApplication.instance().installEventFilter(self)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(self.AUTO_SAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._autosave_if_needed)
        self._autosave_timer.start()

        self.load_active_journal_text()

    def load_shifts(self):
        if not os.path.exists(self.data_file):
            return []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                shifts = json.load(f)
            for s in shifts:
                if "journal_text" not in s:
                    s["journal_text"] = ""
                if "comment" not in s:
                    s["comment"] = ""
            return shifts
        except Exception as e:
            logger.error(f"Ошибка загрузки смен: {e}")
            return []

    def save_shifts(self):
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.shifts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения смен: {e}")

    def get_active_shift(self):
        for s in self.shifts:
            if not s.get("ended_at"):
                return s
        return None

    def refresh_ui(self):
        if self.active_shift:
            self.status_label.setText(f"✅ Активная смена с {self.active_shift.get('started_at')}")
        else:
            self.status_label.setText("❌ Нет активной смены")
        self.shift_list.clear()
        for s in sorted(self.shifts, key=lambda x: x.get("started_at", ""), reverse=True):
            item_text = f"{s.get('started_at')} → {s.get('ended_at','в процессе')}"
            if s.get("comment"):
                item_text += "  ✎"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, s)
            self.shift_list.addItem(item)

    def start_shift(self):
        if self.active_shift:
            QMessageBox.warning(self, "Ошибка", "Смена уже идёт.")
            return
        new_shift = {
            "id": str(uuid.uuid4()),
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": None,
            "journal_text": "",
            "comment": ""
        }
        self.shifts.append(new_shift)
        self.active_shift = new_shift
        self.current_shift_id = new_shift["id"]
        self.save_shifts()
        self.refresh_ui()
        self.journal_editor.clear()
        if self.on_shift_started:
            self.on_shift_started()
        logger.info(f"Смена начата: {new_shift['id']}")

    def end_shift(self):
        if not self.active_shift:
            return
        self.active_shift["ended_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_shifts()
        self.active_shift = None
        self.current_shift_id = None
        self.refresh_ui()
        self.journal_editor.clear()
        logger.info(f"Смена завершена")

    def show_shift_report(self, item):
        shift = item.data(Qt.UserRole)
        if not shift:
            return
        generate_shift_report(shift, self.alarm_manager)

    def show_context_menu(self, pos: QPoint):
        item = self.shift_list.itemAt(pos)
        if not item:
            return
        shift = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("💬 Оставить комментарий", lambda: self.add_comment(shift))
        menu.addAction("🔍 Посмотреть подробности", lambda: self.show_shift_details(shift))
        menu.exec_(self.shift_list.mapToGlobal(pos))

    def add_comment(self, shift):
        comment_text, ok = QInputDialog.getMultiLineText(
            self, "Комментарий к смене", "Введите комментарий:", text=shift.get("comment", "")
        )
        if not ok:
            return
        found = False
        shift_id = shift.get("id")
        if shift_id:
            for s in self.shifts:
                if s.get("id") == shift_id:
                    s["comment"] = comment_text
                    found = True
                    break
        if not found:
            shift["comment"] = comment_text
        self.save_shifts()
        self.refresh_ui()
        logger.info(f"Комментарий к смене {shift_id} обновлён")
        QMessageBox.information(self, "✅ Сохранено", "Комментарий сохранён.")

    def show_shift_details(self, shift):
        fresh = next((s for s in self.shifts if s.get("id") == shift.get("id")), shift)
        show_shift_details_dialog(fresh, self.alarm_manager, self)

    def load_active_journal_text(self):
        if not self.active_shift:
            self.journal_editor.clear()
            return
        text = self.active_shift.get("journal_text", "")
        self.journal_editor.setPlainText(text)

    def on_editor_text_changed(self):
        self._editor_dirty = True

    def save_journal_text(self):
        if not self.active_shift:
            return
        txt = self.journal_editor.toPlainText()
        shift_id = self.active_shift.get("id") if self.active_shift else None
        if shift_id:
            for s in self.shifts:
                if s.get("id") == shift_id:
                    s["journal_text"] = txt
                    break
        else:
            self.active_shift["journal_text"] = txt

        self.save_shifts()
        self._editor_dirty = False
        self._last_saved_text = txt
        self._last_save_time = datetime.now()

        self.save_status.setText(f"✅ Сохранено: {self._last_save_time.strftime('%H:%M:%S')}")
        self._clear_status_timer.start(3000)

        self.highlight_keywords()

    def _autosave_if_needed(self):
        if self._editor_dirty:
            self.save_journal_text()

    def highlight_keywords(self):
        doc = self.journal_editor.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()

        plain = self.journal_editor.toPlainText()
        if not plain:
            return
        joined = "(" + "|".join(self.KEYWORD_PATTERNS) + ")"
        try:
            pattern = re.compile(joined, re.IGNORECASE | re.UNICODE)
        except re.error:
            return
        for match in pattern.finditer(plain):
            start, end = match.span()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setFontWeight(700)
            fmt.setBackground(Qt.yellow)
            cursor.mergeCharFormat(fmt)
            cursor.clearSelection()

    def search_in_journal(self):
        query = self.search_input.text().strip().lower()
        if not query:
            return
        text = self.journal_editor.toPlainText().lower()
        idx = text.find(query)
        if idx == -1:
            QMessageBox.information(self, "Поиск", "Совпадений не найдено.")
            return
        cursor = self.journal_editor.textCursor()
        cursor.setPosition(idx)
        cursor.setPosition(idx + len(query), QTextCursor.KeepAnchor)
        self.journal_editor.setTextCursor(cursor)
        self.journal_editor.setFocus()

    def copy_journal_text(self):
        text = self.journal_editor.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

    def export_txt(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Сохранить журнал как TXT", "", "Текстовый файл (*.txt)")
        if not fname:
            return
        if not fname.lower().endswith(".txt"):
            fname += ".txt"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(self.journal_editor.toPlainText())
            QMessageBox.information(self, "Экспорт", "Экспорт в TXT выполнен.")
        except Exception as ex:
            logger.error(f"Ошибка экспорта TXT: {ex}")
            QMessageBox.warning(self, "Ошибка", str(ex))

    def export_pdf(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Сохранить журнал как PDF", "", "PDF файл (*.pdf)")
        if not fname:
            return
        if not fname.lower().endswith(".pdf"):
            fname += ".pdf"
        try:
            doc = QTextDocument()
            html = "<pre style='font-family:monospace; white-space:pre-wrap'>{}</pre>".format(
                self.journal_editor.toPlainText()
            )
            doc.setHtml(html)
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(fname)
            doc.print_(printer)
            QMessageBox.information(self, "Экспорт", "Экспорт в PDF выполнен.")
        except Exception as ex:
            logger.error(f"Ошибка экспорта PDF: {ex}")
            QMessageBox.warning(self, "Ошибка", str(ex))