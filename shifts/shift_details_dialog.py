# shifts/shift_details_dialog.py
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QMenu, QAction, QInputDialog, QMessageBox,  
    QPushButton, QHBoxLayout, QLineEdit, QFileDialog, QApplication, QToolTip,
    QWidget
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from typing import List, Optional
import json

from utils.logger import logger


class ShiftDetailsDialog(QDialog):
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
    
    def __init__(self, shift: dict, alarm_manager, parent=None):
        super().__init__(parent)
        self.shift = shift or {}
        self.alarm_manager = alarm_manager
        self.setWindowTitle("📊 Подробности смены")
        self.resize(900, 700)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel(f"<b>📅 Смена:</b> {self.shift.get('started_at')} → {self.shift.get('ended_at', 'в процессе')}"))
        
        layout.addWidget(QLabel("<b>💬 Комментарий к смене:</b>"))
        self.comment_box = QTextEdit()
        self.comment_box.setReadOnly(True)
        self.comment_box.setFont(QFont("Segoe UI", 10))
        self.comment_box.setFixedHeight(80)
        self.comment_box.setPlainText(self.shift.get("comment", ""))
        layout.addWidget(self.comment_box)
        
        layout.addWidget(QLabel("<b>📋 Тревоги в смене:</b>"))
        self.alarm_list = QListWidget()
        self.alarm_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.alarm_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.alarm_list)
        
        layout.addWidget(QLabel("<b>🗒️ Журнал смены:</b>"))
        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по журналу (Enter)")
        self.search_input.returnPressed.connect(self.search_in_journal)
        controls.addWidget(self.search_input)
        self.search_btn = QPushButton("Найти")
        self.search_btn.clicked.connect(self.search_in_journal)
        controls.addWidget(self.search_btn)
        self.copy_btn = QPushButton("📋 Копировать")
        self.copy_btn.clicked.connect(self.copy_journal_text)
        controls.addWidget(self.copy_btn)
        self.export_txt_btn = QPushButton("Экспорт TXT")
        self.export_txt_btn.clicked.connect(self.export_txt)
        controls.addWidget(self.export_txt_btn)
        self.export_pdf_btn = QPushButton("Экспорт PDF")
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        controls.addWidget(self.export_pdf_btn)
        layout.addLayout(controls)
        
        self.journal_box = QTextEdit()
        self.journal_box.setReadOnly(True)
        self.journal_box.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.journal_box)
        
        export_controls = QHBoxLayout()
        
        self.export_report_txt_btn = QPushButton("💾 Экспорт отчёта (TXT)")
        self.export_report_txt_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.export_report_txt_btn.clicked.connect(self.export_full_report_txt)
        export_controls.addWidget(self.export_report_txt_btn)
        
        self.export_report_pdf_btn = QPushButton("📄 Экспорт отчёта (PDF)")
        self.export_report_pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.export_report_pdf_btn.clicked.connect(self.export_full_report_pdf)
        export_controls.addWidget(self.export_report_pdf_btn)
        
        self.print_report_btn = QPushButton("🖨️ Печать отчёта")
        self.print_report_btn.setStyleSheet("background-color: #34495e; color: white; font-weight: bold;")
        self.print_report_btn.clicked.connect(self.print_full_report)
        export_controls.addWidget(self.print_report_btn)
        
        export_controls.addStretch()
        layout.addLayout(export_controls)
        
        self.setLayout(layout)
        self.populate_alarm_list()
        self.load_journal_text()
    
    def populate_alarm_list(self):
        self.alarm_list.clear()
        shift_id = self.shift.get("id")
        if not self.alarm_manager:
            return
        
        alarms = [a for a in self.alarm_manager.alarms if a.get("shift_id") == shift_id]
        for alarm in alarms:
            status_icon = "🔴" if alarm.get("status") == "active" else "🟢"
            item = QListWidgetItem(f"{status_icon} {alarm.get('vin','')} | {alarm.get('contract','')} | {alarm.get('message','')}")
            item.setData(Qt.UserRole, alarm)
            self.alarm_list.addItem(item)
    
    def show_context_menu(self, pos: QPoint):
        item = self.alarm_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.addAction("💬 Оставить комментарий", lambda: self.add_comment(item))
        menu.addAction("🔍 Посмотреть подробности", lambda: self.show_alarm_details(item))
        menu.exec_(self.alarm_list.mapToGlobal(pos))
    
    def add_comment(self, item: QListWidgetItem):
        alarm = item.data(Qt.UserRole)
        existing_comment = alarm.get("comment", "")
        comment, ok = QInputDialog.getMultiLineText(self, "Комментарий", "Введите комментарий:", text=existing_comment)
        if ok:
            alarm["comment"] = comment
            if hasattr(self.alarm_manager, "save_alarms"):
                try:
                    self.alarm_manager.save_alarms()
                except Exception as e:
                    logger.error(f"Ошибка сохранения комментария: {e}")
            QMessageBox.information(self, "✅ Сохранено", "Комментарий сохранён.")
            self.populate_alarm_list()
    
    def show_alarm_details(self, item: QListWidgetItem):
        alarm = item.data(Qt.UserRole)
        field_labels = {
            "vin": "🚗 VIN-код",
            "contract": "📄 Договор",
            "brand": "🏷️ Марка",
            "lessee": "👤 Лизингополучатель",
            "license": "📛 Госномер",
            "message": "📢 Тревога",
            "status": "⚠️ Статус",
            "timestamp": "🕒 Время активации",
            "closed_at": "🛑 Время закрытия",
            "comment": "💬 Комментарий",
            "shift_id": "🧾 ID смены",
        }
        lines = []
        for key in ["vin", "contract", "brand", "lessee", "license", "message", "status", "timestamp", "closed_at", "comment", "shift_id"]:
            label = field_labels.get(key, key)
            value = alarm.get(key, "—")
            lines.append(f"<b>{label}:</b> {value}")
        html = "<br><br>".join(lines)
        detail_box = QTextEdit()
        detail_box.setReadOnly(True)
        detail_box.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        detail_box.setHtml(html)
        detail_box.setFont(QFont("Segoe UI", 10))
        dialog = QDialog(self)
        dialog.setWindowTitle("🔍 Подробности тревоги")
        dlg_layout = QVBoxLayout()
        dlg_layout.addWidget(detail_box)
        dialog.setLayout(dlg_layout)
        dialog.resize(600, 450)
        dialog.exec_()
    
    def load_journal_text(self):
        txt = self.shift.get("journal_text", "")
        self.journal_box.setPlainText(txt)
        self.highlight_journal_keywords()
        self.comment_box.setPlainText(self.shift.get("comment", ""))
    
    def search_in_journal(self):
        query = self.search_input.text().strip().lower()
        if not query:
            return
        text = self.journal_box.toPlainText().lower()
        idx = text.find(query)
        if idx == -1:
            QMessageBox.information(self, "Поиск", "Совпадений не найдено.")
            return
        cursor = self.journal_box.textCursor()
        cursor.setPosition(idx)
        cursor.setPosition(idx + len(query), QTextCursor.KeepAnchor)
        self.journal_box.setTextCursor(cursor)
        self.journal_box.setFocus()
    
    def copy_journal_text(self):
        text = self.journal_box.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QToolTip.showText(self.journal_box.mapToGlobal(self.journal_box.rect().topRight()), "📋 Скопировано", self.journal_box)
    
    def export_txt(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Сохранить журнал как TXT", "", "Текстовый файл (*.txt)")
        if not fname:
            return
        if not fname.lower().endswith(".txt"):
            fname += ".txt"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(self.journal_box.toPlainText())
            QMessageBox.information(self, "Экспорт", "Экспорт в TXT выполнен.")
        except Exception as ex:
            logger.error(f"Ошибка экспорта: {ex}")
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
                self.journal_box.toPlainText()
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
    
    def highlight_journal_keywords(self):
        doc = self.journal_box.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()
        plain = self.journal_box.toPlainText()
        if not plain:
            return
        try:
            pattern = re.compile("(" + "|".join(self.KEYWORD_PATTERNS) + ")", re.IGNORECASE | re.UNICODE)
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
    
    def _get_alarms_for_shift(self) -> List[dict]:
        shift_id = self.shift.get("id")
        if not self.alarm_manager or not hasattr(self.alarm_manager, "alarms"):
            return []
        return [a for a in self.alarm_manager.alarms if a.get("shift_id") == shift_id]
    
    def _is_alarm_closed(self, alarm: dict) -> bool:
        if not alarm:
            return False
        if alarm.get("closed_at"):
            return True
        st = str(alarm.get("status", "")).lower()
        if any(tok in st for tok in ("closed", "закрыт", "закрыта", "закрытие")):
            return True
        return False
    
    def _is_alarm_worked(self, alarm: dict) -> bool:
        if not alarm:
            return False
        return alarm.get("status") == "worked"
    
    def _format_alarm_details(self, alarm: dict) -> str:
        lines = []
        status_text = self._get_alarm_status_text(alarm)
        lines.append(f"  {status_text}")
        lines.append(f"  🚨 VIN: {alarm.get('vin', '—')}")
        lines.append(f"  📄 Договор: {alarm.get('contract', '—')}")
        lines.append(f"  🚗 Марка: {alarm.get('brand', '—')}")
        lines.append(f"  👤 Лизингополучатель: {alarm.get('lessee', '—')}")
        lines.append(f"  📢 Сообщение: {alarm.get('message', '—')}")
        lines.append(f"  🕒 Открыта: {alarm.get('timestamp', '—')}")
        closed_at = alarm.get('closed_at', '—')
        if closed_at != '—':
            lines.append(f"  🛑 Закрыта: {closed_at}")
        comment = alarm.get('comment', '').strip()
        if comment:
            lines.append(f"  💬 Комментарий: {comment}")
        return "\n".join(lines)
    
    def _get_alarm_status_text(self, alarm: dict) -> str:
        status = alarm.get("status", "active")
        if status == "closed":
            return "✅ ЗАКРЫТА"
        elif status == "worked":
            return "🟢 ОТРАБОТАНА (не закрыта)"
        else:
            return "🔴 АКТИВНАЯ"
    
    def _generate_full_report_text(self) -> str:
        alarms = self._get_alarms_for_shift()
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("                    ПОЛНЫЙ ОТЧЁТ ПО СМЕНЕ")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        started = self.shift.get("started_at", "—")
        ended = self.shift.get("ended_at", "в процессе")
        report_lines.append(f"📅 Смена: {started} → {ended}")
        report_lines.append(f"🆔 ID смены: {self.shift.get('id', '—')}")
        
        comment = self.shift.get("comment", "").strip()
        if comment:
            report_lines.append(f"💬 Комментарий к смене: {comment}")
        
        report_lines.append("")
        
        total = len(alarms)
        closed = sum(1 for a in alarms if self._is_alarm_closed(a))
        worked = sum(1 for a in alarms if self._is_alarm_worked(a))
        active = total - closed - worked
        
        report_lines.append("=" * 80)
        report_lines.append("                        СТАТИСТИКА ТРЕВОГ")
        report_lines.append("=" * 80)
        report_lines.append(f"📌 Всего тревог: {total}")
        report_lines.append(f"✅ Закрыто: {closed}")
        report_lines.append(f"🟢 Отработано (не закрыто): {worked}")
        report_lines.append(f"🔴 Активных: {active}")
        report_lines.append("")
        
        if total > 0:
            report_lines.append("=" * 80)
            report_lines.append("                    ПОДРОБНЫЙ СПИСОК ТРЕВОГ")
            report_lines.append("=" * 80)
            report_lines.append("")
            
            active_alarms = [a for a in alarms if not self._is_alarm_closed(a) and not self._is_alarm_worked(a)]
            if active_alarms:
                report_lines.append("🔴 АКТИВНЫЕ ТРЕВОГИ:")
                report_lines.append("-" * 80)
                for i, alarm in enumerate(active_alarms, 1):
                    report_lines.append(f"\nТревога #{i}:")
                    report_lines.append(self._format_alarm_details(alarm))
                    report_lines.append("-" * 80)
                report_lines.append("")
            
            worked_alarms = [a for a in alarms if self._is_alarm_worked(a)]
            if worked_alarms:
                report_lines.append("🟢 ОТРАБОТАННЫЕ (но не закрытые) ТРЕВОГИ:")
                report_lines.append("-" * 80)
                for i, alarm in enumerate(worked_alarms, 1):
                    report_lines.append(f"\nТревога #{i}:")
                    report_lines.append(self._format_alarm_details(alarm))
                    report_lines.append("-" * 80)
                report_lines.append("")
            
            closed_alarms = [a for a in alarms if self._is_alarm_closed(a)]
            if closed_alarms:
                report_lines.append("✅ ЗАКРЫТЫЕ ТРЕВОГИ:")
                report_lines.append("-" * 80)
                for i, alarm in enumerate(closed_alarms, 1):
                    report_lines.append(f"\nТревога #{i}:")
                    report_lines.append(self._format_alarm_details(alarm))
                    report_lines.append("-" * 80)
                report_lines.append("")
        
        journal = self.shift.get("journal_text", "") or ""
        if journal.strip():
            report_lines.append("=" * 80)
            report_lines.append("                        ЖУРНАЛ СМЕНЫ")
            report_lines.append("=" * 80)
            report_lines.append("")
            report_lines.append(journal)
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("Отчёт сформирован автоматически системой мониторинга")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def export_full_report_txt(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить полный отчёт как TXT", 
            f"полный_отчёт_смена_{self.shift.get('id', 'unknown')[:8]}.txt",
            "Текстовый файл (*.txt);;Все файлы (*)"
        )
        if not fname:
            return
        
        if not fname.lower().endswith(".txt"):
            fname += ".txt"
        
        try:
            report_text = self._generate_full_report_text()
            with open(fname, "w", encoding="utf-8") as f:
                f.write(report_text)
            QMessageBox.information(self, "Экспорт", f"Полный отчёт успешно сохранён:\n{fname}")
        except Exception as e:
            logger.error(f"Ошибка экспорта отчёта: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")
    
    def export_full_report_pdf(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить полный отчёт как PDF", 
            f"полный_отчёт_смена_{self.shift.get('id', 'unknown')[:8]}.pdf",
            "PDF файл (*.pdf);;Все файлы (*)"
        )
        if not fname:
            return
        
        if not fname.lower().endswith(".pdf"):
            fname += ".pdf"
        
        try:
            doc = QTextDocument()
            report_text = self._generate_full_report_text()
            html = f"<pre style='font-family: Courier New, monospace; font-size: 10pt; white-space: pre-wrap;'>{report_text}</pre>"
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(fname)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            
            doc.print_(printer)
            QMessageBox.information(self, "Экспорт", f"Полный отчёт успешно сохранён:\n{fname}")
        except Exception as e:
            logger.error(f"Ошибка экспорта PDF: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить PDF:\n{str(e)}")
    
    def print_full_report(self):
        try:
            doc = QTextDocument()
            report_text = self._generate_full_report_text()
            html = f"<pre style='font-family: Courier New, monospace; font-size: 10pt;'>{report_text}</pre>"
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec_() == QPrintDialog.Accepted:
                doc.print_(printer)
                QMessageBox.information(self, "Печать", "Отчёт отправлен на печать.")
        except Exception as e:
            logger.error(f"Ошибка печати: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось напечатать отчёт:\n{str(e)}")


def show_shift_details_dialog(shift: dict, alarm_manager, parent=None):
    dlg = ShiftDetailsDialog(shift, alarm_manager, parent)
    dlg.exec_()