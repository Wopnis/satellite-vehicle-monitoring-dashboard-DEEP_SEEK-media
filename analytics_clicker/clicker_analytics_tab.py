# analytics_clicker/clicker_analytics_tab.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QGroupBox, QGridLayout,
    QListWidget, QListWidgetItem, QTabWidget,
    QMessageBox, QMenu, QAction, QFileDialog, QLineEdit,
    QProgressBar
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from .clicker_log_parser import ClickerLogParser
from datetime import datetime, timedelta
import os

from utils.logger import logger

FIELD_NAMES = {
    "vin": "VIN",
    "contract": "Договор",
    "lessee": "Лизингополучатель",
    "alarm_type": "Тип тревоги",
    "alarm_text": "Текст тревоги"
}


class LogParserThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, logs_dir, start_date, end_date, max_records=10000):
        super().__init__()
        self.logs_dir = logs_dir
        self.start_date = start_date
        self.end_date = end_date
        self.max_records = max_records
    
    def run(self):
        try:
            parser = ClickerLogParser(self.logs_dir)
            success = parser.parse_all_logs(
                start_date=self.start_date,
                end_date=self.end_date,
                max_records=self.max_records
            )
            
            if success or parser.parse_errors:
                self.finished.emit(parser)
            else:
                self.error.emit("Не найдено логов за указанный период")
        except Exception as e:
            logger.error(f"Ошибка парсинга логов: {e}")
            self.error.emit(str(e))


