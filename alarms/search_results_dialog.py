# alarms/search_results_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QLabel, QPushButton, 
    QHBoxLayout, QTextEdit, QApplication
)
from PyQt5.QtCore import Qt


class SearchResultDetailDialog(QDialog):
    def __init__(self, result_data, source_type, parent=None):
        super().__init__(parent)
        self.result_data = result_data
        self.source_type = source_type
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Подробная информация")
        self.resize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #F9FAFC;
            }
            QLabel {
                font-weight: bold;
                margin-bottom: 5px;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #D0D0D0;
                padding: 8px;
                font-family: Consolas, monospace;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("Подробная информация")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        self.data_text.setText(self.format_data_for_display())
        layout.addWidget(self.data_text)
        
        button_layout = QHBoxLayout()
        
        self.copy_button = QPushButton("📋 Копировать")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(self.copy_button)
        
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def format_data_for_display(self):
        if not isinstance(self.result_data, dict):
            return str(self.result_data)
            
        field_names = {
            "vin": "VIN",
            "contract": "Договор",
            "brand": "Марка ТС",
            "license": "Госномер",
            "message": "Сообщение",
            "comment": "Комментарий",
            "lessee": "Лизингополучатель",
            "timestamp": "Время создания",
            "closed_at": "Время закрытия",
            "status": "Статус",
            "title": "Заголовок",
            "content": "Содержание",
            "reason": "Причина",
            "id": "ID",
            "started_at": "Начало смены",
            "ended_at": "Окончание смены"
        }
        
        formatted_lines = []
        for key, value in self.result_data.items():
            display_name = field_names.get(key, key)
            formatted_lines.append(f"{display_name}: {value}")
        return "\n".join(formatted_lines)
            
    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.format_data_for_display())


class SearchResultsDialog(QDialog):
    def __init__(self, search_results, parent=None):
        super().__init__(parent)
        self.search_results = search_results
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Результаты глобального поиска")
        self.resize(800, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #F9FAFC;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EEEEEE;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(f"Найдено результатов: {len(self.search_results)}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.show_detail)
        
        for result in self.search_results:
            item_text = result.get("text", "")
            tooltip = result.get("tooltip", "")
            
            from PyQt5.QtWidgets import QListWidgetItem
            item = QListWidgetItem(item_text)
            item.setToolTip(tooltip)
            item.setData(Qt.UserRole, result)
            self.results_list.addItem(item)
            
        layout.addWidget(self.results_list)
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        
    def show_detail(self, item):
        result_data = item.data(Qt.UserRole)
        if result_data and "data" in result_data:
            source_type = result_data.get("source", "")
            detail_dialog = SearchResultDetailDialog(result_data["data"], source_type, self)
            detail_dialog.exec_()