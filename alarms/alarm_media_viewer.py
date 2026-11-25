# alarms/alarm_media_viewer.py
"""Утилита для просмотра медиафайлов тревог с миниатюрами"""

import os
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QMessageBox, QLabel, QScrollArea, QWidget, QGridLayout,
    QFrame, QApplication
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon, QImage

from .alarm_media_manager import media_manager


class MediaViewerDialog(QDialog):
    """Диалог для просмотра медиафайлов с миниатюрами"""
    
    def __init__(self, alarm, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.media_files = media_manager.get_media_files(alarm)
        self.thumbnails = {}
        
        self.setWindowTitle(f"📎 Медиафайлы - {alarm.get('vin', '')}")
        self.resize(750, 550)
        self.setModal(True)
        
        self._init_ui()
        self._load_thumbnails()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Информация
        info_text = f"Тревога: {self.alarm.get('vin', '')} | {self.alarm.get('contract', '')}"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-weight: bold; padding: 4px; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Область с миниатюрами
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                background-color: #f5f5f5;
            }
        """)
        
        self.thumbnails_widget = QWidget()
        self.thumbnails_layout = QGridLayout(self.thumbnails_widget)
        self.thumbnails_layout.setSpacing(10)
        self.thumbnails_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll.setWidget(self.thumbnails_widget)
        layout.addWidget(scroll)
        
        # Статус загрузки
        self.status_label = QLabel("Загрузка миниатюр...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(self.status_label)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        open_btn = QPushButton("📂 Открыть выбранный")
        open_btn.clicked.connect(self._open_selected)
        btn_layout.addWidget(open_btn)
        
        open_folder_btn = QPushButton("📁 Открыть папку")
        open_folder_btn.clicked.connect(self._open_folder)
        btn_layout.addWidget(open_folder_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _load_thumbnails(self):
        """Загружает миниатюры для всех файлов"""
        if not self.media_files:
            self.status_label.setText("Нет медиафайлов")
            return
        
        self.status_label.setText(f"Загрузка {len(self.media_files)} файлов...")
        QApplication.processEvents()
        
        row = 0
        col = 0
        max_cols = 4
        
        for idx, path in enumerate(self.media_files):
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
            
            # Создаём контейнер для миниатюры
            container = QFrame()
            container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #D0D0D0;
                    border-radius: 6px;
                    padding: 4px;
                }
                QFrame:hover {
                    border: 2px solid #2196F3;
                }
            """)
            container.setFixedSize(150, 170)
            container.setProperty("file_path", full_path)
            
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(2)
            container_layout.setContentsMargins(4, 4, 4, 4)
            
            # Миниатюра
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setFixedSize(140, 120)
            thumb_label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
            
            # Имя файла
            name = os.path.basename(full_path)
            name_label = QLabel(name[:20] + ("..." if len(name) > 20 else ""))
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("font-size: 10px; color: #333;")
            name_label.setToolTip(name)
            
            # Размер
            size = self._get_file_size(full_path)
            size_label = QLabel(size)
            size_label.setAlignment(Qt.AlignCenter)
            size_label.setStyleSheet("font-size: 9px; color: #888;")
            
            container_layout.addWidget(thumb_label)
            container_layout.addWidget(name_label)
            container_layout.addWidget(size_label)
            
            # Клик для открытия
            container.mousePressEvent = lambda e, p=full_path: self._open_file_by_path(p)
            
            # Сохраняем ссылку на лейбл для обновления миниатюры
            container.thumb_label = thumb_label
            container.file_path = full_path
            
            self.thumbnails_layout.addWidget(container, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
            
            # Загружаем миниатюру асинхронно
            self._load_thumbnail_async(container, full_path)
        
        self.status_label.setText(f"Загружено {len(self.media_files)} файлов")
    
    def _load_thumbnail_async(self, container, file_path):
        """Загружает миниатюру для файла"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            # Для изображений создаём миниатюру
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # Масштабируем с сохранением пропорций
                    scaled = pixmap.scaled(
                        140, 120, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    container.thumb_label.setPixmap(scaled)
                else:
                    container.thumb_label.setText("🖼️\n(ошибка)")
                    container.thumb_label.setStyleSheet("font-size: 24px; color: #999;")
            
            # Для видео показываем иконку
            elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                container.thumb_label.setText("🎬")
                container.thumb_label.setStyleSheet("font-size: 48px; color: #666;")
            
            else:
                container.thumb_label.setText("📄")
                container.thumb_label.setStyleSheet("font-size: 48px; color: #666;")
                
        except Exception as e:
            container.thumb_label.setText("❌")
            container.thumb_label.setStyleSheet("font-size: 24px; color: #f44336;")
    
    def _get_file_size(self, path):
        """Возвращает размер файла в читаемом формате"""
        try:
            size = os.path.getsize(path)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/(1024*1024):.1f} MB"
        except:
            return "—"
    
    def _open_selected(self):
        """Открывает выбранный файл"""
        # Ищем выделенный контейнер
        for i in range(self.thumbnails_layout.count()):
            widget = self.thumbnails_layout.itemAt(i).widget()
            if widget and widget.styleSheet().find("border: 2px solid #2196F3") != -1:
                self._open_file_by_path(widget.file_path)
                return
        
        QMessageBox.warning(self, "Ошибка", "Выберите файл (кликните по миниатюре).")
    
    def _open_file_by_path(self, file_path):
        """Открывает файл по пути"""
        if file_path and os.path.exists(file_path):
            media_manager.open_media_file(os.path.relpath(file_path, os.path.dirname(os.path.dirname(__file__))))
        else:
            QMessageBox.warning(self, "Ошибка", "Файл не найден.")
    
    def _open_file(self, item):
        """Открывает файл при двойном клике (устаревший метод, оставлен для совместимости)"""
        path = item.data(Qt.UserRole) if item else None
        if path:
            self._open_file_by_path(path)
    
    def _open_folder(self):
        """Открывает папку с медиафайлами"""
        if self.media_files:
            first_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.media_files[0])
            folder = os.path.dirname(first_path)
            if os.path.exists(folder):
                import subprocess
                import sys
                if sys.platform == 'win32':
                    os.startfile(folder)
                else:
                    subprocess.call(('xdg-open', folder))