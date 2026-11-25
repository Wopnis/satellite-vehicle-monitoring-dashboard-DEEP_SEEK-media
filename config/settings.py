# config/settings.py
"""Настройки приложения"""

import os
from config.paths import BASE_DIR


class AppSettings:
    """Класс с настройками приложения"""
    
    # Настройки окна
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    
    # Настройки автосохранения (в миллисекундах)
    AUTO_SAVE_INTERVAL = 30 * 1000  # 30 секунд
    
    # Настройки аналитики
    DEFAULT_TOP_N = 20
    MAX_RECORDS_ANALYTICS = 10000
    
    # Настройки логов
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # Настройки поиска
    SEARCH_MAX_RESULTS = 1000
    
    # Валидация
    MIN_CONTRACT_LENGTH = 3
    MIN_BRAND_LENGTH = 2
    MIN_MESSAGE_LENGTH = 3
    VIN_LENGTH = 17
    
    # Настройки бэкапов
    MAX_BACKUPS = 30
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")


settings = AppSettings()