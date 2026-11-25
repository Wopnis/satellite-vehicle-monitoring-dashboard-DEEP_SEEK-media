# alarms/alarm_search_tab.py
import json
import re
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QDialog, QTextEdit,
    QDialogButtonBox, QApplication, QFileDialog, QComboBox, QStyledItemDelegate,
    QScrollArea, QGridLayout, QFrame
)
from PyQt5.QtGui import QColor, QFont, QTextDocument, QPixmap
from PyQt5.QtCore import Qt, QMimeData, QSize

from utils.logger import logger
from .alarm_media_manager import media_manager


class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, keyword=""):
        super().__init__()
        self.keyword = keyword

    def set_keyword(self, keyword):
        self.keyword = keyword

    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)
        if not isinstance(text, str) or not self.keyword:
            super().paint(painter, option, index)
            return

        doc = QTextDocument()
        doc.setDefaultFont(option.font)

        escaped = re.escape(self.keyword)
        pattern = re.compile(f"({escaped})", re.IGNORECASE)
        highlighted = pattern.sub(
            r"<span style='background-color:#fff9c4;color:#d32f2f;padding:0 2px;border-radius:2px;font-weight:bold;'>\1</span>",
            text
        )
        doc.setHtml(highlighted)
        doc.setTextWidth(option.rect.width())

        painter.save()
        painter.translate(option.rect.topLeft())
        doc.drawContents(painter)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole)
        if not isinstance(text, str):
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setPlainText(text)
        doc.setTextWidth(option.rect.width())
        return doc.size().toSize()


