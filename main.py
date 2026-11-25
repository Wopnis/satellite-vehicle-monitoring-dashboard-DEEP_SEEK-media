# main.py
"""
──────────────────────────────────────────────
Приложение мониторинга | Автор: Wopnis
(c) 2025 Все права защищены
──────────────────────────────────────────────
"""

import sys
import ctypes
import hashlib
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QStatusBar, QMenuBar, QMenu, QAction
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import Qt

from main_window import MainWindow
from config.paths import PATHS
from utils.logger import setup_logger, logger

logger = setup_logger()

__author_signature__ = "Wopnis-2025-UNIQUE-SIGNATURE-741"
__author_hash__ = hashlib.sha256("W-2025".encode()).hexdigest()

THEME_CONFIG_PATH = PATHS["theme"]


def load_theme_preference() -> str:
    if os.path.exists(THEME_CONFIG_PATH):
        try:
            with open(THEME_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("theme", "light")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Ошибка загрузки темы: {e}")
            return "light"
    return "light"


def save_theme_preference(theme_name: str):
    try:
        os.makedirs(os.path.dirname(THEME_CONFIG_PATH), exist_ok=True)
        with open(THEME_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f)
        logger.info(f"Тема сохранена: {theme_name}")
    except Exception as e:
        logger.error(f"Ошибка сохранения темы: {e}")


def apply_light_theme(app: QApplication):
    palette = QPalette()
    base_color = QColor("#f9f9f9")
    text_color = QColor("#2c2c2c")
    accent_color = QColor("#6c63ff")

    palette.setColor(QPalette.Window, base_color)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f0f0f0"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, text_color)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Button, QColor("#e0e0e0"))
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.Highlight, accent_color)
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    app.setPalette(palette)

    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', sans-serif;
            font-size: 16px;
        }
        QPushButton {
            background-color: #6c63ff;
            color: white;
            padding: 6px 12px;
            border-radius: 8px;
        }
        QPushButton:hover {
            background-color: #5952d4;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 4px;
        }
        QListWidget {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 6px;
        }
        QTabBar::tab {
            background: #eaeaea;
            border: 1px solid #cccccc;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 6px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-bottom: 1px solid white;
        }
        QToolTip {
            background-color: #fefefe;
            color: #333333;
            border: 1px solid #aaaaaa;
            padding: 4px;
            border-radius: 6px;
        }
    """)


def apply_dark_theme(app: QApplication):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#2b2b2b"))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor("#3c3f41"))
    palette.setColor(QPalette.AlternateBase, QColor("#2b2b2b"))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor("#3c3f41"))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor("#007acc"))
    palette.setColor(QPalette.HighlightedText, Qt.white)

    app.setPalette(palette)

    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', sans-serif;
            font-size: 16px;
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QPushButton {
            background-color: #007acc;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #005999;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 4px;
        }
        QListWidget {
            background-color: #3a3a3a;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
        }
        QTabBar::tab {
            background: #555555;
            color: white;
            padding: 6px 12px;
            margin-right: 2px;
            border-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #3c3f41;
            font-weight: bold;
        }
        QToolTip {
            background-color: #444444;
            color: white;
            border: 1px solid #888888;
            padding: 4px;
            border-radius: 6px;
        }
    """)


def toggle_theme(app: QApplication, window: MainWindow, menu_action: QAction):
    current_theme = load_theme_preference()
    new_theme = "dark" if current_theme == "light" else "light"
    save_theme_preference(new_theme)

    if new_theme == "dark":
        apply_dark_theme(app)
        menu_action.setText("Светлая тема")
    else:
        apply_light_theme(app)
        menu_action.setText("Тёмная тема")

    window.repaint()


if __name__ == "__main__":
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
        
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon("icons/monitoring.ico"))
        
        theme = load_theme_preference()
        if theme == "dark":
            apply_dark_theme(app)
        else:
            apply_light_theme(app)
        
        window = MainWindow()
        
        status_bar = QStatusBar()
        status_bar.showMessage("Автор: W | © 2025")
        window.setStatusBar(status_bar)
        
        menubar = QMenuBar(window)
        view_menu = QMenu("Вид", menubar)
        theme_action = QAction("Тёмная тема" if theme == "light" else "Светлая тема", window)
        theme_action.triggered.connect(lambda: toggle_theme(app, window, theme_action))
        view_menu.addAction(theme_action)
        menubar.addMenu(view_menu)
        window.setMenuBar(menubar)
        
        window.show()
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске приложения: {e}")
        raise