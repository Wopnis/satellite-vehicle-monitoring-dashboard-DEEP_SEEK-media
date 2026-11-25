# alarms/alarm_manager.py
"""Менеджер тревог"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from core.base_manager import BaseDataManager
from config.paths import PATHS
from utils.logger import logger


class AlarmManager(BaseDataManager):
    """Менеджер тревог"""
    
    def __init__(self):
        super().__init__(PATHS["alarms"])
        logger.info(f"AlarmManager инициализирован: {len(self._cache)} записей")
    
    @property
    def alarms(self) -> List[Dict]:
        """Свойство для обратной совместимости с кодом, использующим .alarms"""
        return self._cache or []
    
    def add_alarm(self, alarm_data: Dict, shift_id: str) -> bool:
        """Добавляет новую тревогу"""
        alarm_data["shift_id"] = shift_id
        self._cache.append(alarm_data)
        self._is_modified = True
        success = self.save_data()
        if success:
            logger.info(f"Тревога добавлена: VIN={alarm_data.get('vin')}, Contract={alarm_data.get('contract')}")
        return success
    
    def get_alarms_for_shift(self, shift_id: str) -> List[Dict]:
        """Возвращает тревоги для указанной смены"""
        return [a for a in self._cache if a.get("shift_id") == shift_id]
    
    def get_active_alarms_for_shift(self, shift_id: str) -> List[Dict]:
        """Возвращает активные тревоги для указанной смены"""
        return [a for a in self._cache 
                if a.get("shift_id") == shift_id and a.get("status") == "active"]
    
    def get_alarm_by_vin_contract(self, vin: str, contract: str, shift_id: Optional[str] = None) -> Optional[Dict]:
        """Находит тревогу по VIN и договору"""
        for alarm in self._cache:
            if alarm.get("vin") == vin and alarm.get("contract") == contract:
                if shift_id is None or alarm.get("shift_id") == shift_id:
                    return alarm
        return None
    
    def close_alarm(self, alarm: Dict) -> bool:
        """Закрывает тревогу"""
        for item in self._cache:
            if (item.get("vin") == alarm.get("vin") and 
                item.get("contract") == alarm.get("contract") and
                item.get("timestamp") == alarm.get("timestamp")):
                if item.get("status") != "closed":
                    item["status"] = "closed"
                    item["closed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self._is_modified = True
                    success = self.save_data()
                    if success:
                        logger.info(f"Тревога закрыта: VIN={alarm.get('vin')}, Contract={alarm.get('contract')}")
                    return success
        return False
    
    def update_alarm(self, old_alarm: Dict, new_data: Dict) -> bool:
        """Обновляет данные тревоги"""
        for item in self._cache:
            if (item.get("vin") == old_alarm.get("vin") and 
                item.get("contract") == old_alarm.get("contract") and
                item.get("timestamp") == old_alarm.get("timestamp")):
                # Сохраняем media при обновлении
                if old_alarm.get("media"):
                    new_data["media"] = old_alarm.get("media")
                item.update(new_data)
                self._is_modified = True
                success = self.save_data()
                if success:
                    logger.info(f"Тревога обновлена: VIN={old_alarm.get('vin')}")
                return success
        return False
    
    def get_statistics(self, shift_id: Optional[str] = None) -> Dict:
        """Возвращает статистику по тревогам"""
        alarms = self.get_alarms_for_shift(shift_id) if shift_id else self._cache
        total = len(alarms)
        active = sum(1 for a in alarms if a.get("status") == "active")
        worked = sum(1 for a in alarms if a.get("status") == "worked")
        closed = total - active - worked
        
        return {
            "total": total,
            "active": active,
            "worked": worked,
            "closed": closed
        }
    
    def save_data(self) -> bool:
        """Переопределяем метод для логирования"""
        result = super().save_data()
        if result:
            logger.debug(f"Данные тревог сохранены: {len(self._cache)} записей")
        return result
    
    def refresh(self):
        """Принудительная перезагрузка данных"""
        super().refresh()
        logger.info(f"Данные тревог перезагружены: {len(self._cache)} записей")