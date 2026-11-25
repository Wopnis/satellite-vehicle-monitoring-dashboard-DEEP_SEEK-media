# alarms/alarm_status_manager.py
"""Модуль управления статусами тревог (Отработано / Не отработано)"""

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from utils.logger import logger
from datetime import datetime


class AlarmStatusManager:
    """
    Менеджер управления статусами тревог.
    Добавляет промежуточный статус "Отработано" между "active" и "closed".
    """
    
    # Константы статусов
    STATUS_ACTIVE = "active"
    STATUS_WORKED = "worked"  # Отработано (промежуточный статус)
    STATUS_CLOSED = "closed"
    
    # Цвета для отображения
    COLORS = {
        STATUS_ACTIVE: QColor("#FF1744"),   # Красный
        STATUS_WORKED: QColor("#00C853"),   # Зелёный
        STATUS_CLOSED: QColor("#8888aa"),   # Серо-фиолетовый
    }
    
    # Метки для отображения
    LABELS = {
        STATUS_ACTIVE: "Активная",
        STATUS_WORKED: "Отработано",
        STATUS_CLOSED: "Закрыта",
    }
    
    def __init__(self, alarm_manager):
        """
        Инициализация менеджера статусов
        
        Args:
            alarm_manager: Экземпляр AlarmManager
        """
        self.alarm_manager = alarm_manager
    
    def set_worked_status(self, alarm: dict) -> bool:
        """
        Переводит тревогу в статус "Отработано"
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            True если успешно, иначе False
        """
        if not alarm:
            return False
        
        # Проверяем, не закрыта ли уже тревога
        if alarm.get("status") == self.STATUS_CLOSED:
            QMessageBox.warning(
                None,
                "Ошибка",
                "Нельзя отметить как отработанную закрытую тревогу."
            )
            return False
        
        # Если уже отработана, возвращаем в активное состояние
        if alarm.get("status") == self.STATUS_WORKED:
            return self._revert_to_active(alarm)
        
        # Обновляем статус
        return self._update_status(alarm, self.STATUS_WORKED)
    
    def _update_status(self, alarm: dict, new_status: str) -> bool:
        """
        Обновляет статус тревоги
        
        Args:
            alarm: Данные тревоги
            new_status: Новый статус
        
        Returns:
            True если успешно, иначе False
        """
        try:
            # Находим и обновляем тревогу
            for item in self.alarm_manager.alarms:
                if (item.get("vin") == alarm.get("vin") and 
                    item.get("contract") == alarm.get("contract") and
                    item.get("timestamp") == alarm.get("timestamp")):
                    
                    old_status = item.get("status", self.STATUS_ACTIVE)
                    item["status"] = new_status
                    item["status_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Сохраняем изменения
                    success = self.alarm_manager.save_data()
                    
                    if success:
                        logger.info(
                            f"Статус тревоги изменён: {old_status} -> {new_status}, "
                            f"VIN={alarm.get('vin')}, Contract={alarm.get('contract')}"
                        )
                        return True
                    else:
                        logger.error(f"Не удалось сохранить изменения статуса для VIN={alarm.get('vin')}")
                        return False
            
            logger.warning(f"Тревога не найдена: VIN={alarm.get('vin')}, Contract={alarm.get('contract')}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса: {e}")
            return False
    
    def _revert_to_active(self, alarm: dict) -> bool:
        """
        Возвращает тревогу из статуса "Отработано" в "Активная"
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            True если успешно, иначе False
        """
        confirm = QMessageBox.question(
            None,
            "Подтверждение",
            "Тревога уже отмечена как отработанная.\n"
            "Вернуть её в статус 'Активная'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            return self._update_status(alarm, self.STATUS_ACTIVE)
        
        return False
    
    def get_status_color(self, alarm: dict) -> QColor:
        """
        Возвращает цвет для отображения статуса тревоги
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            QColor для отображения
        """
        status = alarm.get("status", self.STATUS_ACTIVE)
        return self.COLORS.get(status, self.COLORS[self.STATUS_ACTIVE])
    
    def get_status_label(self, alarm: dict) -> str:
        """
        Возвращает текстовую метку статуса
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            Текстовая метка статуса
        """
        status = alarm.get("status", self.STATUS_ACTIVE)
        return self.LABELS.get(status, self.LABELS[self.STATUS_ACTIVE])
    
    def is_worked(self, alarm: dict) -> bool:
        """
        Проверяет, находится ли тревога в статусе "Отработано"
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            True если статус "Отработано"
        """
        return alarm.get("status") == self.STATUS_WORKED
    
    def is_active(self, alarm: dict) -> bool:
        """
        Проверяет, находится ли тревога в статусе "Активная"
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            True если статус "Активная"
        """
        return alarm.get("status") == self.STATUS_ACTIVE
    
    def is_closed(self, alarm: dict) -> bool:
        """
        Проверяет, закрыта ли тревога
        
        Args:
            alarm: Данные тревоги
        
        Returns:
            True если статус "Закрыта"
        """
        return alarm.get("status") == self.STATUS_CLOSED