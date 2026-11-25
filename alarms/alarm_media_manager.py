# alarms/alarm_media_manager.py
"""Менеджер для работы с медиафайлами тревог"""

import os
import shutil
from datetime import datetime
from typing import List, Optional
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

from config.paths import BASE_DIR
from utils.logger import logger


class AlarmMediaManager:
    """Менеджер медиафайлов тревог"""
    
    def __init__(self):
        self.media_dir = os.path.join(BASE_DIR, "data", "media", "alarms")
        os.makedirs(self.media_dir, exist_ok=True)
        logger.info(f"📁 Медиа директория: {self.media_dir}")
    
    def get_media_folder(self, alarm: dict) -> str:
        """
        Возвращает путь к папке медиа для конкретной тревоги
        """
        timestamp = alarm.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        vin = alarm.get("vin", "unknown")
        folder_name = f"{timestamp.replace(':', '-').replace(' ', '_')}_{vin}"
        folder_path = os.path.join(self.media_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
    
    def add_media_files(self, alarm: dict, file_paths: List[str]) -> List[str]:
        """
        Добавляет медиафайлы к тревоге
        
        Args:
            alarm: Данные тревоги
            file_paths: Список путей к файлам для добавления
        
        Returns:
            Список относительных путей к сохранённым файлам
        """
        if not file_paths:
            return []
        
        folder = self.get_media_folder(alarm)
        saved_paths = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue
            
            _, ext = os.path.splitext(file_path)
            counter = 1
            base_name = f"media_{counter}"
            while os.path.exists(os.path.join(folder, f"{base_name}{ext}")):
                counter += 1
                base_name = f"media_{counter}"
            
            dest_path = os.path.join(folder, f"{base_name}{ext}")
            try:
                shutil.copy2(file_path, dest_path)
                rel_path = os.path.relpath(dest_path, BASE_DIR)
                saved_paths.append(rel_path)
                logger.info(f"📎 Медиафайл добавлен: {rel_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка копирования файла {file_path}: {e}")
        
        return saved_paths
    
    def remove_media_file(self, alarm: dict, media_path: str) -> bool:
        """
        Удаляет медиафайл из тревоги
        """
        full_path = os.path.join(BASE_DIR, media_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                logger.info(f"🗑️ Медиафайл удалён: {media_path}")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка удаления {media_path}: {e}")
        return False
    
    def get_media_files(self, alarm: dict) -> List[str]:
        """
        Возвращает список медиафайлов тревоги
        """
        media_list = alarm.get("media", [])
        valid_files = []
        for path in media_list:
            full_path = os.path.join(BASE_DIR, path)
            if os.path.exists(full_path):
                valid_files.append(path)
            else:
                logger.warning(f"⚠️ Файл не найден: {full_path}")
        return valid_files
    
    def open_media_file(self, media_path: str):
        """
        Открывает медиафайл в стандартном просмотрщике
        """
        full_path = os.path.join(BASE_DIR, media_path)
        if os.path.exists(full_path):
            import subprocess
            import sys
            try:
                if sys.platform == 'win32':
                    os.startfile(full_path)
                else:
                    subprocess.call(('xdg-open', full_path))
                logger.info(f"📂 Открыт медиафайл: {full_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка открытия файла: {e}")
                QMessageBox.warning(None, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")
        else:
            logger.warning(f"⚠️ Файл не найден: {full_path}")
            QMessageBox.warning(None, "Ошибка", "Файл не найден.")
    
    def delete_all_media(self, alarm: dict) -> bool:
        """
        Удаляет все медиафайлы тревоги
        """
        folder = self.get_media_folder(alarm)
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                logger.info(f"🗑️ Удалена папка медиа: {folder}")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка удаления папки {folder}: {e}")
        return False


media_manager = AlarmMediaManager()