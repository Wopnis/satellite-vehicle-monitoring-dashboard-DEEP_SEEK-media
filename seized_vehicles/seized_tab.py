# seized_vehicles/seized_tab.py
"""Вкладка для работы с изъятыми ТС"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QTextEdit, QSplitter, QGroupBox, QGridLayout, QComboBox,
    QDialog, QMenu, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor

from .seized_manager import seized_manager
from .seized_entry_dialog import SeizedEntryDialog
from utils.logger import logger


class SeizedTab(QWidget):
    """Вкладка для работы с изъятыми ТС"""
    
    def __init__(self):
        super().__init__()
        self._updating = False
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        header = QLabel("🚗 База изъятых ТС")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.stats_label)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(3)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(8)
        
        search_group = QGroupBox("🔍 Поиск")
        search_layout = QGridLayout()
        search_layout.setSpacing(8)
        
        search_layout.addWidget(QLabel("Поиск:"), 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("VIN, госномер, договор, стоянка...")
        self.search_input.returnPressed.connect(self.search)
        search_layout.addWidget(self.search_input, 0, 1)
        
        self.search_btn = QPushButton("🔎 Искать")
        self.search_btn.clicked.connect(self.search)
        search_layout.addWidget(self.search_btn, 0, 2)
        
        self.clear_search_btn = QPushButton("🧹 Очистить")
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn, 0, 3)
        
        search_layout.addWidget(QLabel("Стоянка:"), 1, 0)
        self.storage_filter = QComboBox()
        self.storage_filter.addItem("Все стоянки")
        self.storage_filter.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.storage_filter, 1, 1)
        
        self.refresh_storages_btn = QPushButton("🔄")
        self.refresh_storages_btn.setFixedWidth(30)
        self.refresh_storages_btn.setToolTip("Обновить список стоянок")
        self.refresh_storages_btn.clicked.connect(self.update_storage_filter)
        search_layout.addWidget(self.refresh_storages_btn, 1, 2)
        
        search_group.setLayout(search_layout)
        top_layout.addWidget(search_group)
        
        add_group = QGroupBox("➕ Добавление записи")
        add_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Добавить изъятое ТС")
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px;")
        self.add_btn.clicked.connect(self.add_vehicle)
        add_layout.addWidget(self.add_btn)
        
        add_layout.addStretch()
        add_group.setLayout(add_layout)
        top_layout.addWidget(add_group)
        
        splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(4)
        
        list_header = QLabel("📋 Список изъятых ТС:")
        list_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        bottom_layout.addWidget(list_header)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.show_details)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        bottom_layout.addWidget(self.list_widget)
        
        list_btn_layout = QHBoxLayout()
        
        self.details_btn = QPushButton("📋 Подробности")
        self.details_btn.clicked.connect(self.show_selected_details)
        list_btn_layout.addWidget(self.details_btn)
        
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_selected)
        list_btn_layout.addWidget(self.delete_btn)
        
        list_btn_layout.addStretch()
        bottom_layout.addLayout(list_btn_layout)
        
        splitter.addWidget(bottom_widget)
        splitter.setSizes([250, 450])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def load_data(self):
        if self._updating:
            return
        self._updating = True
        try:
            self.update_list()
            self.update_stats()
            self.update_storage_filter()
        finally:
            self._updating = False
    
    def update_list(self, vehicles=None):
        self.list_widget.clear()
        
        if vehicles is None:
            vehicles = seized_manager.get_all()
        
        if not vehicles:
            item = QListWidgetItem("ℹ️ Нет записей об изъятых ТС")
            item.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(item)
            return
        
        vehicles = sorted(vehicles, key=lambda x: x.get("date", ""), reverse=True)
        
        for v in vehicles:
            vin = v.get("vin", "")
            license_plate = v.get("license_plate", "")
            contract = v.get("contract_number", "")
            brand = v.get("vehicle_brand", "")
            storage = v.get("storage_address", "")
            
            display_text = f"{vin} | {license_plate} | {contract} | {brand} | {storage[:40]}..."
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, v)
            self.list_widget.addItem(item)
    
    def update_stats(self):
        stats = seized_manager.get_statistics()
        total = stats.get("total", 0)
        storages_count = len(stats.get("by_storage", {}))
        lessors_count = len(stats.get("by_lessor", {}))
        self.stats_label.setText(f"📊 Всего записей: {total} | Стоянок: {storages_count} | Лизингодателей: {lessors_count}")
    
    def update_storage_filter(self):
        if self._updating:
            return
        current = self.storage_filter.currentText()
        self.storage_filter.blockSignals(True)
        self.storage_filter.clear()
        self.storage_filter.addItem("Все стоянки")
        
        storages = seized_manager.get_all_storages()
        for s in storages:
            self.storage_filter.addItem(s)
        
        index = self.storage_filter.findText(current)
        if index >= 0:
            self.storage_filter.setCurrentIndex(index)
        self.storage_filter.blockSignals(False)
    
    def search(self):
        query = self.search_input.text().strip()
        if not query:
            self.load_data()
            return
        
        results = seized_manager.search(query)
        self.update_list(results)
        
        if not results:
            QMessageBox.information(self, "Поиск", "Ничего не найдено.")
        else:
            QMessageBox.information(self, "Поиск", f"Найдено записей: {len(results)}")
    
    def clear_search(self):
        self.search_input.clear()
        self.storage_filter.setCurrentIndex(0)
        self.load_data()
    
    def _on_filter_changed(self, storage):
        if self._updating:
            return
        if storage == "Все стоянки" or not storage:
            self.load_data()
            return
        
        results = seized_manager.get_by_storage(storage)
        self.update_list(results)
    
    def add_vehicle(self):
        dialog = SeizedEntryDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            if data:
                if isinstance(data, list):
                    count = 0
                    for item in data:
                        if item and any(item.values()):
                            seized_manager.add_vehicle(item)
                            count += 1
                    if count > 0:
                        self.load_data()
                        QMessageBox.information(self, "✅ Добавлено", f"Добавлено {count} записей об изъятых ТС.")
                else:
                    if data and any(data.values()):
                        seized_manager.add_vehicle(data)
                        self.load_data()
                        QMessageBox.information(self, "✅ Добавлено", "Запись об изъятом ТС добавлена.")
    
    def show_selected_details(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите запись в списке.")
            return
        self.show_details(item)
    
    def show_details(self, item):
        vehicle = item.data(Qt.UserRole)
        if not vehicle:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Детали изъятого ТС - {vehicle.get('vin', '')}")
        dialog.resize(650, 550)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Segoe UI", 11))
        
        info = []
        info.append("=" * 60)
        info.append("          ДЕТАЛИ ИЗЪЯТОГО ТРАНСПОРТНОГО СРЕДСТВА")
        info.append("=" * 60)
        info.append("")
        info.append(f"  📅 Дата изъятия:       {vehicle.get('date', '—')}")
        info.append(f"  📄 Договор:            {vehicle.get('contract_number', '—')}")
        info.append(f"  🏢 Лизингодатель:      {vehicle.get('lessor', '—')}")
        info.append(f"  👤 Лизингополучатель:  {vehicle.get('lessee', '—')}")
        info.append(f"  🚗 Марка ТС:           {vehicle.get('vehicle_brand', '—')}")
        info.append(f"  🔑 VIN:                {vehicle.get('vin', '—')}")
        info.append(f"  📛 Госномер:           {vehicle.get('license_plate', '—')}")
        info.append(f"  📍 Стоянка:            {vehicle.get('storage_address', '—')}")
        info.append(f"  📤 Выдано со стоянки:  {vehicle.get('released_to', '—')}")
        info.append("")
        info.append("  📋 Статус документов:")
        
        flags = []
        if vehicle.get('act_signed'):
            flags.append("    ✅ Акт составлен")
        if vehicle.get('sts_available'):
            flags.append("    ✅ СТС в наличии")
        if vehicle.get('photos_in_rososmotr'):
            flags.append("    ✅ Фото в приложении")
        if flags:
            info.extend(flags)
        else:
            info.append("    — Не указано")
        
        info.append("")
        if vehicle.get('comment'):
            info.append("  💬 Комментарий:")
            info.append(f"    {vehicle.get('comment')}")
            info.append("")
        
        info.append(f"  🕐 Добавлено:          {vehicle.get('created_at', '—')}")
        info.append("")
        info.append("=" * 60)
        
        text.setPlainText("\n".join(info))
        layout.addWidget(text)
        
        btn_layout = QHBoxLayout()
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px 16px;")
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        vehicle = item.data(Qt.UserRole)
        if not vehicle:
            return
        
        menu = QMenu(self)
        
        details_action = QAction("📋 Подробности", self)
        details_action.triggered.connect(lambda: self.show_details(item))
        menu.addAction(details_action)
        
        edit_action = QAction("✏️ Редактировать", self)
        edit_action.triggered.connect(lambda: self.edit_vehicle(item))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ Удалить запись", self)
        delete_action.triggered.connect(lambda: self.delete_vehicle(item))
        menu.addAction(delete_action)
        
        menu.exec_(self.list_widget.mapToGlobal(pos))
    
    def edit_vehicle(self, item):
        vehicle = item.data(Qt.UserRole)
        if not vehicle:
            return
        
        dialog = SeizedEntryDialog(self, edit_data=vehicle)
        if dialog.exec_():
            new_data = dialog.get_data()
            if new_data:
                success = seized_manager.update_vehicle(vehicle, new_data)
                if success:
                    self.load_data()
                    QMessageBox.information(self, "✅ Обновлено", "Запись успешно обновлена.")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось обновить запись.")
    
    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите запись в списке.")
            return
        self.delete_vehicle(item)
    
    def delete_vehicle(self, item):
        vehicle = item.data(Qt.UserRole)
        if not vehicle:
            return
        
        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Удалить запись об изъятом ТС?\n\n"
            f"VIN: {vehicle.get('vin', '')}\n"
            f"Договор: {vehicle.get('contract_number', '')}\n"
            f"Стоянка: {vehicle.get('storage_address', '')}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            success = seized_manager.delete_vehicle(vehicle)
            if success:
                self.load_data()
                QMessageBox.information(self, "✅ Удалено", "Запись успешно удалена.")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить запись.")