class ClickerAnalyticsTab(QWidget):
    def __init__(self, logs_dir: str = "logs", parent=None):
        super().__init__(parent)
        self.logs_dir = logs_dir
        self.parser = None
        self.parser_thread = None
        
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #F9FAFC;
                font-size: 13px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
            }
            QComboBox, QDateEdit, QLineEdit {
                padding: 4px;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
            }
            QProgressBar {
                border: 1px solid #D0D0D0;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        
        header_layout = QHBoxLayout()
        header_label = QLabel("📊 Аналитика логов кликера")
        header_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.refresh_btn.clicked.connect(self._load_logs)
        header_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("💾 Экспорт")
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.export_btn.clicked.connect(self._show_export_menu)
        header_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(header_layout)
        
        path_group = QGroupBox("📁 Путь к логам")
        path_layout = QHBoxLayout()
        
        self.logs_dir_input = QLineEdit(self.logs_dir)
        self.logs_dir_input.setPlaceholderText("Путь к папке с логами")
        path_layout.addWidget(QLabel("Папка:"))
        path_layout.addWidget(self.logs_dir_input)
        
        self.browse_btn = QPushButton("📂 Обзор")
        self.browse_btn.clicked.connect(self._browse_logs_dir)
        path_layout.addWidget(self.browse_btn)
        
        path_group.setLayout(path_layout)
        main_layout.addWidget(path_group)
        
        date_group = QGroupBox("📅 Фильтр по датам (по имени файла)")
        date_layout = QHBoxLayout()
        
        date_layout.addWidget(QLabel("С:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        date_layout.addWidget(self.date_from)
        
        date_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        date_layout.addWidget(self.date_to)
        
        date_layout.addWidget(QLabel("Макс. записей:"))
        self.max_records_combo = QComboBox()
        self.max_records_combo.addItems(["1000", "5000", "10000", "50000", "Все"])
        self.max_records_combo.setCurrentText("10000")
        date_layout.addWidget(self.max_records_combo)
        
        self.apply_filter_btn = QPushButton("✅ Применить")
        self.apply_filter_btn.setStyleSheet("background-color: #27AE60; color: white;")
        self.apply_filter_btn.clicked.connect(self._load_logs)
        date_layout.addWidget(self.apply_filter_btn)
        
        self.reset_filter_btn = QPushButton("🔄 Сбросить")
        self.reset_filter_btn.setStyleSheet("background-color: #E67E22; color: white;")
        self.reset_filter_btn.clicked.connect(self._reset_date_filter)
        date_layout.addWidget(self.reset_filter_btn)
        
        date_group.setLayout(date_layout)
        main_layout.addWidget(date_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        main_layout.addWidget(self.progress_bar)
        
        filter_group = QGroupBox("🔍 Быстрые фильтры")
        filter_layout = QGridLayout()
        
        filter_layout.addWidget(QLabel("VIN:"), 0, 0)
        self.filter_vin = QLineEdit()
        self.filter_vin.setPlaceholderText("Поиск по VIN")
        self.filter_vin.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.filter_vin, 0, 1)
        
        filter_layout.addWidget(QLabel("Договор:"), 0, 2)
        self.filter_contract = QLineEdit()
        self.filter_contract.setPlaceholderText("Поиск по договору")
        self.filter_contract.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.filter_contract, 0, 3)
        
        filter_layout.addWidget(QLabel("Тип тревоги:"), 1, 0)
        self.filter_type = QComboBox()
        self.filter_type.addItems(["Все типы", "auto_close", "manual_close", "other"])
        self.filter_type.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.filter_type, 1, 1)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        stats_group = QGroupBox("📈 Базовая статистика")
        stats_layout = QGridLayout()
        
        self.stat_total = QLabel("Всего: —")
        self.stat_auto = QLabel("Автозакрытие: —")
        self.stat_manual = QLabel("Ручное: —")
        self.stat_other = QLabel("Прочее: —")
        self.stat_vin = QLabel("С VIN: —")
        self.stat_contract = QLabel("С договором: —")
        self.stat_files = QLabel("Файлов: —")
        
        stats_layout.addWidget(self.stat_total, 0, 0)
        stats_layout.addWidget(self.stat_auto, 0, 1)
        stats_layout.addWidget(self.stat_manual, 1, 0)
        stats_layout.addWidget(self.stat_other, 1, 1)
        stats_layout.addWidget(self.stat_vin, 2, 0)
        stats_layout.addWidget(self.stat_contract, 2, 1)
        stats_layout.addWidget(self.stat_files, 3, 0)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        self.analysis_tabs = QTabWidget()
        
        dup_tab = QWidget()
        dup_layout = QVBoxLayout()
        dup_controls = QHBoxLayout()
        dup_controls.addWidget(QLabel("Искать дубли по:"))
        self.dup_field_combo = QComboBox()
        self.dup_field_combo.addItems(["VIN", "Договор", "Тип тревоги"])
        dup_controls.addWidget(self.dup_field_combo)
        
        self.find_dups_btn = QPushButton("🔍 Найти")
        self.find_dups_btn.clicked.connect(self._find_duplicates)
        dup_controls.addWidget(self.find_dups_btn)
        dup_layout.addLayout(dup_controls)
        
        self.dup_list = QListWidget()
        dup_layout.addWidget(self.dup_list)
        dup_tab.setLayout(dup_layout)
        
        freq_tab = QWidget()
        freq_layout = QVBoxLayout()
        freq_controls = QHBoxLayout()
        freq_controls.addWidget(QLabel("Анализ по полю:"))
        self.freq_field_combo = QComboBox()
        self.freq_field_combo.addItems(["vin", "contract", "alarm_type"])
        self.freq_field_combo.setItemText(0, "VIN")
        self.freq_field_combo.setItemText(1, "Договор")
        self.freq_field_combo.setItemText(2, "Тип тревоги")
        self.freq_field_combo.currentTextChanged.connect(self._run_frequency_analysis)
        freq_controls.addWidget(self.freq_field_combo)
        
        freq_controls.addWidget(QLabel("Топ:"))
        self.freq_top_spin = QComboBox()
        self.freq_top_spin.addItems(["10", "20", "50", "100"])
        self.freq_top_spin.setCurrentText("20")
        self.freq_top_spin.currentTextChanged.connect(self._run_frequency_analysis)
        freq_controls.addWidget(self.freq_top_spin)
        freq_layout.addLayout(freq_controls)
        
        self.freq_list = QListWidget()
        freq_layout.addWidget(self.freq_list)
        freq_tab.setLayout(freq_layout)
        
        types_tab = QWidget()
        types_layout = QVBoxLayout()
        self.show_types_btn = QPushButton("📋 Показать распределение")
        self.show_types_btn.clicked.connect(self._show_alarm_types)
        types_layout.addWidget(self.show_types_btn)
        
        self.types_list = QListWidget()
        types_layout.addWidget(self.types_list)
        types_tab.setLayout(types_layout)
        
        time_tab = QWidget()
        time_layout = QVBoxLayout()
        time_controls = QHBoxLayout()
        time_controls.addWidget(QLabel("Интервал:"))
        self.time_interval_combo = QComboBox()
        self.time_interval_combo.addItems(["hour", "day_of_week", "date"])
        self.time_interval_combo.setItemText(0, "Часы суток")
        self.time_interval_combo.setItemText(1, "Дни недели")
        self.time_interval_combo.setItemText(2, "Даты")
        self.time_interval_combo.currentTextChanged.connect(self._show_time_distribution)
        time_controls.addWidget(self.time_interval_combo)
        time_layout.addLayout(time_controls)
        
        self.time_list = QListWidget()
        time_layout.addWidget(self.time_list)
        time_tab.setLayout(time_layout)
        
        self.analysis_tabs.addTab(dup_tab, "🔁 Дубликаты")
        self.analysis_tabs.addTab(freq_tab, "📊 Частоты")
        self.analysis_tabs.addTab(types_tab, "📋 Типы")
        self.analysis_tabs.addTab(time_tab, "⏰ Время")
        
        main_layout.addWidget(self.analysis_tabs)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
    
    def _browse_logs_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с логами",
            self.logs_dir
        )
        if dir_path:
            self.logs_dir = dir_path
            self.logs_dir_input.setText(dir_path)
            logger.info(f"Путь к логам изменён: {dir_path}")
    
    def _load_logs(self):
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("⏳ Чтение логов...")
        
        start = self.date_from.date().toString("yyyy-MM-dd")
        end = self.date_to.date().toString("yyyy-MM-dd")
        
        max_records_text = self.max_records_combo.currentText()
        max_records = None if max_records_text == "Все" else int(max_records_text)
        
        self.parser_thread = LogParserThread(
            self.logs_dir,
            start,
            end,
            max_records
        )
        self.parser_thread.finished.connect(self._on_parser_finished)
        self.parser_thread.error.connect(self._on_parser_error)
        self.parser_thread.start()
    
    def _on_parser_finished(self, parser):
        self.parser = parser
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        
        self._update_stats()
        self._apply_filters()
        
        msg = f"✅ Загружено {len(self.parser.df)} тревог"
        if self.parser.parse_errors:
            msg += f" (+{len(self.parser.parse_errors)} ошибок)"
        msg += f" | Файлов: {parser.files_processed} обработано, {parser.files_skipped} пропущено"
        self.status_label.setText(msg)
        logger.info(f"Загрузка логов завершена: {msg}")
    
    def _on_parser_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        logger.error(f"Ошибка парсинга логов: {error_msg}")
        QMessageBox.warning(self, "⚠️ Ошибка", f"Не удалось загрузить логи:\n{error_msg}")
        self.status_label.setText("❌ Ошибка загрузки")
    
    def _update_stats(self):
        if not self.parser or self.parser.df is None:
            return
        
        stats = self.parser.get_basic_stats()
        self.stat_total.setText(f"Всего: {stats['total_alarms']}")
        self.stat_auto.setText(f"Автозакрытие: {stats['auto_close']}")
        self.stat_manual.setText(f"Ручное: {stats['manual_close']}")
        self.stat_other.setText(f"Прочее: {stats['other']}")
        self.stat_vin.setText(f"С VIN: {stats['with_vin']}")
        self.stat_contract.setText(f"С договором: {stats['with_contract']}")
        self.stat_files.setText(f"Файлов: {stats['files_processed']} обработано, {stats['files_skipped']} пропущено")
    
    def _reset_date_filter(self):
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_to.setDate(QDate.currentDate())
        self.max_records_combo.setCurrentText("10000")
        self._load_logs()
    
    def _apply_filters(self):
        if not self.parser or self.parser.df is None:
            return
        
        vin = self.filter_vin.text().strip()
        contract = self.filter_contract.text().strip()
        alarm_type = self.filter_type.currentText()
        
        df = self.parser.df.copy()
        
        if vin:
            df = df[df['vin'].astype(str).str.contains(vin, case=False, na=False)]
        
        if contract:
            df = df[df['contract'].astype(str).str.contains(contract, case=False, na=False)]
        
        if alarm_type != "Все типы":
            df = df[df['alarm_type'] == alarm_type]
        
        self.parser.df = df
        self._update_stats()
        
        current_idx = self.analysis_tabs.currentIndex()
        if current_idx == 0:
            self._find_duplicates()
        elif current_idx == 1:
            self._run_frequency_analysis()
        elif current_idx == 2:
            self._show_alarm_types()
        elif current_idx == 3:
            self._show_time_distribution()
    
    def _find_duplicates(self):
        field_map = {
            "VIN": "vin",
            "Договор": "contract",
            "Тип тревоги": "alarm_type"
        }
        field = field_map.get(self.dup_field_combo.currentText(), "vin")
        
        self.dup_list.clear()
        self.status_label.setText("🔍 Поиск дубликатов...")
        
        try:
            if self.parser.df is None or len(self.parser.df) == 0:
                self.dup_list.addItem("ℹ️ Нет данных")
                return
            
            grouped = self.parser.df.groupby(field).size().reset_index(name='count')
            dups = grouped[grouped['count'] >= 2].sort_values('count', ascending=False)
            
            if len(dups) == 0:
                self.dup_list.addItem("✅ Дубликаты не найдены")
                return
            
            for _, row in dups.head(50).iterrows():
                item_text = f"🔁 {row['count']}× | {str(row[field])[:50]}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, {"key": row[field], "count": row['count']})
                self.dup_list.addItem(item)
            
            self.status_label.setText(f"✅ Найдено {len(dups)} групп дубликатов")
        except Exception as e:
            logger.error(f"Ошибка поиска дубликатов: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", str(e))
    
    def _run_frequency_analysis(self):
        field_map = {
            "VIN": "vin",
            "Договор": "contract",
            "Тип тревоги": "alarm_type"
        }
        field = field_map.get(self.freq_field_combo.currentText(), "vin")
        top_n = int(self.freq_top_spin.currentText())
        
        self.freq_list.clear()
        self.status_label.setText(f"📊 Анализ по '{field}'...")
        
        try:
            stats = self.parser.get_frequency_stats(field, top_n=top_n)
            if not stats:
                self.freq_list.addItem("ℹ️ Нет данных")
                return
            
            for i, item in enumerate(stats, 1):
                bar = "█" * min(int(item["percentage"] / 2), 25)
                text = f"{i}. {item['value']} {bar} {item['count']} ({item['percentage']}%)"
                self.freq_list.addItem(text)
            
            self.status_label.setText(f"✅ Показано топ-{len(stats)}")
        except Exception as e:
            logger.error(f"Ошибка частотного анализа: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", str(e))
    
    def _show_alarm_types(self):
        self.types_list.clear()
        self.status_label.setText("📋 Группировка по типам...")
        
        try:
            stats = self.parser.get_alarm_types_distribution()
            if not stats:
                self.types_list.addItem("ℹ️ Нет данных")
                return
            
            total = sum(stats.values())
            for label, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                pct = round(count / total * 100, 1) if total else 0
                bar = "█" * min(pct // 2, 25)
                self.types_list.addItem(f"{label}: {count} ({pct}%) {bar}")
            
            self.status_label.setText(f"✅ Найдено {len(stats)} типов")
        except Exception as e:
            logger.error(f"Ошибка анализа типов: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", str(e))
    
    def _show_time_distribution(self):
        self.time_list.clear()
        interval = self.time_interval_combo.currentText()
        self.status_label.setText(f"⏰ Анализ по '{interval}'...")
        
        try:
            stats = self.parser.get_time_distribution(interval)
            if not stats:
                self.time_list.addItem("ℹ️ Нет данных")
                return
            
            labels = {"hour": "Час", "day_of_week": "День", "date": "Дата"}
            for period, count in stats.items():
                if count > 0:
                    bar = "█" * min(count // 2, 30)
                    self.time_list.addItem(f"{labels.get(interval)} {period}: {count} {bar}")
            
            self.status_label.setText(f"✅ Построено распределение")
        except Exception as e:
            logger.error(f"Ошибка временного анализа: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", str(e))
    
    def _show_export_menu(self):
        if not self.parser or self.parser.df is None:
            QMessageBox.warning(self, "⚠️ Нет данных", "Сначала загрузите логи")
            return
        
        options = {
            "📋 Все тревоги": lambda p: self.parser.export_to_csv(p, "alarms_raw"),
            "📊 Частоты (VIN)": lambda p: self.parser.export_to_csv(p, "frequency", field="vin"),
            "📊 Частоты (Договор)": lambda p: self.parser.export_to_csv(p, "frequency", field="contract"),
            "📋 Типы тревог": lambda p: self.parser.export_to_csv(p, "alarm_types"),
        }
        
        menu = QMenu(self)
        for label, generator in options.items():
            action = QAction(label, self)
            action.triggered.connect(lambda _, g=generator: self._export_csv(g))
            menu.addAction(action)
        
        menu.exec_(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))
    
    def _export_csv(self, generator):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            f"clicker_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV файлы (*.csv);;Все файлы (*)"
        )
        
        if not file_path:
            return
        
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"
        
        try:
            success, message = generator(file_path)
            if success:
                QMessageBox.information(self, "✅ Экспорт", message)
            else:
                QMessageBox.warning(self, "⚠️ Ошибка", message)
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось сохранить:\n{e}")