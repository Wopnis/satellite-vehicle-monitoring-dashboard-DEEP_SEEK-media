# seized_vehicles/seized_entry_dialog.py
"""Диалог добавления изъятого ТС"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QFormLayout,
    QCheckBox, QGroupBox, QGridLayout, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .seized_parser import SeizedTextParser
from utils.logger import logger


class SeizedEntryDialog(QDialog):
    """Диалог для добавления записи об изъятом ТС"""
    
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle("➕ Добавить изъятое ТС" if not edit_data else "✏️ Редактировать запись")
        self.setModal(True)
        self.resize(800, 700)
        
        self.init_ui()
        if edit_data:
            self.load_data(edit_data)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        tabs = QTabWidget()
        
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        
        text_layout.addWidget(QLabel("📝 Вставьте текст об изъятии ТС:"))
        text_layout.addWidget(QLabel("Программа автоматически извлечёт все данные.", styleSheet="color: #666; font-style: italic;"))
        
        self.raw_text_input = QTextEdit()
        self.raw_text_input.setPlaceholderText(
            "Вставьте текст с информацией об изъятии ТС.\n"
            "Программа распознает: дату, договор, марку, VIN, госномер, стоянку."
        )
        self.raw_text_input.setMinimumHeight(200)
        text_layout.addWidget(self.raw_text_input)
        
        parse_btn_layout = QHBoxLayout()
        self.parse_btn = QPushButton("🔍 Распарсить и заполнить форму")
        self.parse_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px 16px;")
        self.parse_btn.clicked.connect(self.parse_and_fill)
        parse_btn_layout.addWidget(self.parse_btn)
        parse_btn_layout.addStretch()
        text_layout.addLayout(parse_btn_layout)
        
        tabs.addTab(text_tab, "📝 Вставить текст")
        
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Например: 15.07.2026")
        form.addRow("📅 Дата изъятия:", self.date_input)
        
        self.contract_input = QLineEdit()
        self.contract_input.setPlaceholderText("Например: ДЛ 2780040995")
        form.addRow("📄 Номер договора:", self.contract_input)
        
        self.lessor_input = QLineEdit()
        self.lessor_input.setPlaceholderText("Например: Бест лизинг/Карго")
        form.addRow("🏢 Лизингодатель:", self.lessor_input)
        
        self.lessee_input = QLineEdit()
        self.lessee_input.setPlaceholderText("Например: ИП Иванов")
        form.addRow("👤 Лизингополучатель:", self.lessee_input)
        
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Например: Schmitz Cargobull")
        form.addRow("🚗 Марка ТС:", self.brand_input)
        
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("VIN код")
        form.addRow("🔑 VIN:", self.vin_input)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Например: ВУ00000")
        form.addRow("📛 Госномер:", self.license_input)
        
        self.storage_input = QLineEdit()
        self.storage_input.setPlaceholderText("Например: г. Набережные Челны, ул. Промышленная 58")
        form.addRow("📍 Стоянка:", self.storage_input)
        
        self.released_to_input = QLineEdit()
        self.released_to_input.setPlaceholderText("Кому и когда выдано со стоянки")
        form.addRow("📤 Выдано со стоянки:", self.released_to_input)
        
        manual_layout.addLayout(form)
        
        flags_group = QGroupBox("📋 Статус документов")
        flags_layout = QGridLayout()
        
        self.act_check = QCheckBox("Акт составлен")
        self.sts_check = QCheckBox("СТС в наличии")
        self.photos_check = QCheckBox("Фото в приложении")
        
        flags_layout.addWidget(self.act_check, 0, 0)
        flags_layout.addWidget(self.sts_check, 0, 1)
        flags_layout.addWidget(self.photos_check, 0, 2)
        
        flags_group.setLayout(flags_layout)
        manual_layout.addWidget(flags_group)
        
        manual_layout.addWidget(QLabel("💬 Комментарий:"))
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Дополнительная информация...")
        self.comment_input.setMaximumHeight(80)
        manual_layout.addWidget(self.comment_input)
        
        tabs.addTab(manual_tab, "✏️ Заполнить вручную")
        
        layout.addWidget(tabs)
        
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px;")
        self.save_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("❌ Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def parse_and_fill(self):
        text = self.raw_text_input.toPlainText().strip()
        if not text:
            return
        
        try:
            data = SeizedTextParser.parse(text)
            
            if data.get("date"):
                self.date_input.setText(data["date"])
            if data.get("contract_number"):
                self.contract_input.setText(data["contract_number"])
            if data.get("lessor"):
                self.lessor_input.setText(data["lessor"])
            if data.get("lessee"):
                self.lessee_input.setText(data["lessee"])
            if data.get("vehicle_brand"):
                self.brand_input.setText(data["vehicle_brand"])
            if data.get("vin"):
                self.vin_input.setText(data["vin"])
            if data.get("license_plate"):
                self.license_input.setText(data["license_plate"])
            if data.get("storage_address"):
                self.storage_input.setText(data["storage_address"])
            
            self.act_check.setChecked(data.get("act_signed", False))
            self.sts_check.setChecked(data.get("sts_available", False))
            self.photos_check.setChecked(data.get("photos_in_rososmotr", False))
            
            found_fields = []
            if data.get("date"): found_fields.append("дата")
            if data.get("contract_number"): found_fields.append("договор")
            if data.get("vehicle_brand"): found_fields.append("марка")
            if data.get("vin"): found_fields.append("VIN")
            if data.get("license_plate"): found_fields.append("госномер")
            if data.get("storage_address"): found_fields.append("стоянка")
            
            if found_fields:
                QMessageBox.information(
                    self, 
                    "✅ Парсинг завершён", 
                    f"Найдены поля: {', '.join(found_fields)}\n\nОстальные поля можно заполнить вручную."
                )
            
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
    
    def load_data(self, data):
        self.date_input.setText(data.get("date", ""))
        self.contract_input.setText(data.get("contract_number", ""))
        self.lessor_input.setText(data.get("lessor", ""))
        self.lessee_input.setText(data.get("lessee", ""))
        self.brand_input.setText(data.get("vehicle_brand", ""))
        self.vin_input.setText(data.get("vin", ""))
        self.license_input.setText(data.get("license_plate", ""))
        self.storage_input.setText(data.get("storage_address", ""))
        self.released_to_input.setText(data.get("released_to", ""))
        self.act_check.setChecked(data.get("act_signed", False))
        self.sts_check.setChecked(data.get("sts_available", False))
        self.photos_check.setChecked(data.get("photos_in_rososmotr", False))
        self.comment_input.setText(data.get("comment", ""))
    
    def get_data(self):
        return {
            "date": self.date_input.text().strip(),
            "contract_number": self.contract_input.text().strip(),
            "lessor": self.lessor_input.text().strip(),
            "lessee": self.lessee_input.text().strip(),
            "vehicle_brand": self.brand_input.text().strip(),
            "vin": self.vin_input.text().strip().upper(),
            "license_plate": self.license_input.text().strip().upper(),
            "storage_address": self.storage_input.text().strip(),
            "released_to": self.released_to_input.text().strip(),
            "act_signed": self.act_check.isChecked(),
            "sts_available": self.sts_check.isChecked(),
            "photos_in_rososmotr": self.photos_check.isChecked(),
            "comment": self.comment_input.toPlainText().strip()
        }
    
    def save(self):
        data = self.get_data()
        
        has_data = any([
            data.get("date"),
            data.get("contract_number"),
            data.get("vehicle_brand"),
            data.get("vin"),
            data.get("storage_address")
        ])
        
        if not has_data:
            reply = QMessageBox.question(
                self,
                "⚠️ Внимание",
                "Не заполнены основные поля (дата, договор, марка, VIN, стоянка).\n\n"
                "Всё равно сохранить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.accept()