# notes/notes_tab.py
import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QDialog, QDialogButtonBox, QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from datetime import datetime

from core.base_manager import BaseDataManager
from config.paths import PATHS
from utils.logger import logger


class NotesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.notes_file = PATHS["notes"]
        self.notes = self.load_notes()

        layout = QVBoxLayout()
        self.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                font-size: 13px;
            }
            QLabel {
                font-weight: bold;
                color: #2c3e50;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 1px solid #4f4f4f;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget {
                background-color: #fff;              
                border: 1px solid #4f4f4f;
            }
            QPushButton {
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
                background-color: #c4c4c4;
                color: black;
            }
        """)

        self.title_input = QLineEdit()
        self.content_input = QTextEdit()
        # ✅ Сохраняем форматирование в QTextEdit
        self.content_input.setAcceptRichText(False)  # Отключаем HTML, используем plain text
        self.content_input.setTabChangesFocus(False)  # Tab вставляет табуляцию
        self.content_input.setLineWrapMode(QTextEdit.WidgetWidth)  # Перенос по словам
        
        add_button = QPushButton("📝 Добавить заметку")
        add_button.setStyleSheet("background-color: #4CAF50; color: white;")
        add_button.clicked.connect(self.add_note)

        layout.addWidget(QLabel("🖋️ Заголовок:"))
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("📋 Содержание:"))
        layout.addWidget(self.content_input)
        layout.addWidget(add_button)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по заголовку или содержанию...")
        self.search_input.returnPressed.connect(self.search_notes)

        search_button = QPushButton("🔎 Искать")
        search_button.setStyleSheet("background-color: #2196F3; color: white;")
        search_button.clicked.connect(self.search_notes)

        clear_button = QPushButton("🧹 Очистить")
        clear_button.setStyleSheet("background-color: #FF7043; color: white;")
        clear_button.clicked.connect(self.clear_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_layout.addWidget(clear_button)
        layout.addLayout(search_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.show_note_view)
        self.list_widget.itemPressed.connect(self.handle_right_click)
        layout.addWidget(self.list_widget)

        delete_button = QPushButton("🗑️ Удалить выбранную заметку")
        delete_button.setStyleSheet("background-color: #c62828; color: white;")
        delete_button.clicked.connect(self.delete_note)
        layout.addWidget(delete_button)

        self.setLayout(layout)
        self.refresh_list()

    def load_notes(self):
        if os.path.exists(self.notes_file):
            try:
                with open(self.notes_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки заметок: {e}")
                return []
        return []

    def save_notes(self):
        try:
            os.makedirs(os.path.dirname(self.notes_file), exist_ok=True)
            with open(self.notes_file, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения заметок: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить заметки: {e}")

    def add_note(self):
        title = self.title_input.text().strip()
        # ✅ Сохраняем содержимое с переносами строк и пробелами
        content = self.content_input.toPlainText()  # Используем toPlainText() вместо toPlainText().strip()
        
        if not title or not content.strip():
            QMessageBox.warning(self, "Ошибка", "Заполните заголовок и содержание.")
            return
        
        note = {
            "title": title,
            "content": content,  # Сохраняем с форматированием
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.notes.append(note)
        self.save_notes()
        self.title_input.clear()
        self.content_input.clear()
        self.refresh_list()
        logger.info(f"Добавлена заметка: {title}")

    def search_notes(self):
        keyword = self.search_input.text().strip().lower()
        self.list_widget.clear()
        for note in self.notes:
            if keyword in note["title"].lower() or keyword in note["content"].lower():
                item = QListWidgetItem(f"{note['title']} ({note['created_at']})")
                item.setData(Qt.UserRole, note)
                self.list_widget.addItem(item)

    def clear_search(self):
        self.search_input.clear()
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for note in self.notes:
            item = QListWidgetItem(f"{note['title']} ({note['created_at']})")
            item.setData(Qt.UserRole, note)
            self.list_widget.addItem(item)

    def show_note_view(self, item):
        note = item.data(Qt.UserRole)
        dialog = QDialog(self)
        dialog.setWindowTitle(note["title"])
        dialog.resize(600, 450)  # Увеличил размер для удобства
        
        layout = QVBoxLayout()
        text_box = QTextEdit()
        text_box.setReadOnly(True)
        text_box.setFont(QFont("Courier New", 11))  # Моноширинный шрифт для сохранения форматирования
        # ✅ Отображаем с сохранением форматирования
        text_box.setPlainText(note["content"])
        layout.addWidget(text_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.exec_()

    def handle_right_click(self, item):
        if QApplication.mouseButtons() == Qt.RightButton:
            self.edit_note(item)

    def edit_note(self, item):
        note = item.data(Qt.UserRole)
        try:
            index = self.notes.index(note)
        except ValueError:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать заметку")
        dialog.resize(600, 500)
        
        layout = QVBoxLayout()

        title_input = QLineEdit(note["title"])
        
        content_input = QTextEdit()
        content_input.setFont(QFont("Courier New", 11))
        # ✅ Сохраняем форматирование при редактировании
        content_input.setAcceptRichText(False)
        content_input.setPlainText(note["content"])  # Используем setPlainText для сохранения переносов

        layout.addWidget(QLabel("Заголовок:"))
        layout.addWidget(title_input)
        layout.addWidget(QLabel("Содержание:"))
        layout.addWidget(content_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            new_title = title_input.text().strip()
            # ✅ Сохраняем с форматированием
            new_content = content_input.toPlainText()  # toPlainText() сохраняет переносы
            
            if not new_title or not new_content.strip():
                QMessageBox.warning(self, "Ошибка", "Заголовок и содержание не могут быть пустыми.")
                return
            
            self.notes[index]["title"] = new_title
            self.notes[index]["content"] = new_content
            self.save_notes()
            self.refresh_list()
            logger.info(f"Обновлена заметка: {new_title}")

    def delete_note(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        note = item.data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Удалить заметку '{note['title']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            confirm2 = QMessageBox.question(
                self, "Подтверждение",
                "Вы точно уверены?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm2 == QMessageBox.Yes:
                self.notes.remove(note)
                self.save_notes()
                self.refresh_list()
                logger.info(f"Удалена заметка: {note['title']}")