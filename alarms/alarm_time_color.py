# alarms/alarm_time_color.py
"""Модуль для управления цветом времени открытия тревоги"""

from datetime import datetime
from PyQt5.QtGui import QColor


class TimeColorManager:
    """Менеджер цвета времени открытия тревоги"""
    
    # Цвета для разных интервалов времени
    COLOR_GREEN = QColor("#00C853")      # Зеленый (до 1 часа)
    COLOR_YELLOW = QColor("#FFAB00")     # Темно-желтый (1-2 часа)
    COLOR_RED = QColor("#D50000")        # Темно-красный (более 2 часов)
    COLOR_DEFAULT = QColor("#8888aa")    # Серый (по умолчанию)
    
    @staticmethod
    def get_time_color(timestamp_str: str) -> tuple:
        """
        Возвращает цвет и флаг жирности для времени открытия
        
        Args:
            timestamp_str: Строка с датой и временем открытия
            
        Returns:
            tuple: (QColor, is_bold)
        """
        if not timestamp_str:
            return TimeColorManager.COLOR_DEFAULT, False
        
        try:
            opened_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()
            minutes_passed = (current_time - opened_time).total_seconds() / 60
            
            if minutes_passed < 60:
                return TimeColorManager.COLOR_GREEN, False
            elif minutes_passed < 120:
                return TimeColorManager.COLOR_YELLOW, False
            else:
                return TimeColorManager.COLOR_RED, True
                
        except Exception:
            return TimeColorManager.COLOR_DEFAULT, False