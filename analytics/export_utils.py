# analytics/export_utils.py
import os
import csv
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from utils.logger import logger


def save_csv_dialog(parent, default_name: str, data_generator) -> bool:
    """Показывает диалог сохранения CSV и экспортирует данные"""
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Сохранить отчёт",
        f"{default_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "CSV файлы (*.csv);;Все файлы (*)"
    )
    if not file_path:
        return False
    
    if not file_path.lower().endswith(".csv"):
        file_path += ".csv"
    
    try:
        success, message = data_generator(file_path)
        if success:
            QMessageBox.information(parent, "✅ Экспорт", message)
            return True
        else:
            QMessageBox.warning(parent, "⚠️ Ошибка", message)
            return False
    except Exception as e:
        logger.error(f"Ошибка сохранения CSV: {e}")
        QMessageBox.critical(parent, "❌ Ошибка", f"Не удалось сохранить файл:\n{e}")
        return False