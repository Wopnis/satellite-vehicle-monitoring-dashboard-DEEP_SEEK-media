# utils/logger.py
"""Система логирования"""

import os
import logging
from logging.handlers import RotatingFileHandler

from config.paths import PATHS
from config.settings import settings


def setup_logger(name: str = "monitoring", log_level: int = logging.INFO) -> logging.Logger:
    """
    Настраивает и возвращает логгер
    """
    log_dir = PATHS["logs"]
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{name}.log")
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()


def log_action(message: str, level: str = "info"):
    """Упрощенный метод для логирования действий"""
    levels = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }
    func = levels.get(level, logger.info)
    func(message)