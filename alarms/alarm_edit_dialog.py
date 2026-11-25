# alarms/alarm_edit_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem, QFileDialog, QApplication,
    QLabel
)
from PyQt5.QtCore import Qt
import os
from datetime import datetime

from utils.validators import Validators
from utils.logger import logger
from .alarm_media_manager import media_manager


class AlarmEditDialog(QDialog):
    def __init__(self, alarm, on_save, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать тревогу")
        self.alarm = alarm.copy()
        self.on_save = on_save
        self._pending_media = []
        self._existing_media = alarm.get("media", []).copy()

        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # ---- Основная форма ----
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.brand_input = QLineEdit(self.alarm.get("brand", ""))
        self.vin_input = QLineEdit(self.alarm.get("vin", ""))
        self.license_input = QLineEdit(self.alarm.get("license", ""))
        self.contract_input = QLineEdit(self.alarm.get("contract", ""))
        self.lessee_input = QLineEdit(self.alarm.get("lessee", ""))
        
        self.message_input = QTextEdit()
        self.message_input.setPlainText(self.alarm.get("message", ""))
        self.message_input.setMaximumHeight(80)
        
        self.comment_input = QTextEdit()
        self.comment_input.setPlainText(self.alarm.get("comment", ""))

        form_layout.addRow("🚗 Марка ТС:", self.brand_input)
        form_layout.addRow("🔑 VIN:", self.vin_input)
        form_layout.addRow("🚘 Госномер:", self.license_input)
        form_layout.addRow("📄 Договор:", self.contract_input)
        form_layout.addRow("👤 Лизингополучатель:", self.lessee_input)
        form_layout.addRow("📢 Сообщение:", self.message_input)
        form_layout.addRow("📝 Комментарий:", self.comment_input)

        main_layout.addLayout(form_layout)

        # ---- Медиафайлы ----
        media_group = QGroupBox("📎 Медиафайлы")
        media_group.setStyleSheet("""
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
        """)
        media_group.setMaximumHeight(220)
        
        media_layout = QVBoxLayout()
        media_layout.setSpacing(3)

        # Подсказка для вставки
        hint_label = QLabel("💡 Для вставки из буфера используйте Ctrl+V или кнопку «Вставить»")
        hint_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic; padding: 2px;")
        media_layout.addWidget(hint_label)

        # Список медиафайлов
        self.media_list = QListWidget()
        self.media_list.setMaximumHeight(80)
        self.media_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        self.media_list.itemDoubleClicked.connect(self._open_media_file)
        media_layout.addWidget(self.media_list)

        # Кнопки управления медиа
        media_btn_layout = QHBoxLayout()
        media_btn_layout.setSpacing(4)

        self.add_media_btn = QPushButton("📎 Добавить")
        self.add_media_btn.setFixedHeight(26)
        self.add_media_btn.setToolTip("Добавить фото или видео")
        self.add_media_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                border: none;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.add_media_btn.clicked.connect(self._add_media_files)
        media_btn_layout.addWidget(self.add_media_btn)

        self.paste_media_btn = QPushButton("📋 Вставить (Ctrl+V)")
        self.paste_media_btn.setFixedHeight(26)
        self.paste_media_btn.setToolTip("Вставить из буфера обмена (Ctrl+V)")
        self.paste_media_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                background-color: #9C27B0;
                color: white;
                border-radius: 4px;
                border: none;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.paste_media_btn.clicked.connect(self._paste_from_clipboard)
        media_btn_layout.addWidget(self.paste_media_btn)

        self.remove_media_btn = QPushButton("🗑️ Удалить")
        self.remove_media_btn.setFixedHeight(26)
        self.remove_media_btn.setToolTip("Удалить выбранный файл")
        self.remove_media_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                background-color: #F44336;
                color: white;
                border-radius: 4px;
                border: none;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.remove_media_btn.clicked.connect(self._remove_media_file)
        media_btn_layout.addWidget(self.remove_media_btn)

        self.clear_media_btn = QPushButton("🧹 Очистить")
        self.clear_media_btn.setFixedHeight(26)
        self.clear_media_btn.setToolTip("Удалить все медиафайлы")
        self.clear_media_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                background-color: #FF9800;
                color: white;
                border-radius: 4px;
                border: none;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.clear_media_btn.clicked.connect(self._clear_media)
        media_btn_layout.addWidget(self.clear_media_btn)

        media_btn_layout.addStretch()
        media_layout.addLayout(media_btn_layout)

        media_group.setLayout(media_layout)
        main_layout.addWidget(media_group)

        # ---- Кнопки Save/Cancel ----
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        save_button = QPushButton("💾 Сохранить изменения")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        save_button.clicked.connect(self.save)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("❌ Отмена")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.resize(1400, 800)

        # Устанавливаем фокус на список медиа для Ctrl+V
        self.media_list.setFocusPolicy(Qt.StrongFocus)

        # Загружаем существующие медиа в список
        self._update_media_list()

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш для Ctrl+V"""
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            self._paste_from_clipboard()
            event.accept()
            return
        super().keyPressEvent(event)

    def _add_media_files(self):
        """Открывает диалог выбора файлов и добавляет их"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите медиафайлы для тревоги",
            "",
            "Изображения (*.jpg *.jpeg *.png *.gif *.bmp);;Видео (*.mp4 *.avi *.mov *.mkv);;Все файлы (*)"
        )
        if files:
            self._pending_media.extend(files)
            self._update_media_list()
            QMessageBox.information(
                self,
                "✅ Файлы добавлены",
                f"Добавлено {len(files)} файлов.\nОни будут сохранены при сохранении тревоги."
            )

    def _paste_from_clipboard(self):
        """Вставляет изображение из буфера обмена"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = mime_data.imageData()
            if not image.isNull():
                self._save_image_from_clipboard(image)
                return

        if mime_data.hasUrls():
            urls = mime_data.urls()
            files = []
            for url in urls:
                file_path = url.toLocalFile()
                if file_path and os.path.exists(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.avi', '.mov', '.mkv']:
                        files.append(file_path)
            if files:
                self._pending_media.extend(files)
                self._update_media_list()
                QMessageBox.information(
                    self,
                    "✅ Файлы добавлены",
                    f"Добавлено {len(files)} файлов из буфера обмена."
                )
                return

        if mime_data.hasText():
            text = mime_data.text().strip()
            if os.path.exists(text):
                ext = os.path.splitext(text)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.avi', '.mov', '.mkv']:
                    self._pending_media.append(text)
                    self._update_media_list()
                    QMessageBox.information(
                        self,
                        "✅ Файл добавлен",
                        f"Файл добавлен из буфера обмена: {os.path.basename(text)}"
                    )
                    return

        QMessageBox.information(
            self,
            "ℹ️ Нет данных",
            "В буфере обмена нет изображения или поддерживаемого файла.\n\n"
            "Поддерживаются: JPG, PNG, GIF, BMP, MP4, AVI, MOV, MKV"
        )

    def _save_image_from_clipboard(self, image):
        """Сохраняет изображение из буфера во временный файл"""
        try:
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
            os.makedirs(temp_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_path = os.path.join(temp_dir, f"clipboard_{timestamp}.png")

            image.save(temp_path, "PNG")
            self._pending_media.append(temp_path)
            self._update_media_list()

            QMessageBox.information(
                self,
                "✅ Изображение добавлено",
                f"Изображение из буфера обмена сохранено как:\n{os.path.basename(temp_path)}"
            )
        except Exception as e:
            logger.error(f"Ошибка сохранения изображения из буфера: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить изображение:\n{str(e)}")

    def _remove_media_file(self):
        """Удаляет выбранный медиафайл из списка"""
        current_row = self.media_list.currentRow()
        if current_row < 0:
            return

        # Проверяем, есть ли файл в ожидающих
        if self._pending_media and current_row < len(self._pending_media):
            path = self._pending_media[current_row]
            if "temp" in path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
            del self._pending_media[current_row]
            self._update_media_list()
            return

        # Проверяем, есть ли файл в существующих
        if self._existing_media:
            idx = current_row - len(self._pending_media)
            if idx >= 0 and idx < len(self._existing_media):
                media_path = self._existing_media[idx]
                if media_manager.remove_media_file(self.alarm, media_path):
                    del self._existing_media[idx]
                    self._update_media_list()

    def _clear_media(self):
        """Очищает все медиафайлы"""
        for path in self._pending_media:
            if "temp" in path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        self._pending_media = []

        for path in self._existing_media:
            media_manager.remove_media_file(self.alarm, path)
        self._existing_media = []

        self._update_media_list()

    def _update_media_list(self):
        """Обновляет список медиафайлов"""
        self.media_list.clear()

        # Отображаем ожидающие файлы
        if self._pending_media:
            for path in self._pending_media:
                name = os.path.basename(path)
                if "temp" in path:
                    item = QListWidgetItem(f"📋 {name}")
                else:
                    item = QListWidgetItem(f"⏳ {name}")
                item.setData(Qt.UserRole, path)
                self.media_list.addItem(item)

        # Отображаем уже сохранённые
        if self._existing_media:
            for path in self._existing_media:
                name = os.path.basename(path)
                full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
                item = QListWidgetItem(f"✅ {name}")
                item.setData(Qt.UserRole, full_path)
                self.media_list.addItem(item)

        if self.media_list.count() > 0:
            self.media_list.setToolTip("Двойной клик для просмотра файла")

    def _open_media_file(self, item):
        """Открывает медиафайл при двойном клике"""
        path = item.data(Qt.UserRole)
        if path:
            if os.path.exists(path):
                import subprocess
                import sys
                if sys.platform == 'win32':
                    os.startfile(path)
                else:
                    subprocess.call(('xdg-open', path))
            else:
                QMessageBox.warning(self, "Ошибка", "Файл не найден.")

    def save(self):
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

        # Сохраняем медиафайлы
        media_list = self._existing_media.copy()

        if self._pending_media:
            final_media = []
            for path in self._pending_media:
                if "temp" in path:
                    saved_paths = media_manager.add_media_files(self.alarm, [path])
                    if saved_paths:
                        final_media.extend(saved_paths)
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except:
                        pass
                else:
                    saved_paths = media_manager.add_media_files(self.alarm, [path])
                    if saved_paths:
                        final_media.extend(saved_paths)
            if final_media:
                media_list.extend(final_media)

        updated_alarm = {
            "brand": brand,
            "vin": vin,
            "license": license_plate,
            "contract": contract,
            "lessee": lessee,
            "message": message,
            "comment": comment,
            "media": media_list
        }

        self.on_save(updated_alarm)
        self.accept()
        logger.info(f"Тревога обновлена в диалоге: VIN={vin}, Contract={contract}")