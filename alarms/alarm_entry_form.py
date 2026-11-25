# alarm_entry_form.py
from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QHBoxLayout, QDialog, QVBoxLayout
)
from PyQt5.QtCore import Qt
from datetime import datetime
import os

from utils.global_search import global_search
from utils.validators import Validators
from utils.logger import logger
from alarms.alarm_search_tab import AlarmSearchTab
from alarms.alarm_integration import check_seized_vehicle, show_seized_alert


class AlarmEntryForm(QWidget):
    def __init__(self, alarm_manager, blacklist_tab, get_shift_id):
        super().__init__()
        self.alarm_manager = alarm_manager
        self.blacklist_tab = blacklist_tab
        self.get_shift_id = get_shift_id
        self.on_alarm_added = None
        self._current_alarm = None
        
        layout = QFormLayout()
        layout.setSpacing(10)

        # Стилизация формы
        self.setStyleSheet("""
            QWidget {
                background-color: #F9FAFC;
                font-size: 14px;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #D0D0D0;
                padding: 4px;
                background-color: #FFFFFF;
            }
            QPushButton {
                padding: 6px 12px;
                font-weight: bold;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
            }
        """)

        self.brand_input = QLineEdit()
        self.vin_input = QLineEdit()
        self.license_input = QLineEdit()
        self.contract_input = QLineEdit()
        self.lessee_input = QLineEdit()
        
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(60)
        self.message_input.setPlaceholderText("Краткое описание тревоги...")
        
        self.comment_input = QTextEdit()
        self.comment_input.setMinimumHeight(150)
        self.comment_input.setPlaceholderText("Подробная информация, контакты, действия...")

        layout.addRow("🚗 Марка ТС*:", self.brand_input)
        layout.addRow("🔑 VIN*:", self.vin_input)  # ← Добавлена звёздочка
        layout.addRow("🚘 Госномер:", self.license_input)
        layout.addRow("📄 Договор*:", self.contract_input)
        layout.addRow("👤 Лизингополучатель:", self.lessee_input)
        layout.addRow("📢 Сообщение*:", self.message_input)
        layout.addRow("📝 Комментарий:", self.comment_input)

        # Кнопки
        button_row = QHBoxLayout()
        
        self.save_button = QPushButton("💾 Сохранить тревогу")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:disabled {
                background-color: #A5D6A7;
                color: #eeeeee;
            }
        """)
        self.save_button.clicked.connect(self.save_alarm)
        button_row.addWidget(self.save_button)

        self.clear_button = QPushButton("🧹 Очистить форму")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #FF7043;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        self.clear_button.clicked.connect(self.clear_form)
        button_row.addWidget(self.clear_button)

        layout.addRow(button_row)

        self.setLayout(layout)

    def save_alarm(self):
        brand = self.brand_input.text().strip()
        vin = self.vin_input.text().strip()
        license_plate = self.license_input.text().strip()
        contract = self.contract_input.text().strip()
        lessee = self.lessee_input.text().strip()
        message = self.message_input.toPlainText().strip()
        comment = self.comment_input.toPlainText().strip()

        # Валидация
        errors = []
        result = Validators.validate_brand(brand)
        if not result.is_valid:
            errors.append(result.error_message)
        
        # VIN — обязателен, но без проверки длины
        if not vin:
            errors.append("VIN обязателен")
        
        result = Validators.validate_contract(contract)
        if not result.is_valid:
            errors.append(result.error_message)
        
        result = Validators.validate_message(message)
        if not result.is_valid:
            errors.append(result.error_message)

        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        # Проверка чёрного списка
        if self.blacklist_tab and self.blacklist_tab.is_blacklisted(vin, contract):
            warning_box = QMessageBox(self)
            warning_box.setWindowTitle("⚠️ Внимание")
            warning_box.setText("VIN или договор присутствуют в чёрном списке!")
            warning_box.setIcon(QMessageBox.Warning)
            warning_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FFEBEE;
                    color: #C62828;
                }
                QPushButton {
                    background-color: #C62828;
                    color: white;
                }
            """)
            warning_box.exec_()
            logger.warning(f"Попытка добавить в чёрный список: VIN={vin}, Contract={contract}")

        # Проверка на изъятое ТС
        seized_result = check_seized_vehicle(vin, contract)
        if seized_result["found"]:
            show_seized_alert(seized_result["vehicles"], self)
            storage = seized_result["vehicles"][0].get("storage_address", "неизвестная стоянка")
            if comment:
                comment = f"{comment}\n\n⚠️ ТС в базе изъятых! Стоянка: {storage}"
            else:
                comment = f"⚠️ ТС в базе изъятых! Стоянка: {storage}"
            self.comment_input.setText(comment)

        shift_id = self.get_shift_id()
        if not shift_id:
            QMessageBox.warning(self, "Нет активной смены", "Перед созданием тревоги начните смену.")
            return

        # Проверка дубликатов
        duplicate_in_current_shift = False
        existing_active_from_other_shift = None

        for alarm in self.alarm_manager.alarms:
            alarm_vin = alarm.get("vin")
            alarm_contract = alarm.get("contract")
            alarm_status = alarm.get("status")
            alarm_shift_id = alarm.get("shift_id")

            if alarm_vin == vin and alarm_contract == contract:
                if alarm_shift_id == shift_id and alarm_status == "active":
                    duplicate_in_current_shift = True
                    break
                elif alarm_shift_id != shift_id and alarm_status == "active":
                    existing_active_from_other_shift = alarm

        if duplicate_in_current_shift:
            QMessageBox.warning(self, "Дубликат", "Активная тревога с таким VIN и договором уже существует в текущей смене.")
            return

        if existing_active_from_other_shift:
            prev_vin = existing_active_from_other_shift.get("vin", "N/A")
            prev_contract = existing_active_from_other_shift.get("contract", "N/A")
            prev_message = existing_active_from_other_shift.get("message", "N/A")
            prev_timestamp = existing_active_from_other_shift.get("timestamp", "N/A")
            prev_shift_id = existing_active_from_other_shift.get("shift_id", "N/A")

            warning_msg = (f"⚠️ Обнаружена незакрытая тревога с теми же данными из другой смены!\n\n"
                           f"VIN: {prev_vin}\n"
                           f"Договор: {prev_contract}\n"
                           f"Сообщение: {prev_message}\n"
                           f"Время активации: {prev_timestamp}\n"
                           f"ID смены (где была создана): {prev_shift_id}\n\n"
                           f"Вы собираетесь создать новую тревогу в текущей смене.")

            warning_box = QMessageBox(self)
            warning_box.setWindowTitle("⚠️ Предупреждение: Незакрытая тревога")
            warning_box.setText(warning_msg)
            warning_box.setIcon(QMessageBox.Warning)
            warning_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            warning_box.setDefaultButton(QMessageBox.Ok)
            warning_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FFF3E0;
                    color: #E65100;
                }
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-weight: bold;
                }
            """)
            result = warning_box.exec_()

            if result == QMessageBox.Cancel:
                return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alarm_data = {
            "brand": brand,
            "vin": vin,
            "license": license_plate,
            "contract": contract,
            "lessee": lessee,
            "message": message,
            "comment": comment,
            "timestamp": timestamp,
            "status": "active",
            "media": []
        }

        self.alarm_manager.add_alarm(alarm_data, shift_id)
        self._current_alarm = alarm_data
        logger.info(f"Тревога создана: VIN={vin}, Contract={contract}")

        # Глобальный поиск
        search_dialog = QDialog(self)
        search_dialog.setWindowTitle("🔍 Найдены связанные записи")
        search_dialog.resize(900, 600)

        layout = QVBoxLayout()
        search_tab = AlarmSearchTab(self.alarm_manager)
        layout.addWidget(search_tab)
        search_dialog.setLayout(layout)

        search_keyword = f"{vin} {contract}".strip()
        if search_keyword:
            search_tab.global_input.setText(search_keyword)
            search_tab.perform_global_search()

            if search_tab.current_results_full:
                search_dialog.exec_()

        if self.on_alarm_added:
            self.on_alarm_added()

        self.save_button.setEnabled(False)

    def clear_form(self):
        self.brand_input.clear()
        self.vin_input.clear()
        self.license_input.clear()
        self.contract_input.clear()
        self.lessee_input.clear()
        self.message_input.clear()
        self.comment_input.clear()
        self._current_alarm = None
        self.save_button.setEnabled(True)
        if self.on_alarm_added:
            self.on_alarm_added()