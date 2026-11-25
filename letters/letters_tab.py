# letters/letters_tab.py
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QListWidget, QPushButton, QMessageBox
)
from PyQt5.QtGui import QFont

from config.paths import PATHS
from utils.logger import logger


class LettersTab(QWidget):
    def __init__(self):
        super().__init__()

        self.templates = self.load_templates()

        layout = QVBoxLayout()
        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f7;
                font-size: 13px;
                color: black;
            }
            QLabel {
                font-weight: bold;
                color: #2c3e50;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 1px solid black;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget {
                background-color: #fff;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)

        self.fields = {}
        field_names = {
            "brand": "🚗 Марка ТС",
            "vin": "🔑 VIN",
            "license": "📛 Госномер",
            "contract": "📄 Договор",
            "message": "🗒️ Описание ситуации"
        }

        for key, label in field_names.items():
            hlayout = QHBoxLayout()
            lbl = QLabel(label + ":")
            line_edit = QLineEdit()
            self.fields[key] = line_edit
            hlayout.addWidget(lbl)
            hlayout.addWidget(line_edit)
            layout.addLayout(hlayout)

        layout.addWidget(QLabel("📋 Шаблоны писем:"))
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.apply_template)
        for t in self.templates:
            self.template_list.addItem(t["title"])
        layout.addWidget(self.template_list)

        layout.addWidget(QLabel("✉️ Результат:"))
        self.result_text = QTextEdit()
        self.result_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.result_text)

        self.generate_button = QPushButton("📨 Сформировать письмо")
        self.generate_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.generate_button.clicked.connect(self.generate_message)
        layout.addWidget(self.generate_button)

        self.setLayout(layout)

    def load_templates(self):
        try:
            with open(PATHS["templates_letters"], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов писем: {e}")
            QMessageBox.warning(self, "Ошибка загрузки", f"Не удалось загрузить шаблоны писем:\n{e}")
            return []

    def apply_template(self, item):
        index = self.template_list.row(item)
        self.result_text.clear()
        self.result_text.setPlainText(self.templates[index]["content"])

    def generate_message(self):
        raw_text = self.result_text.toPlainText()
        if not raw_text.strip():
            QMessageBox.warning(self, "Ошибка", "Шаблон письма не выбран или пуст.")
            return

        data = {k: f.text().strip() for k, f in self.fields.items()}
        if not any(data.values()):
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно поле.")
            return

        try:
            result = raw_text.format(**data)
            self.result_text.setPlainText(result)
        except KeyError as e:
            QMessageBox.warning(self, "Ошибка", f"Отсутствует поле: {e}")