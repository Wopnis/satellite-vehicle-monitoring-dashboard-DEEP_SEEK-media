# config/paths.py
"""Централизованное управление путями к файлам"""

import os

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Словарь со всеми путями
PATHS = {
    # Данные
    "alarms": os.path.join(BASE_DIR, "data", "alarms.json"),
    "shifts": os.path.join(BASE_DIR, "shifts", "shifts_data.json"),
    "notes": os.path.join(BASE_DIR, "notes", "notes_data.json"),
    "blacklist": os.path.join(BASE_DIR, "blacklist", "blacklist_data.json"),
    
    # Шаблоны
    "templates_letters": os.path.join(BASE_DIR, "letters", "templates.json"),
    "templates_messages": os.path.join(BASE_DIR, "messages", "message_templates.json"),
    
    # Настройки
    "theme": os.path.join(BASE_DIR, "config", "theme.json"),
    
    # Логи
    "logs": os.path.join(BASE_DIR, "logs"),
}

# Конфигурируемый путь к логам кликера
CLICKER_LOGS_DIR = os.environ.get(
    "CLICKER_LOGS_DIR", 
    os.path.join(BASE_DIR, "logs_clicker")
)


def ensure_directories():
    """Создаёт необходимые директории"""
    dirs_to_create = [
        os.path.join(BASE_DIR, "data"),
        os.path.join(BASE_DIR, "data", "media", "alarms"),
        os.path.join(BASE_DIR, "logs"),
        os.path.join(BASE_DIR, "logs_clicker"),
        os.path.join(BASE_DIR, "config"),
        os.path.join(BASE_DIR, "backups"),
    ]
    for d in dirs_to_create:
        os.makedirs(d, exist_ok=True)


ensure_directories()