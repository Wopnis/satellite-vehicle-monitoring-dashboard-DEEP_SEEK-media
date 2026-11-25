# reminders/reminders_tab.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)


class RemindersTab(QWidget):
    """Вкладка напоминаний (заглушка)"""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("⏰ Напоминания"))
        layout.addWidget(QLabel("(Функция в разработке)"))
        self.setLayout(layout)