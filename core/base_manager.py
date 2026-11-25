# core/base_manager.py
"""Базовый класс для управления данными в JSON файлах"""

import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseDataManager:
    """Базовый класс для управления данными в JSON файлах"""
    
    def __init__(self, filepath: str, auto_load: bool = True):
        self.filepath = filepath
        self._cache: Optional[List[Dict]] = None
        self._is_modified = False
        
        if auto_load:
            self._cache = self._load_data()
    
    def _load_data(self) -> List[Dict]:
        """Загружает данные из JSON файла"""
        if not os.path.exists(self.filepath):
            return []
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return data
        except Exception as e:
            logger.error(f"Ошибка загрузки {self.filepath}: {e}")
            return []
    
    def save_data(self) -> bool:
        """Сохраняет данные в JSON файл"""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            self._is_modified = False
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения {self.filepath}: {e}")
            return False
    
    def get_all(self) -> List[Dict]:
        """Возвращает копию всех записей"""
        return self._cache.copy() if self._cache else []
    
    def get_count(self) -> int:
        """Возвращает количество записей"""
        return len(self._cache) if self._cache else 0
    
    def add(self, item: Dict) -> bool:
        """Добавляет запись"""
        if self._cache is None:
            self._cache = []
        self._cache.append(item)
        self._is_modified = True
        return self.save_data()
    
    def delete(self, index: int) -> bool:
        """Удаляет запись по индексу"""
        if self._cache is None or not (0 <= index < len(self._cache)):
            return False
        del self._cache[index]
        self._is_modified = True
        return self.save_data()
    
    def find(self, **kwargs) -> List[Dict]:
        """Поиск записей по полям"""
        if self._cache is None:
            return []
        
        results = []
        for item in self._cache:
            match = True
            for key, value in kwargs.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results
    
    def find_one(self, **kwargs) -> Optional[Dict]:
        """Находит первую запись, удовлетворяющую условиям"""
        results = self.find(**kwargs)
        return results[0] if results else None
    
    def update(self, index: int, new_data: Dict) -> bool:
        """Обновляет запись по индексу"""
        if self._cache is None or not (0 <= index < len(self._cache)):
            return False
        self._cache[index].update(new_data)
        self._is_modified = True
        return self.save_data()
    
    def refresh(self):
        """Принудительная перезагрузка данных"""
        self._cache = self._load_data()