class AlarmSearchTab(QWidget):
    def __init__(self, alarm_manager):
        super().__init__()
        self.alarm_manager = alarm_manager
        self.current_results_full = []
        self.last_search_keyword = ""

        layout = QVBoxLayout()
        self.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                font-size: 13px;
            }
            QLineEdit {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton {
                padding: 6px 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #ccc;
            }
        """)

        global_layout = QHBoxLayout()
        global_layout.addWidget(QLabel("🔍 Поиск по всем базам:"))
        self.global_input = QLineEdit()
        self.global_input.setPlaceholderText("Введите ключевое слово, VIN, договор...")
        self.global_input.returnPressed.connect(self.perform_global_search)
        global_layout.addWidget(self.global_input)

        self.clear_button = QPushButton("❌ Очистить")
        self.clear_button.setStyleSheet("background-color: #e74c3c; color: white;")
        self.clear_button.clicked.connect(self.clear_search)
        global_layout.addWidget(self.clear_button)

        self.global_search_button = QPushButton("🔎 Найти")
        self.global_search_button.setStyleSheet("background-color: #8e44ad; color: white;")
        self.global_search_button.clicked.connect(self.perform_global_search)
        global_layout.addWidget(self.global_search_button)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Тревоги", "Заметки", "Чёрный список", "Журналы смен", "Изъятые ТС"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        global_layout.addWidget(QLabel("Фильтр:"))
        global_layout.addWidget(self.filter_combo)

        self.print_button = QPushButton("🖨️ Печать")
        self.print_button.setStyleSheet("background-color: #34495e; color: white;")
        self.print_button.clicked.connect(self.print_all_details)
        global_layout.addWidget(self.print_button)

        self.save_txt_button = QPushButton("📄 TXT")
        self.save_txt_button.setStyleSheet("background-color: #2980b9; color: white;")
        self.save_txt_button.clicked.connect(self.save_all_details_as_txt)
        global_layout.addWidget(self.save_txt_button)

        self.copy_button = QPushButton("📋 Копировать")
        self.copy_button.setStyleSheet("background-color: #27ae60; color: white;")
        self.copy_button.clicked.connect(self.copy_all_details_to_clipboard)
        global_layout.addWidget(self.copy_button)

        layout.addLayout(global_layout)

        self.result_list = QListWidget()
        self.result_list.itemClicked.connect(self.highlight_item)
        self.result_list.itemPressed.connect(self.handle_right_click_global)
        self.result_list.itemDoubleClicked.connect(self.show_details_dialog)

        self.highlight_delegate = HighlightDelegate()
        self.result_list.setItemDelegate(self.highlight_delegate)

        layout.addWidget(self.result_list)
        self.setLayout(layout)

    def clear_search(self):
        self.global_input.clear()
        self.result_list.clear()
        self.current_results_full.clear()
        self.last_search_keyword = ""
        self.filter_combo.setCurrentIndex(0)
        self.global_input.setFocus()

    def highlight_item(self, item):
        item.setBackground(QColor("#e3f2fd"))

    def handle_right_click_global(self, item):
        if QApplication.mouseButtons() == Qt.RightButton:
            self.show_details_dialog(item)

    def show_details_dialog(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            QMessageBox.warning(
                self,
                "Данные недоступны",
                "Не удалось загрузить детали.\nВозможно, запись была изменена или удалена."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("📄 Детали")
        dialog.resize(750, 600)
        dialog.setModal(True)
        
        layout = QVBoxLayout()

        text_box = QTextEdit()
        text_box.setReadOnly(True)
        text_box.setFont(QFont("Courier", 10))
        html = self._format_detail_html(data)
        text_box.setHtml(html)
        layout.addWidget(text_box)

        if isinstance(data, dict) and data.get("media"):
            media_files = data.get("media", [])
            
            media_label = QLabel(f"📎 Медиафайлы ({len(media_files)})")
            media_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
            layout.addWidget(media_label)
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(200)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: 1px solid #D0D0D0;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                }
            """)
            
            thumb_widget = QWidget()
            thumb_layout = QGridLayout(thumb_widget)
            thumb_layout.setSpacing(5)
            
            row = 0
            col = 0
            max_cols = 5
            
            for idx, path in enumerate(media_files[:10]):
                full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
                name = os.path.basename(full_path)
                
                container = QFrame()
                container.setStyleSheet("""
                    QFrame {
                        background-color: white;
                        border: 1px solid #D0D0D0;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QFrame:hover {
                        border: 2px solid #2196F3;
                    }
                """)
                container.setFixedSize(100, 100)
                container.setProperty("file_path", full_path)
                
                container_layout = QVBoxLayout(container)
                container_layout.setSpacing(1)
                container_layout.setContentsMargins(2, 2, 2, 2)
                
                thumb_label = QLabel()
                thumb_label.setAlignment(Qt.AlignCenter)
                thumb_label.setFixedSize(90, 70)
                thumb_label.setStyleSheet("background-color: #f0f0f0; border-radius: 2px;")
                
                ext = os.path.splitext(full_path)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    pixmap = QPixmap(full_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(90, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb_label.setPixmap(scaled)
                    else:
                        thumb_label.setText("🖼️")
                        thumb_label.setStyleSheet("font-size: 24px; color: #999;")
                elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                    thumb_label.setText("🎬")
                    thumb_label.setStyleSheet("font-size: 32px; color: #666;")
                else:
                    thumb_label.setText("📄")
                    thumb_label.setStyleSheet("font-size: 32px; color: #666;")
                
                name_label = QLabel(name[:10] + ("..." if len(name) > 10 else ""))
                name_label.setAlignment(Qt.AlignCenter)
                name_label.setStyleSheet("font-size: 8px; color: #333;")
                name_label.setToolTip(name)
                
                container_layout.addWidget(thumb_label)
                container_layout.addWidget(name_label)
                
                container.mousePressEvent = lambda e, p=full_path: self._open_media_from_search_by_path(p)
                
                thumb_layout.addWidget(container, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            if len(media_files) > 10:
                more_label = QLabel(f"... и ещё {len(media_files) - 10} файлов")
                more_label.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
                thumb_layout.addWidget(more_label, row, col)
            
            scroll.setWidget(thumb_widget)
            layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.exec_()

    def _open_media_from_search_by_path(self, file_path):
        if file_path and os.path.exists(file_path):
            media_manager.open_media_file(os.path.relpath(file_path, os.path.dirname(os.path.dirname(__file__))))
        else:
            QMessageBox.warning(self, "Ошибка", "Файл не найден.")

    def _open_media_from_search(self, alarm):
        media_files = media_manager.get_media_files(alarm)
        if not media_files:
            QMessageBox.information(self, "Медиафайлы", "У этой тревоги нет прикреплённых медиафайлов.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📎 Медиафайлы - {alarm.get('vin', '')}")
        dialog.resize(500, 400)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        list_widget = QListWidget()
        for path in media_files:
            name = os.path.basename(path)
            item = QListWidgetItem(f"📄 {name}")
            item.setData(Qt.UserRole, os.path.join(os.path.dirname(os.path.dirname(__file__)), path))
            list_widget.addItem(item)
        
        list_widget.itemDoubleClicked.connect(
            lambda item: media_manager.open_media_file(item.data(Qt.UserRole))
        )
        layout.addWidget(list_widget)
        
        btn_layout = QHBoxLayout()
        
        open_btn = QPushButton("📂 Открыть")
        open_btn.clicked.connect(
            lambda: media_manager.open_media_file(
                list_widget.currentItem().data(Qt.UserRole) if list_widget.currentItem() else ""
            )
        )
        btn_layout.addWidget(open_btn)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def _format_detail_html(self, data):
        keyword = self.last_search_keyword.strip()
        lines = []

        if isinstance(data, dict):
            if "message" in data:
                lines.append("<b>ТИП: Тревога</b>")
                lines.append(f"Марка: {self._highlight_in_text(data.get('brand', ''), keyword)}")
                lines.append(f"VIN: {self._highlight_in_text(data.get('vin', ''), keyword)}")
                lines.append(f"Госномер: {self._highlight_in_text(data.get('license', ''), keyword)}")
                lines.append(f"Договор: {self._highlight_in_text(data.get('contract', ''), keyword)}")
                lines.append(f"Лизингополучатель: {self._highlight_in_text(data.get('lessee', ''), keyword)}")
                lines.append(f"Сообщение: {self._highlight_in_text(data.get('message', ''), keyword)}")
                lines.append(f"Комментарий: {self._highlight_in_text(data.get('comment', ''), keyword)}")
                lines.append(f"Открыта: {self._highlight_in_text(data.get('timestamp', ''), keyword)}")
                lines.append(f"Закрыта: {self._highlight_in_text(data.get('closed_at', ''), keyword)}")
                lines.append(f"Медиа: {len(data.get('media', []))} файлов")

            elif "title" in data and "content" in data:
                lines.append("<b>ТИП: Заметка</b>")
                lines.append(f"Заголовок: {self._highlight_in_text(data.get('title', ''), keyword)}")
                lines.append("")
                lines.append("Содержимое:")
                lines.append(self._highlight_in_text(data.get('content', ''), keyword))

            elif "reason" in data:
                lines.append("<b>ТИП: Чёрный список</b>")
                lines.append(f"VIN: {self._highlight_in_text(data.get('vin', ''), keyword)}")
                lines.append(f"Договор: {self._highlight_in_text(data.get('contract', ''), keyword)}")
                lines.append(f"Причина: {self._highlight_in_text(data.get('reason', ''), keyword)}")
                lines.append(f"Дата добавления: {self._highlight_in_text(data.get('date_added', ''), keyword)}")

            elif "journal_entries" in data or "journal_text" in data:
                journal_entries = data.get("journal_entries", [])
                journal_text_full = data.get("journal_text", "")
                comment = data.get("comment", "")
                started_at = data.get("started_at", "-")
                ended_at = data.get("ended_at", "в процессе")

                lines.append("<b>ТИП: Журнал смены</b>")
                lines.append(f"ID смены: {self._highlight_in_text(data.get('id', ''), keyword)}")
                lines.append(f"Начало: {self._highlight_in_text(started_at, keyword)}")
                lines.append(f"Окончание: {self._highlight_in_text(ended_at, keyword)}")
                lines.append(f"Комментарий: {self._highlight_in_text(comment, keyword)}")
                lines.append("")

                if journal_entries:
                    lines.append("Записи журнала:")
                    for entry in journal_entries:
                        timestamp = entry.get('timestamp', '')
                        text = entry.get('text', '')
                        highlighted = self._highlight_in_text(text, keyword)
                        lines.append(f"[{self._highlight_in_text(timestamp, keyword)}] {highlighted}")
                elif journal_text_full:
                    lines.append("Журнал:")
                    lines.append(self._highlight_in_text(journal_text_full, keyword))
                else:
                    lines.append("Нет записей")

            elif "storage_address" in data:
                lines.append("<b>ТИП: Изъятое ТС</b>")
                lines.append(f"VIN: {self._highlight_in_text(data.get('vin', ''), keyword)}")
                lines.append(f"Договор: {self._highlight_in_text(data.get('contract_number', ''), keyword)}")
                lines.append(f"Марка: {self._highlight_in_text(data.get('vehicle_brand', ''), keyword)}")
                lines.append(f"Госномер: {self._highlight_in_text(data.get('license_plate', ''), keyword)}")
                lines.append(f"Лизингодатель: {self._highlight_in_text(data.get('lessor', ''), keyword)}")
                lines.append(f"Лизингополучатель: {self._highlight_in_text(data.get('lessee', ''), keyword)}")
                lines.append(f"Стоянка: {self._highlight_in_text(data.get('storage_address', ''), keyword)}")
                lines.append(f"Дата изъятия: {self._highlight_in_text(data.get('date', ''), keyword)}")
                lines.append(f"Выдано: {self._highlight_in_text(data.get('released_to', ''), keyword)}")
                if data.get('comment'):
                    lines.append(f"Комментарий: {self._highlight_in_text(data.get('comment', ''), keyword)}")

            else:
                lines.append("Данные:")
                lines.append(self._highlight_in_text(json.dumps(data, ensure_ascii=False, indent=2), keyword))

        else:
            lines.append(self._highlight_in_text(str(data), keyword))

        body = "<br>".join(lines)
        return f"""
        <div style="
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
            white-space: pre-wrap;
            padding: 8px;
        ">
        {body}
        </div>
        """

    def _format_detail_text(self, data):
        if isinstance(data, dict):
            if "message" in data:
                return (
                    f"ТИП: Тревога\n"
                    f"Марка: {data.get('brand', '-')}\n"
                    f"VIN: {data.get('vin', '-')}\n"
                    f"Госномер: {data.get('license', '-')}\n"
                    f"Договор: {data.get('contract', '-')}\n"
                    f"Лизингополучатель: {data.get('lessee', '-')}\n"
                    f"Сообщение: {data.get('message', '-')}\n"
                    f"Комментарий: {data.get('comment', '-')}\n"
                    f"Открыта: {data.get('timestamp', 'Неизвестно')}\n"
                    f"Закрыта: {data.get('closed_at', '—')}\n"
                    f"Медиа: {len(data.get('media', []))} файлов"
                )
            elif "title" in data and "content" in data:
                return (
                    f"ТИП: Заметка\n\n"
                    f"Заголовок: {data.get('title', '-')}\n\n"
                    f"Содержимое:\n{data.get('content', '-')}"
                )
            elif "reason" in data:
                return (
                    f"ТИП: Чёрный список\n\n"
                    f"VIN: {data.get('vin', '-')}\n"
                    f"Договор: {data.get('contract', '-')}\n"
                    f"Причина: {data.get('reason', '-')}\n"
                    f"Дата добавления: {data.get('date_added', '—')}"
                )
            elif "journal_entries" in data or "journal_text" in data:
                journal_entries = data.get("journal_entries", [])
                journal_text_full = data.get("journal_text", "")
                comment = data.get("comment", "")
                started_at = data.get("started_at", "-")
                ended_at = data.get("ended_at", "в процессе")

                full_journal = ""
                if journal_entries:
                    for entry in journal_entries:
                        timestamp = entry.get('timestamp', '')
                        text = entry.get('text', '')
                        full_journal += f"[{timestamp}] {text}\n"
                elif journal_text_full:
                    full_journal = journal_text_full

                return (
                    f"ТИП: Журнал смены\n\n"
                    f"ID смены: {data.get('id', '-')}\n"
                    f"Начало: {started_at}\n"
                    f"Окончание: {ended_at}\n"
                    f"Комментарий: {comment}\n\n"
                    f"Записи журнала:\n{full_journal if full_journal else 'Нет записей'}"
                )
            elif "storage_address" in data:
                return (
                    f"ТИП: Изъятое ТС\n\n"
                    f"VIN: {data.get('vin', '-')}\n"
                    f"Договор: {data.get('contract_number', '-')}\n"
                    f"Марка: {data.get('vehicle_brand', '-')}\n"
                    f"Госномер: {data.get('license_plate', '-')}\n"
                    f"Лизингодатель: {data.get('lessor', '-')}\n"
                    f"Лизингополучатель: {data.get('lessee', '-')}\n"
                    f"Стоянка: {data.get('storage_address', '-')}\n"
                    f"Дата изъятия: {data.get('date', '-')}\n"
                    f"Выдано: {data.get('released_to', '-')}"
                )
            else:
                return f"Данные:\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        else:
            return str(data)

    def _highlight_in_text(self, text: str, keyword: str) -> str:
        if not keyword or not text:
            return text
        escaped = re.escape(keyword)
        pattern = re.compile(f"({escaped})", re.IGNORECASE)
        return pattern.sub(
            r"<span style='background-color:#fff9c4;color:#d32f2f;padding:0 2px;border-radius:2px;font-weight:bold;'>\1</span>",
            text
        )

    def _highlight_plain_text(self, text: str, keyword: str) -> str:
        if not keyword or not text:
            return text
        escaped = re.escape(keyword)
        pattern = re.compile(f"({escaped})", re.IGNORECASE)

        def replacer(match):
            return f"📌 {match.group(1)} 📌"

        return pattern.sub(replacer, text)

    def perform_global_search(self):
        keyword = self.global_input.text().strip()
        self.last_search_keyword = keyword

        if not keyword:
            QMessageBox.warning(self, "Пусто", "Введите слово для поиска.")
            return

        try:
            from utils.global_search import global_search
            results = global_search(keyword)
        except Exception as e:
            logger.error(f"Ошибка глобального поиска: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить поиск: {e}")
            return

        if not results:
            QMessageBox.information(self, "Поиск", "Ничего не найдено.")
            self.result_list.clear()
            self.current_results_full = []
            return

        self.result_list.clear()
        self.current_results_full = [res["data"] for res in results]
        self.highlight_delegate.set_keyword(keyword)

        for res in results:
            source_map = {
                "alarm": "🚨",
                "note": "📝",
                "blacklist": "🚫",
                "shift_journal": "📅",
                "seized_vehicle": "🚗"
            }
            icon = source_map.get(res.get("source", "unknown"), "❓")
            item_text = f"{icon} {res['text']}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, res.get("data"))
            item.setForeground(Qt.black)
            item.setBackground(QColor("#e0f7fa"))
            self.result_list.addItem(item)

        self.filter_combo.setCurrentIndex(0)
        self.apply_filter()

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        self.result_list.clear()

        if not self.current_results_full:
            return

        filtered = []
        for data in self.current_results_full:
            if filter_text == "Все":
                filtered.append(data)
            elif filter_text == "Тревоги" and isinstance(data, dict) and "message" in data:
                filtered.append(data)
            elif filter_text == "Заметки" and isinstance(data, dict) and "title" in data and "content" in data:
                filtered.append(data)
            elif filter_text == "Чёрный список" and isinstance(data, dict) and "reason" in data:
                filtered.append(data)
            elif filter_text == "Журналы смен" and isinstance(data, dict) and ("journal_entries" in data or "journal_text" in data):
                filtered.append(data)
            elif filter_text == "Изъятые ТС" and isinstance(data, dict) and "storage_address" in data:
                filtered.append(data)

        self.highlight_delegate.set_keyword(self.last_search_keyword)

        for data in filtered:
            if isinstance(data, dict):
                if "message" in data:
                    title = f"{data.get('timestamp', '-')} | {data.get('vin', '-')} | {data.get('contract', '-')}"
                elif "title" in data and "content" in data:
                    title = data.get("title", "Без заголовка")
                elif "reason" in data:
                    title = f"{data.get('vin', '-')} | {data.get('reason', '')[:40]}"
                elif "journal_text" in data or "journal_entries" in data:
                    started = data.get("started_at", "-")
                    ended = data.get("ended_at", "в процессе")
                    title = f"{started} → {ended}"
                elif "storage_address" in data:
                    title = f"{data.get('vin', '-')} | {data.get('license_plate', '-')} | {data.get('storage_address', '')[:30]}"
                else:
                    title = "Результат"
            else:
                title = str(data)

            preview = "..."
            item_text = f"{title} — {preview}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, data)
            item.setForeground(Qt.black)
            item.setBackground(QColor("#e0f7fa"))
            self.result_list.addItem(item)

    def print_all_details(self):
        if not self.current_results_full:
            QMessageBox.information(self, "Печать", "Нет результатов для печати.")
            return
        full_text = self._build_full_details_text()
        self._show_preview_dialog(full_text, "Печать всех деталей")

    def save_all_details_as_txt(self):
        if not self.current_results_full:
            QMessageBox.information(self, "Сохранение", "Нет результатов для сохранения.")
            return
        full_text = self._build_full_details_text()
        self._save_to_file(full_text, "txt")

    def copy_all_details_to_clipboard(self):
        if not self.current_results_full:
            QMessageBox.information(self, "Копирование", "Нет результатов для копирования.")
            return
        full_text = self._build_full_details_text()
        clipboard = QApplication.clipboard()
        mime = QMimeData()
        mime.setText(full_text)
        clipboard.setMimeData(mime)
        QMessageBox.information(self, "Копировано", "Все детали скопированы в буфер обмена.")

    def _build_full_details_text(self):
        if not self.current_results_full:
            return "Нет результатов."

        keyword = self.last_search_keyword
        parts = [
            f"Результаты поиска: '{keyword}'",
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            "=" * 80,
            ""
        ]

        for i, data in enumerate(self.current_results_full, 1):
            detail_text = self._format_detail_text(data)
            highlighted = self._highlight_plain_text(detail_text, keyword)
            parts.append(f"=== Результат #{i} ===")
            parts.append(highlighted)
            parts.append("")

        return "\n".join(parts)

    def _show_preview_dialog(self, text, title):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(800, 600)
        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setPlainText(text)
        text_edit.setFont(QFont("Courier", 10))
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.close)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        dialog.exec_()

    def _save_to_file(self, content, ext):
        default_name = f"детали_поиска_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Сохранить как .{ext}",
            default_name,
            f"Текстовые файлы (*.{ext});;Все файлы (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            QMessageBox.information(self, "Сохранено", f"Файл сохранён: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {str(e)}")