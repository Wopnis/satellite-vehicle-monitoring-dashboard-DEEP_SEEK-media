# main_window.py
import os
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QDesktopWidget
from PyQt5.QtGui import QIcon

from alarms.alarm_manager import AlarmManager
from alarms.alarm_tab import AlarmTab
from alarms.alarm_search_tab import AlarmSearchTab
from messages.message_tab import MessageTab
from notes.notes_tab import NotesTab
from blacklist.blacklist_tab import BlacklistTab
from shifts.shifts_tab import ShiftsTab
from letters.letters_tab import LettersTab
from reminders.reminders_tab import RemindersTab
from analytics.analytics_tab import AnalyticsTab
from analytics_clicker.clicker_analytics_tab import ClickerAnalyticsTab
from seized_vehicles.seized_tab import SeizedTab

from config.paths import CLICKER_LOGS_DIR, PATHS
from utils.logger import logger
from config.settings import settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icons/monitoring.ico"))
        self.setWindowTitle("Дашборд оператора мониторинга")

        self.resize(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
        self.setMinimumSize(settings.WINDOW_MIN_WIDTH, settings.WINDOW_MIN_HEIGHT)

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.alarm_manager = AlarmManager()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.blacklist_tab = BlacklistTab()
        self.shifts_tab = ShiftsTab(self.alarm_manager)
        self.alarm_tab = AlarmTab(self.alarm_manager, self.blacklist_tab, self.shifts_tab)
        self.alarm_tab.entry_form.on_alarm_added = self.on_alarm_added

        self.message_tab = MessageTab(self.get_alarm_from_form)
        self.search_tab = AlarmSearchTab(self.alarm_manager)
        self.notes_tab = NotesTab()
        self.letters_tab = LettersTab()
        self.reminders_tab = RemindersTab()
        
        self.analytics_tab = AnalyticsTab(alarms_file=PATHS["alarms"])
        
        logger.info(f"Загрузка логов кликера из: {CLICKER_LOGS_DIR}")
        self.clicker_analytics_tab = ClickerAnalyticsTab(
            logs_dir=CLICKER_LOGS_DIR
        )

        self.seized_tab = SeizedTab()

        self.tabs.addTab(self.alarm_tab, "🚨 Тревоги")
        self.tabs.addTab(self.message_tab, "💬 Сообщения")
        self.tabs.addTab(self.search_tab, "🔍 Поиск")
        self.tabs.addTab(self.notes_tab, "📝 Заметки")
        self.tabs.addTab(self.letters_tab, "✉️ Письма")
        self.tabs.addTab(self.reminders_tab, "⏰ Напоминания")
        self.tabs.addTab(self.blacklist_tab, "🚫 Чёрный список")
        self.tabs.addTab(self.analytics_tab, "📊 Аналитика демонтажей")
        self.tabs.addTab(self.clicker_analytics_tab, "📊 Аналитика логов")
        self.tabs.addTab(self.seized_tab, "🚗 Изъятые ТС")
        self.tabs.addTab(self.shifts_tab, "📅 Смены")

        self.alarm_tab.list_view.update_alarm_list()
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def get_alarm_from_form(self):
        form = self.alarm_tab.entry_form
        return {
            "vin": form.vin_input.text(),
            "contract": form.contract_input.text(),
            "brand": form.brand_input.text()
        }

    def on_alarm_added(self):
        self.alarm_tab.list_view.update_alarm_list()
        self.message_tab.update_alarm_info(self.get_alarm_from_form())
        
    def on_tab_changed(self, index):
        current_widget = self.tabs.widget(index)
        if isinstance(current_widget, MessageTab):
            current_widget.on_tab_activated()