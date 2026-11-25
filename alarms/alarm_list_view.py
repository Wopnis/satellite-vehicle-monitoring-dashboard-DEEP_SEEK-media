# alarms/alarm_list_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QCheckBox, QPushButton, QDialog, QLineEdit, QTextEdit,
    QDialogButtonBox, QFormLayout, QMessageBox, QMenu, QHBoxLayout
)
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from datetime import datetime
import os

from .comment_dialog import CommentDialog
from .alarm_edit_dialog import AlarmEditDialog
from .alarm_status_manager import AlarmStatusManager
from .alarm_time_color import TimeColorManager
from .alarm_sound import alarm_sound_manager
from .alarm_media_manager import media_manager
from .alarm_media_viewer import MediaViewerDialog
from .alarm_report_dialog import AlarmReportDialog
from utils.logger import logger


class AlarmListView(QWidget):
    def __init__(self, alarm_manager, get_shift_id, on_alarm_closed=None, on_alarm_selected=None):
        super().__init__()
        self.alarm_manager = alarm_manager
        self.get_shift_id = get_shift_id
        self.on_alarm_closed = on_alarm_closed
        self.on_alarm_selected = on_alarm_selected
        
        self.status_manager = AlarmStatusManager(alarm_manager)

        layout = QVBoxLayout()

        self.active_only_checkbox = QCheckBox("Показать только активные тревоги")
        self.active_only_checkbox.setChecked(False)
        self.active_only_checkbox.stateChanged.connect(self.update_alarm_list)
        layout.addWidget(self.active_only_checkbox)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.handle_double_click)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        
        self.worked_button = QPushButton("✅ Отработано")
        self.worked_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.worked_button.clicked.connect(self.mark_as_worked)
        button_layout.addWidget(self.worked_button)

        self.close_button = QPushButton("Закрыть выбранную тревогу")
        self.close_button.clicked.connect(self.close_selected_alarm)
        button_layout.addWidget(self.close_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update_alarm_list()

    def on_item_clicked(self, item):
        alarm_sound_manager.on_alarm_clicked()

    def _get_time_indicator(self, alarm: dict) -> str:
        status = alarm.get("status")
        if status in ["closed", "worked"]:
            return ""
        
        timestamp = alarm.get("timestamp", "")
        if not timestamp:
            return ""
        
        color, is_bold = TimeColorManager.get_time_color(timestamp)
        
        if color == TimeColorManager.COLOR_GREEN:
            return "🟢"
        elif color == TimeColorManager.COLOR_YELLOW:
            return "🟡"
        elif color == TimeColorManager.COLOR_RED:
            return "🔴"
        else:
            return ""

    def update_alarm_list(self):
        self.list_widget.clear()
        shift_id = self.get_shift_id()
        if not shift_id:
            return

        show_only_active = self.active_only_checkbox.isChecked()

        filtered_alarms = [
            alarm for alarm in self.alarm_manager.alarms
            if alarm.get("shift_id") == shift_id and
            (not show_only_active or alarm.get("status") != "closed")
        ]

        for alarm in filtered_alarms:
            vin = alarm.get("vin", "")
            contract = alarm.get("contract", "")
            brand = alarm.get("brand", "")
            message = alarm.get("message", "")
            opened = alarm.get("timestamp", "")
            closed = alarm.get("closed_at", "—") if alarm.get("status") == "closed" else "—"

            status_label = self.status_manager.get_status_label(alarm)
            status_color = self.status_manager.get_status_color(alarm)
            time_indicator = self._get_time_indicator(alarm)
            
            media_files = alarm.get("media", [])
            media_indicator = "📎" if media_files else ""

            if time_indicator:
                display_text = (
                    f"{status_label} | {vin} | {contract} | {brand} | {message} | "
                    f"Открыта: {time_indicator} {opened} | Закрыта: {closed} {media_indicator}"
                )
            else:
                display_text = (
                    f"{status_label} | {vin} | {contract} | {brand} | {message} | "
                    f"Открыта: {opened} | Закрыта: {closed} {media_indicator}"
                )

            if alarm.get("status") == "closed":
                display_text += " ✏️"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, alarm)
            item.setForeground(status_color)
            
            if media_files:
                item.setToolTip("📎 ПКМ -> Просмотреть медиа")

            self.list_widget.addItem(item)

        alarm_sound_manager.check_and_play(filtered_alarms)

    def handle_double_click(self, item):
        alarm = item.data(Qt.UserRole)
        if not alarm:
            return
        
        if self.on_alarm_selected:
            self.on_alarm_selected(alarm)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        alarm = item.data(Qt.UserRole)
        if not alarm:
            return

        menu = QMenu()

        # 📄 НОВЫЙ ПУНКТ: Создать отчёт
        report_action = menu.addAction("📄 Создать отчёт")
        report_action.triggered.connect(lambda: self.show_alarm_report(alarm))
        menu.addSeparator()

        media_files = alarm.get("media", [])
        has_media = bool(media_files)

        if has_media:
            media_action = menu.addAction("📎 Просмотреть медиа")
            media_action.triggered.connect(lambda: self.show_media_dialog(alarm))
            menu.addSeparator()

        if alarm.get("status") != "closed":
            if alarm.get("status") == "worked":
                worked_action = menu.addAction("↩️ Вернуть в активные")
            else:
                worked_action = menu.addAction("✅ Отработано")
            worked_action.triggered.connect(lambda: self.mark_as_worked())
            menu.addSeparator()

        if alarm.get("status") == "closed":
            add_comment_action = menu.addAction("Добавить комментарий ✏️")
            action = menu.exec_(QCursor.pos())
            if action == add_comment_action:
                self.open_comment_dialog(alarm)
        else:
            edit_action = menu.addAction("Редактировать тревогу")
            action = menu.exec_(QCursor.pos())
            if action == edit_action:
                self.open_edit_dialog(alarm)

    def show_alarm_report(self, alarm):
        """Показывает диалог с отчётом по тревоге"""
        dialog = AlarmReportDialog(alarm, self)
        dialog.exec_()

    def open_edit_dialog(self, alarm):
        from .alarm_edit_dialog import AlarmEditDialog
        
        def save_callback(updated_alarm):
            for original in self.alarm_manager.alarms:
                if (original.get("vin") == alarm.get("vin") and
                    original.get("contract") == alarm.get("contract") and
                    original.get("timestamp") == alarm.get("timestamp")):
                    original.update(updated_alarm)
                    break
            self.alarm_manager.save_data()
            self.update_alarm_list()
            logger.info(f"Тревога отредактирована: VIN={alarm.get('vin')}")
        
        dialog = AlarmEditDialog(alarm, save_callback, self)
        dialog.exec_()

    def open_comment_dialog(self, alarm):
        dialog = CommentDialog(initial_comment=alarm.get("comment", ""), alarm=alarm)
        if dialog.exec_():
            new_comment = dialog.get_comment()
            saved_media = dialog.save_media(alarm)
            
            for original in self.alarm_manager.alarms:
                if (original.get("vin") == alarm.get("vin") and
                    original.get("contract") == alarm.get("contract") and
                    original.get("timestamp") == alarm.get("timestamp")):
                    original["comment"] = new_comment
                    if saved_media:
                        existing = original.get("media", [])
                        original["media"] = existing + saved_media
            self.alarm_manager.save_data()
            self.update_alarm_list()

    def close_selected_alarm(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Закрытие тревоги", "Выберите тревогу в списке.")
            return

        alarm = item.data(Qt.UserRole)
        if not alarm:
            return
            
        if alarm.get("status") == "closed":
            QMessageBox.information(self, "Уже закрыта", "Эта тревога уже закрыта.")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы точно хотите закрыть эту тревогу?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            success = self.alarm_manager.close_alarm(alarm)
            if success:
                self.update_alarm_list()
                if self.on_alarm_closed:
                    self.on_alarm_closed()
                logger.info(f"Тревога закрыта: VIN={alarm.get('vin')}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось закрыть тревогу.")

    def mark_as_worked(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(
                self, 
                "Отработка тревоги", 
                "Выберите тревогу в списке."
            )
            return

        alarm = item.data(Qt.UserRole)
        if not alarm:
            return

        if alarm.get("status") == "closed":
            QMessageBox.information(
                self, 
                "Ошибка", 
                "Нельзя отметить как отработанную закрытую тревогу."
            )
            return

        if alarm.get("status") == "worked":
            result = QMessageBox.question(
                self,
                "Вернуть в активные?",
                "Тревога уже отмечена как отработанная.\n"
                "Вернуть её в статус 'Активная'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                worked_reverted = False
                for original in self.alarm_manager.alarms:
                    if (original.get("vin") == alarm.get("vin") and
                        original.get("contract") == alarm.get("contract") and
                        original.get("timestamp") == alarm.get("timestamp")):
                            if original["status"] == "worked":
                                original["status"] = "active"
                                worked_reverted = True
                                break
                
                if worked_reverted:
                    self.alarm_manager.save_data()
                    self.update_alarm_list()
                    logger.info(f"Тревога возвращена в активные: VIN={alarm.get('vin')}")
            return

        worked = False
        for original in self.alarm_manager.alarms:
            if (original.get("vin") == alarm.get("vin") and
                original.get("contract") == alarm.get("contract") and
                original.get("timestamp") == alarm.get("timestamp")):
                if original["status"] != "closed":
                    original["status"] = "worked"
                    worked = True
                    break

        if worked:
            self.alarm_manager.save_data()
            self.update_alarm_list()
            logger.info(f"Тревога отмечена как отработанная: VIN={alarm.get('vin')}")

    def show_media_dialog(self, alarm):
        media_files = media_manager.get_media_files(alarm)
        if not media_files:
            QMessageBox.information(self, "Медиафайлы", "У этой тревоги нет прикреплённых медиафайлов.")
            return
        
        viewer = MediaViewerDialog(alarm, self)
        viewer.exec_()