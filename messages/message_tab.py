# messages/message_tab.py
import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QMessageBox, QGroupBox, QFormLayout, QApplication
)
from PyQt5.QtGui import QFont

from config.paths import PATHS
from utils.logger import logger


class MessageTab(QWidget):
    def __init__(self, get_current_alarm_callback):
        super().__init__()
        self.get_current_alarm = get_current_alarm_callback
        self.templates = self.load_templates()

        layout = QVBoxLayout()
        font = QFont()
        font.setPointSize(12)

        self.setStyleSheet("""
            QWidget {
                background-color: #f4f4f4;
            }
            QLabel {
                color: #2c3e50;
                font-weight: bold;
            }
            QComboBox {
                background-color: white;
                border: 1px solid #ccc;
                padding: 4px;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                border-radius: 4px;
                padding: 8px 14px;
                font-weight: bold;
            }
        """)

        self.info_group = QGroupBox("🔍 Обрабатываемая тревога")
        info_layout = QFormLayout()
        self.vin_label = QLabel("")
        self.contract_label = QLabel("")
        self.brand_label = QLabel("")
        self.lessee_label = QLabel("")
        self.vin_label.setFont(font)
        self.contract_label.setFont(font)
        self.brand_label.setFont(font)
        self.lessee_label.setFont(font)
        info_layout.addRow("🔢 VIN:", self.vin_label)
        info_layout.addRow("📄 Договор:", self.contract_label)
        info_layout.addRow("🚗 Марка:", self.brand_label)
        info_layout.addRow("👤 Лизингополучатель:", self.lessee_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        layout.addWidget(QLabel("🧩 Выберите шаблон сообщения:"))
        self.template_box = QComboBox()
        self.template_box.setFont(font)
        self.template_box.addItems(self.templates)
        layout.addWidget(self.template_box)

        self.generate_button = QPushButton("✏️ Сформировать сообщение")
        self.generate_button.setFont(font)
        self.generate_button.clicked.connect(self.generate_message)
        self.generate_button.setStyleSheet("background-color: #2196F3; color: white;")
        layout.addWidget(self.generate_button)

        self.message_box = QTextEdit()
        self.message_box.setFont(QFont("Courier", 12))
        layout.addWidget(self.message_box)

        self.copy_button = QPushButton("📋 Копировать и очистить")
        self.copy_button.setFont(font)
        self.copy_button.clicked.connect(self.copy_and_clear)
        self.copy_button.setStyleSheet("background-color: #4CAF50; color: white;")
        layout.addWidget(self.copy_button)

        self.clear_button = QPushButton("🧹 Очистить")
        self.clear_button.setFont(font)
        self.clear_button.clicked.connect(self.message_box.clear)
        self.clear_button.setStyleSheet("background-color: #FF7043; color: white;")
        layout.addWidget(self.clear_button)

        self.setLayout(layout)

    def load_templates(self):
        path = PATHS["templates_messages"]
        if not os.path.exists(path):
            logger.warning(f"Файл шаблонов не найден: {path}")
            return ["⚠️ Шаблон: {brand} | {vin} | {contract}"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                templates = json.load(f)
                if not templates:
                    return ["⚠️ Шаблон: {brand} | {vin} | {contract}"]
                return templates
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов: {e}")
            return ["⚠️ Шаблон: {brand} | {vin} | {contract}"]

    def generate_message(self):
        template = self.template_box.currentText()
        alarm = self.get_current_alarm()
        if not alarm or not alarm.get("vin"):
            QMessageBox.warning(self, "Ошибка", "Нет данных тревоги. Сначала создайте тревогу.")
            return

        try:
            message = template.format(
                brand=alarm.get("brand", ""),
                vin=alarm.get("vin", ""),
                contract=alarm.get("contract", ""),
                lessee=alarm.get("lessee", "")
            )
            self.message_box.setPlainText(message)
            self.update_alarm_info(alarm)
            logger.info(f"Сгенерировано сообщение для VIN={alarm.get('vin')}")
        except KeyError as e:
            QMessageBox.warning(self, "Ошибка", f"В шаблоне отсутствует поле: {e}")

    def copy_and_clear(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.message_box.toPlainText())
        self.message_box.clear()

    def update_alarm_info(self, alarm):
        self.vin_label.setText(alarm.get("vin", ""))
        self.contract_label.setText(alarm.get("contract", ""))
        self.brand_label.setText(alarm.get("brand", ""))
        self.lessee_label.setText(alarm.get("lessee", ""))

    def on_tab_activated(self):
        alarm = self.get_current_alarm()
        if alarm and alarm.get("vin"):
            self.update_alarm_info(alarm)