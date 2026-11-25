# comment_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit,
    QPushButton, QHBoxLayout, QLabel, QGroupBox,
    QListWidget, QListWidgetItem, QFileDialog, QApplication,
    QMessageBox
)
from PyQt5.QtCore import Qt
import os
from datetime import datetime

from .alarm_media_manager import media_manager
from utils.logger import logger


class CommentDialog(QDialog):
    def __init__(self, parent=None, initial_comment="", alarm=None):
        super().__init__(parent)
        self.alarm = alarm
        self._pending_media = []
        self._existing_media = alarm.get("media", []).copy() if alarm else []
        
        self.setWindowTitle("Добавить комментарий")
        self.setModal(True)
        self.resize(1000, 750)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)

        self.label = QLabel("💬 Комментарий:")
        self.label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(self.label)

        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("Введите комментарий...")
        self.comment_edit.setText(initial_comment)
        self.comment_edit.setMinimumHeight(150)
        self.layout.addWidget(self.comment_edit)

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

        hint_label = QLabel("💡 Для вставки из буфера используйте Ctrl+V или кнопку «Вставить»")
        hint_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic; padding: 2px;")
        media_layout.addWidget(hint_label)

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
        self.layout.addWidget(media_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.ok_button = QPushButton("💾 Сохранить")
        self.ok_button.setStyleSheet("""
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
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("❌ Отмена")
        self.cancel_button.setStyleSheet("""
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
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

        self.media_list.setFocusPolicy(Qt.StrongFocus)
        self._update_media_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            self._paste_from_clipboard()
            event.accept()
            return
        super().keyPressEvent(event)

    def _add_media_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите медиафайлы",
            "",
            "Изображения (*.jpg *.jpeg *.png *.gif *.bmp);;Видео (*.mp4 *.avi *.mov *.mkv);;Все файлы (*)"
        )
        if files:
            self._pending_media.extend(files)
            self._update_media_list()
            QMessageBox.information(
                self,
                "✅ Файлы добавлены",
                f"Добавлено {len(files)} файлов."
            )

    def _paste_from_clipboard(self):
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
                f"Изображение из буфера обмена сохранено."
            )
        except Exception as e:
            logger.error(f"Ошибка сохранения изображения из буфера: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить изображение:\n{str(e)}")

    def _remove_media_file(self):
        current_row = self.media_list.currentRow()
        if current_row < 0:
            return

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

        if self._existing_media:
            idx = current_row - len(self._pending_media)
            if idx >= 0 and idx < len(self._existing_media):
                media_path = self._existing_media[idx]
                if self.alarm and media_manager.remove_media_file(self.alarm, media_path):
                    del self._existing_media[idx]
                    self._update_media_list()

    def _clear_media(self):
        for path in self._pending_media:
            if "temp" in path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        self._pending_media = []

        if self.alarm:
            for path in self._existing_media:
                media_manager.remove_media_file(self.alarm, path)
        self._existing_media = []

        self._update_media_list()

    def _update_media_list(self):
        self.media_list.clear()

        if self._pending_media:
            for path in self._pending_media:
                name = os.path.basename(path)
                if "temp" in path:
                    item = QListWidgetItem(f"📋 {name}")
                else:
                    item = QListWidgetItem(f"⏳ {name}")
                item.setData(Qt.UserRole, path)
                self.media_list.addItem(item)

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

    def get_comment(self):
        return self.comment_edit.toPlainText().strip()

    def get_media(self):
        """Возвращает список медиафайлов"""
        result = self._existing_media.copy()
        for path in self._pending_media:
            if "temp" in path:
                result.append(path)
            else:
                result.append(path)
        return result

    def save_media(self, alarm):
        """Сохраняет медиафайлы в постоянное хранилище"""
        if not self._pending_media:
            return []
        
        saved_paths = []
        for path in self._pending_media:
            if "temp" in path:
                saved = media_manager.add_media_files(alarm, [path])
                if saved:
                    saved_paths.extend(saved)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except:
                    pass
            else:
                saved = media_manager.add_media_files(alarm, [path])
                if saved:
                    saved_paths.extend(saved)
        
        self._pending_media = []
        return saved_paths