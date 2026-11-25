# analytics/analytics_tab.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QGroupBox, QGridLayout,
    QListWidget, QListWidgetItem, QTabWidget,
    QMessageBox, QMenu, QAction, QDialog, QTextEdit,
    QDialogButtonBox, QFileDialog, QProgressBar, QCheckBox,
    QLineEdit  # ✅ ДОБАВЛЕНО
)
from PyQt5.QtCore import Qt, QDate, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from .analyzer import AlarmAnalyzer
from .export_utils import save_csv_dialog
from datetime import datetime
import os

from utils.logger import logger

# Попытка импорта для DOCX
DOCX_AVAILABLE = False
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    DOCX_AVAILABLE = True
except ImportError:
    pass

FIELD_NAMES = {
    "vin": "VIN",
    "contract": "Договор",
    "lessee": "Лизингополучатель",
    "brand": "Марка ТС",
    "message": "Сообщение",
    "alarm_text": "Текст тревоги"
}


class ExportThread(QThread):
    """Поток для экспорта отчётов (не блокирует UI)"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    
    def __init__(self, analyzer, export_type, filepath, **kwargs):
        super().__init__()
        self.analyzer = analyzer
        self.export_type = export_type
        self.filepath = filepath
        self.kwargs = kwargs
    
    def run(self):
        try:
            if self.export_type == "full_report":
                success, msg = self._export_full_report()
            elif self.export_type == "docx":
                success, msg = self._export_docx()
            else:
                success, msg = self.analyzer.export_to_csv(self.filepath, self.export_type, **self.kwargs)
            
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def _export_full_report(self):
        """Экспорт полного отчёта в DOCX"""
        if not DOCX_AVAILABLE:
            return False, "python-docx не установлен"
        
        try:
            doc = Document()
            
            # Заголовок
            title = doc.add_heading('ОТЧЁТ ПО ДЕМОНТАЖАМ', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Дата отчёта
            doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
            doc.add_paragraph()
            
            # Статистика
            stats = self.analyzer.get_basic_stats()
            doc.add_heading('СТАТИСТИКА', level=1)
            
            table = doc.add_table(rows=3, cols=2)
            table.style = 'Table Grid'
            table.rows[0].cells[0].text = '📌 Всего тревог'
            table.rows[0].cells[1].text = str(stats['total'])
            table.rows[1].cells[0].text = '🟢 Активные'
            table.rows[1].cells[1].text = str(stats['active'])
            table.rows[2].cells[0].text = '✅ Закрытые'
            table.rows[2].cells[1].text = str(stats['closed'])
            
            doc.add_paragraph()
            
            # Типы тревог
            types = self.analyzer.get_alarm_types_distribution()
            if types:
                doc.add_heading('ТИПЫ ТРЕВОГ', level=1)
                for label, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
                    doc.add_paragraph(f'  {label}: {count}')
            
            doc.add_paragraph()
            
            # Топ по VIN
            vin_stats = self.analyzer.get_frequency_stats('vin', top_n=20)
            if vin_stats:
                doc.add_heading('ТОП-20 ПО VIN', level=1)
                for i, item in enumerate(vin_stats, 1):
                    doc.add_paragraph(f'  {i}. {item["value"]} — {item["count"]} ({item["percentage"]}%)')
            
            # Подвал
            doc.add_paragraph()
            p = doc.add_paragraph()
            p.add_run('Отчёт сформирован автоматически').italic = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.save(self.filepath)
            return True, f"Отчёт сохранён: {self.filepath}"
        except Exception as e:
            return False, str(e)
    
    def _export_docx(self):
        """Экспорт детального отчёта в DOCX"""
        if not DOCX_AVAILABLE:
            return False, "python-docx не установлен"
        
        try:
            doc = Document()
            
            title = doc.add_heading('ДЕТАЛЬНЫЙ ОТЧЁТ ПО ДЕМОНТАЖАМ', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
            doc.add_paragraph()
            
            # Список тревог
            alarms = self.analyzer.alarms
            if alarms:
                doc.add_heading('СПИСОК ТРЕВОГ', level=1)
                for i, alarm in enumerate(alarms, 1):
                    p = doc.add_paragraph()
                    p.add_run(f'Тревога #{i}').bold = True
                    doc.add_paragraph(f'  🚨 VIN: {alarm.get("vin", "—")}')
                    doc.add_paragraph(f'  📄 Договор: {alarm.get("contract", "—")}')
                    doc.add_paragraph(f'  🚗 Марка: {alarm.get("brand", "—")}')
                    doc.add_paragraph(f'  👤 Лизингополучатель: {alarm.get("lessee", "—")}')
                    doc.add_paragraph(f'  📢 Сообщение: {alarm.get("message", "—")}')
                    doc.add_paragraph(f'  🕒 Открыта: {alarm.get("timestamp", "—")}')
                    if alarm.get("closed_at"):
                        doc.add_paragraph(f'  🛑 Закрыта: {alarm.get("closed_at", "—")}')
                    doc.add_paragraph()
            
            doc.save(self.filepath)
            return True, f"Отчёт сохранён: {self.filepath}"
        except Exception as e:
            return False, str(e)


class AnalyticsTab(QWidget):
    def __init__(self, alarms_file: str = "data/alarms.json", parent=None):
        super().__init__(parent)
        self.alarms_file = alarms_file
        self.analyzer = None
        self.export_thread = None
        
        self._init_ui()
        self._load_data()
    
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
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        
        # ---- Верхняя панель ----
        header_layout = QHBoxLayout()
        header_label = QLabel("📊 Аналитика демонтажей")
        header_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.refresh_btn.clicked.connect(self._load_data)
        header_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("💾 Экспорт")
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.export_btn.clicked.connect(self._show_export_menu)
        header_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(header_layout)
        
        # ---- Фильтры ----
        filter_group = QGroupBox("📅 Фильтры")
        filter_layout = QGridLayout()
        filter_layout.setSpacing(8)
        
        # Дата с
        filter_layout.addWidget(QLabel("С:"), 0, 0)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        filter_layout.addWidget(self.date_from, 0, 1)
        
        # Дата по
        filter_layout.addWidget(QLabel("По:"), 0, 2)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        filter_layout.addWidget(self.date_to, 0, 3)
        
        # Кнопки фильтра
        self.apply_filter_btn = QPushButton("✅ Применить фильтр")
        self.apply_filter_btn.setStyleSheet("background-color: #27AE60; color: white;")
        self.apply_filter_btn.clicked.connect(self._apply_date_filter)
        filter_layout.addWidget(self.apply_filter_btn, 0, 4)
        
        self.reset_filter_btn = QPushButton("🔄 Сбросить")
        self.reset_filter_btn.setStyleSheet("background-color: #E67E22; color: white;")
        self.reset_filter_btn.clicked.connect(self._reset_date_filter)
        filter_layout.addWidget(self.reset_filter_btn, 0, 5)
        
        # Фильтр по статусу
        filter_layout.addWidget(QLabel("Статус:"), 1, 0)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Все", "Активные", "Закрытые", "Отработанные"])
        self.status_filter.currentTextChanged.connect(self._apply_status_filter)
        filter_layout.addWidget(self.status_filter, 1, 1)
        
        # Фильтр по VIN
        filter_layout.addWidget(QLabel("VIN:"), 1, 2)
        self.vin_filter = QLineEdit()
        self.vin_filter.setPlaceholderText("Поиск по VIN...")
        self.vin_filter.textChanged.connect(self._apply_vin_filter)
        filter_layout.addWidget(self.vin_filter, 1, 3)
        
        # Чекбокс "Показать только с медиа"
        self.media_only_check = QCheckBox("Только с медиа")
        self.media_only_check.stateChanged.connect(self._apply_media_filter)
        filter_layout.addWidget(self.media_only_check, 1, 4)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # ---- Прогресс ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # ---- Статистика ----
        stats_group = QGroupBox("📈 Статистика")
        stats_layout = QGridLayout()
        
        self.stat_total = QLabel("Всего: —")
        self.stat_active = QLabel("Активные: —")
        self.stat_worked = QLabel("Отработано: —")
        self.stat_closed = QLabel("Закрытые: —")
        self.stat_range = QLabel("Период: —")
        self.stat_media = QLabel("С медиа: —")
        
        stats_layout.addWidget(self.stat_total, 0, 0)
        stats_layout.addWidget(self.stat_active, 0, 1)
        stats_layout.addWidget(self.stat_worked, 0, 2)
        stats_layout.addWidget(self.stat_closed, 1, 0)
        stats_layout.addWidget(self.stat_range, 1, 1)
        stats_layout.addWidget(self.stat_media, 1, 2)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # ---- Вкладки с аналитикой ----
        self.analysis_tabs = QTabWidget()
        
        # 1. Общая аналитика
        general_tab = self._create_general_tab()
        self.analysis_tabs.addTab(general_tab, "📊 Общая")
        
        # 2. Дубликаты
        dup_tab = self._create_duplicates_tab()
        self.analysis_tabs.addTab(dup_tab, "🔁 Дубликаты")
        
        # 3. Частоты
        freq_tab = self._create_frequency_tab()
        self.analysis_tabs.addTab(freq_tab, "📊 Частоты")
        
        # 4. Типы
        types_tab = self._create_types_tab()
        self.analysis_tabs.addTab(types_tab, "📋 Типы")
        
        # 5. Время
        time_tab = self._create_time_tab()
        self.analysis_tabs.addTab(time_tab, "⏰ Время")
        
        main_layout.addWidget(self.analysis_tabs)
        
        # ---- Статус ----
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
    
    def _create_general_tab(self):
        """Создаёт вкладку общей аналитики"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Кнопки для экспорта общих отчётов
        btn_layout = QHBoxLayout()
        
        self.full_report_btn = QPushButton("📊 Полный отчёт (DOCX)")
        self.full_report_btn.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold;")
        self.full_report_btn.clicked.connect(self._export_full_report)
        if not DOCX_AVAILABLE:
            self.full_report_btn.setEnabled(False)
            self.full_report_btn.setToolTip("Установите python-docx")
        btn_layout.addWidget(self.full_report_btn)
        
        self.detail_report_btn = QPushButton("📄 Детальный отчёт (DOCX)")
        self.detail_report_btn.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold;")
        self.detail_report_btn.clicked.connect(self._export_detailed_report)
        if not DOCX_AVAILABLE:
            self.detail_report_btn.setEnabled(False)
            self.detail_report_btn.setToolTip("Установите python-docx")
        btn_layout.addWidget(self.detail_report_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Список тревог (общий)
        layout.addWidget(QLabel("📋 Список тревог за период:"))
        self.general_list = QListWidget()
        self.general_list.itemDoubleClicked.connect(self._show_alarm_details)
        layout.addWidget(self.general_list)
        
        tab.setLayout(layout)
        return tab
    
    def _create_duplicates_tab(self):
        """Создаёт вкладку дубликатов"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Искать дубли по:"))
        self.dup_field_combo = QComboBox()
        self.dup_field_combo.addItems(["VIN + Договор", "VIN", "Договор", "Сообщение"])
        controls.addWidget(self.dup_field_combo)
        
        self.find_dups_btn = QPushButton("🔍 Найти")
        self.find_dups_btn.clicked.connect(self._find_duplicates)
        controls.addWidget(self.find_dups_btn)
        layout.addLayout(controls)
        
        self.dup_list = QListWidget()
        self.dup_list.itemDoubleClicked.connect(self._show_dup_details)
        layout.addWidget(self.dup_list)
        
        tab.setLayout(layout)
        return tab
    
    def _create_frequency_tab(self):
        """Создаёт вкладку частот"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Анализ по полю:"))
        self.freq_field_combo = QComboBox()
        self.freq_field_combo.addItems(["vin", "contract", "lessee", "brand"])
        self.freq_field_combo.setItemText(0, "VIN")
        self.freq_field_combo.setItemText(1, "Договор")
        self.freq_field_combo.setItemText(2, "Лизингополучатель")
        self.freq_field_combo.setItemText(3, "Марка ТС")
        self.freq_field_combo.currentTextChanged.connect(self._run_frequency_analysis)
        controls.addWidget(self.freq_field_combo)
        
        controls.addWidget(QLabel("Топ:"))
        self.freq_top_spin = QComboBox()
        self.freq_top_spin.addItems(["10", "20", "50", "100"])
        self.freq_top_spin.setCurrentText("20")
        self.freq_top_spin.currentTextChanged.connect(self._run_frequency_analysis)
        controls.addWidget(self.freq_top_spin)
        layout.addLayout(controls)
        
        self.freq_list = QListWidget()
        self.freq_list.itemDoubleClicked.connect(self._show_freq_details)
        layout.addWidget(self.freq_list)
        
        tab.setLayout(layout)
        return tab
    
    def _create_types_tab(self):
        """Создаёт вкладку типов"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.show_types_btn = QPushButton("📋 Показать распределение")
        self.show_types_btn.clicked.connect(self._show_alarm_types)
        layout.addWidget(self.show_types_btn)
        
        self.types_list = QListWidget()
        self.types_list.itemDoubleClicked.connect(self._show_types_details)
        layout.addWidget(self.types_list)
        
        tab.setLayout(layout)
        return tab
    
    def _create_time_tab(self):
        """Создаёт вкладку времени"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Интервал:"))
        self.time_interval_combo = QComboBox()
        self.time_interval_combo.addItems(["hour", "day_of_week", "date"])
        self.time_interval_combo.setItemText(0, "Часы суток")
        self.time_interval_combo.setItemText(1, "Дни недели")
        self.time_interval_combo.setItemText(2, "Даты")
        self.time_interval_combo.currentTextChanged.connect(self._show_time_distribution)
        controls.addWidget(self.time_interval_combo)
        layout.addLayout(controls)
        
        self.time_list = QListWidget()
        self.time_list.itemDoubleClicked.connect(self._show_time_details)
        layout.addWidget(self.time_list)
        
        tab.setLayout(layout)
        return tab
    
    def _load_data(self):
        """Загрузка и первичный анализ данных"""
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("⏳ Загрузка данных...")
        self.repaint()
        
        try:
            self.analyzer = AlarmAnalyzer(self.alarms_file)
            errors = self.analyzer.get_load_errors()
            if errors:
                QMessageBox.warning(self, "⚠️ Предупреждение", 
                                  "При загрузке данных возникли проблемы:\n" + "\n".join(errors))
            
            self._update_stats()
            self._update_general_list()
            self._run_frequency_analysis()
            
            self.status_label.setText(f"✅ Загружено {self.analyzer.get_basic_stats()['total']} записей")
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось загрузить данные:\n{e}")
            self.status_label.setText("❌ Ошибка загрузки")
        finally:
            self.refresh_btn.setEnabled(True)
    
    def _update_stats(self):
        """Обновляет статистику"""
        if not self.analyzer:
            return
        
        stats = self.analyzer.get_basic_stats()
        self.stat_total.setText(f"Всего: {stats['total']}")
        self.stat_active.setText(f"Активные: {stats['active']}")
        self.stat_closed.setText(f"Закрытые: {stats['closed']}")
        self.stat_range.setText(f"Период: {stats['date_range']}")
        
        # Подсчёт отработанных
        worked = sum(1 for a in self.analyzer.alarms if a.get("status") == "worked")
        self.stat_worked.setText(f"Отработано: {worked}")
        
        # Подсчёт с медиа
        with_media = sum(1 for a in self.analyzer.alarms if a.get("media"))
        self.stat_media.setText(f"С медиа: {with_media}")
    
    def _update_general_list(self):
        """Обновляет общий список тревог"""
        self.general_list.clear()
        
        if not self.analyzer or not self.analyzer.alarms:
            self.general_list.addItem("ℹ️ Нет данных")
            return
        
        for alarm in self.analyzer.alarms:
            vin = alarm.get("vin", "")
            contract = alarm.get("contract", "")
            brand = alarm.get("brand", "")
            status = alarm.get("status", "active")
            timestamp = alarm.get("timestamp", "")
            has_media = "📎" if alarm.get("media") else ""
            
            status_icon = {
                "active": "🔴",
                "worked": "🟢",
                "closed": "✅"
            }.get(status, "❓")
            
            display_text = f"{status_icon} {timestamp} | {vin} | {contract} | {brand} {has_media}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, alarm)
            self.general_list.addItem(item)
    
    def _show_alarm_details(self, item):
        """Показывает детали тревоги из общего списка"""
        alarm = item.data(Qt.UserRole)
        if not alarm:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📄 Детали тревоги - {alarm.get('vin', '')}")
        dialog.resize(600, 500)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Segoe UI", 11))
        
        info = []
        info.append("=" * 60)
        info.append("          ДЕТАЛИ ТРЕВОГИ")
        info.append("=" * 60)
        info.append("")
        info.append(f"  🚗 Марка:     {alarm.get('brand', '—')}")
        info.append(f"  🔑 VIN:       {alarm.get('vin', '—')}")
        info.append(f"  📛 Госномер:  {alarm.get('license', '—')}")
        info.append(f"  📄 Договор:   {alarm.get('contract', '—')}")
        info.append(f"  👤 Лизингополучатель: {alarm.get('lessee', '—')}")
        info.append(f"  📢 Сообщение: {alarm.get('message', '—')}")
        info.append(f"  💬 Комментарий: {alarm.get('comment', '—')}")
        info.append(f"  🕒 Открыта:   {alarm.get('timestamp', '—')}")
        
        if alarm.get('closed_at'):
            info.append(f"  🛑 Закрыта:   {alarm.get('closed_at', '—')}")
        
        info.append(f"  📎 Медиа:     {'есть' if alarm.get('media') else 'нет'}")
        info.append("")
        info.append("=" * 60)
        
        text.setPlainText("\n".join(info))
        layout.addWidget(text)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _apply_date_filter(self):
        """Применяет фильтр по датам"""
        if not self.analyzer:
            return
        
        start = self.date_from.date().toString("yyyy-MM-dd")
        end = self.date_to.date().toString("yyyy-MM-dd")
        
        self.status_label.setText(f"⏳ Фильтрация: {start} — {end}...")
        self.repaint()
        
        try:
            self.analyzer = self.analyzer.filter_by_date_range(start, end)
            self._update_stats()
            self._update_general_list()
            
            current_idx = self.analysis_tabs.currentIndex()
            if current_idx == 1:
                self._find_duplicates()
            elif current_idx == 2:
                self._run_frequency_analysis()
            elif current_idx == 3:
                self._show_alarm_types()
            elif current_idx == 4:
                self._show_time_distribution()
            
            self.status_label.setText(f"✅ Отфильтровано: {len(self.analyzer.alarms)} записей")
        except Exception as e:
            logger.error(f"Ошибка фильтрации: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", f"Не удалось применить фильтр:\n{e}")
            self.status_label.setText("❌ Ошибка фильтрации")
    
    def _reset_date_filter(self):
        """Сброс фильтра"""
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.status_filter.setCurrentIndex(0)
        self.vin_filter.clear()
        self.media_only_check.setChecked(False)
        self._load_data()
    
    def _apply_status_filter(self):
        """Фильтр по статусу"""
        # TODO: реализовать фильтрацию по статусу
        pass
    
    def _apply_vin_filter(self):
        """Фильтр по VIN"""
        # TODO: реализовать фильтрацию по VIN
        pass
    
    def _apply_media_filter(self):
        """Фильтр по наличию медиа"""
        # TODO: реализовать фильтрацию по медиа
        pass
    
    def _find_duplicates(self):
        """Поиск дубликатов"""
        mapping = {
            "VIN + Договор": ["vin", "contract"],
            "VIN": ["vin"],
            "Договор": ["contract"],
            "Сообщение": ["message"]
        }
        fields = mapping.get(self.dup_field_combo.currentText(), ["vin", "contract"])
        
        self.dup_list.clear()
        self.status_label.setText("🔍 Поиск дубликатов...")
        
        try:
            dups = self.analyzer.find_duplicates(by_fields=fields, min_count=2)
            if not dups:
                self.dup_list.addItem("✅ Дубликаты не найдены")
                self.status_label.setText("✅ Дубликаты: не найдено")
                return
            
            for dup in dups[:50]:
                field_names_ru = " + ".join([FIELD_NAMES.get(f, f) for f in dup['fields']])
                item_text = f"🔁 {dup['count']}× | {dup['key'][:60]}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, dup)
                item.setToolTip(f"Поля: {field_names_ru}\n{dup['key']}")
                self.dup_list.addItem(item)
            
            self.status_label.setText(f"✅ Найдено {len(dups)} групп дубликатов")
        except Exception as e:
            logger.error(f"Ошибка поиска дубликатов: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", f"Не удалось найти дубликаты:\n{e}")
    
    def _show_dup_details(self, item):
        """Показ деталей дубликата"""
        dup = item.data(Qt.UserRole)
        if not dup:
            return
        
        details = f"🔁 Группа дубликатов\n"
        details += "=" * 60 + "\n"
        details += f"📋 Поля поиска: {', '.join(dup['fields'])}\n"
        details += f"🔢 Количество повторений: {dup['count']} раз(а)\n"
        details += f"🕐 Первое появление: {dup['first_seen']}\n"
        details += f"🕐 Последнее появление: {dup['last_seen']}\n"
        details += "=" * 60 + "\n"
        details += f"📄 Пример сообщения:\n{dup['sample_message']}\n"
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 Детали дубликатов")
        dialog.resize(600, 400)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(details)
        layout.addWidget(text)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _run_frequency_analysis(self):
        """Частотный анализ"""
        if not self.analyzer:
            return
        
        field_index = self.freq_field_combo.currentIndex()
        field_map = ["vin", "contract", "lessee", "brand"]
        field = field_map[field_index] if field_index < len(field_map) else "vin"
        
        top_n = int(self.freq_top_spin.currentText())
        
        self.freq_list.clear()
        self.status_label.setText(f"📊 Анализ по '{FIELD_NAMES.get(field, field)}'...")
        
        try:
            stats = self.analyzer.get_frequency_stats(field, top_n=top_n)
            if not stats:
                self.freq_list.addItem("ℹ️ Нет данных для анализа")
                return
            
            field_label = FIELD_NAMES.get(field, field)
            
            for i, item in enumerate(stats, 1):
                bar = "█" * min(int(item["percentage"] / 2), 25)
                text = f"{i}. {item['value']} {bar} {item['count']} ({item['percentage']}%)"
                list_item = QListWidgetItem(text)
                list_item.setData(Qt.UserRole, item)
                self.freq_list.addItem(list_item)
            
            self.status_label.setText(f"✅ Показано топ-{len(stats)} по '{field_label}'")
        except Exception as e:
            logger.error(f"Ошибка частотного анализа: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", f"Не удалось выполнить анализ:\n{e}")
    
    def _show_freq_details(self, item):
        """Показ деталей частотного анализа"""
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        details = (
            f"📊 Детали частотного анализа\n"
            f"{'='*50}\n"
            f"Значение: {data.get('value', 'N/A')}\n"
            f"Количество: {data.get('count', 0)}\n"
            f"Процент от общего: {data.get('percentage', 0)}%\n"
            f"{'='*50}\n"
            f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 Детали частот")
        dialog.resize(500, 300)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(details)
        layout.addWidget(text)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _show_alarm_types(self):
        """Показать распределение по типам тревог"""
        if not self.analyzer:
            return
        
        self.types_list.clear()
        self.status_label.setText("📋 Группировка по типам...")
        
        try:
            stats = self.analyzer.get_alarm_types_distribution()
            if not stats:
                self.types_list.addItem("ℹ️ Нет данных для анализа")
                return
            
            total = sum(stats.values())
            for label, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                pct = round(count / total * 100, 1) if total else 0
                bar = "█" * min(pct // 2, 25)
                item_text = f"{label}: {count} ({pct}%) {bar}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, {"label": label, "count": count, "percentage": pct})
                self.types_list.addItem(item)
            
            self.status_label.setText(f"✅ Найдено {len(stats)} типов тревог")
        except Exception as e:
            logger.error(f"Ошибка анализа типов: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", f"Не удалось проанализировать типы:\n{e}")
    
    def _show_types_details(self, item):
        """Показ деталей типов тревог"""
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        details = (
            f"📋 Тип тревоги\n"
            f"{'='*50}\n"
            f"Название: {data.get('label', 'N/A')}\n"
            f"Количество: {data.get('count', 0)}\n"
            f"Процент: {data.get('percentage', 0)}%\n"
            f"{'='*50}\n"
            f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 Детали типа")
        dialog.resize(500, 300)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(details)
        layout.addWidget(text)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _show_time_distribution(self):
        """Показать распределение по времени"""
        if not self.analyzer:
            return
        
        self.time_list.clear()
        interval = self.time_interval_combo.currentText()
        self.status_label.setText(f"⏰ Анализ по '{interval}'...")
        
        try:
            stats = self.analyzer.get_time_distribution(interval)
            if not stats:
                self.time_list.addItem("ℹ️ Нет данных для анализа")
                return
            
            labels = {
                "hour": "Час",
                "day_of_week": "День недели", 
                "date": "Дата"
            }
            
            for period, count in stats.items():
                if count > 0:
                    bar = "█" * min(count // 2, 30)
                    item_text = f"{labels.get(interval, '')} {period}: {count} {bar}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, {"period": period, "count": count})
                    self.time_list.addItem(item)
            
            self.status_label.setText(f"✅ Построено распределение по '{interval}'")
        except Exception as e:
            logger.error(f"Ошибка временного анализа: {e}")
            QMessageBox.warning(self, "⚠️ Ошибка", f"Не удалось проанализировать время:\n{e}")
    
    def _show_time_details(self, item):
        """Показ деталей временного распределения"""
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        details = (
            f"⏰ Временное распределение\n"
            f"{'='*50}\n"
            f"Период: {data.get('period', 'N/A')}\n"
            f"Количество тревог: {data.get('count', 0)}\n"
            f"{'='*50}\n"
            f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("⏰ Детали времени")
        dialog.resize(500, 300)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(details)
        layout.addWidget(text)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _show_export_menu(self):
        """Показывает меню экспорта"""
        if not self.analyzer:
            QMessageBox.warning(self, "⚠️ Нет данных", "Сначала загрузите данные для анализа")
            return
        
        menu = QMenu(self)
        
        # CSV экспорт
        csv_menu = menu.addMenu("📊 CSV")
        
        csv_options = {
            "🔁 Дубликаты": lambda p: self.analyzer.export_to_csv(p, "duplicates", by_fields=["vin", "contract"]),
            "📊 Частоты (VIN)": lambda p: self.analyzer.export_to_csv(p, "frequency", field="vin"),
            "📊 Частоты (Договор)": lambda p: self.analyzer.export_to_csv(p, "frequency", field="contract"),
            "📋 Типы тревог": lambda p: self.analyzer.export_to_csv(p, "alarm_types"),
            "⏰ По часам": lambda p: self.analyzer.export_to_csv(p, "time_distribution", interval="hour"),
            "⏰ По дням недели": lambda p: self.analyzer.export_to_csv(p, "time_distribution", interval="day_of_week")
        }
        
        for label, generator in csv_options.items():
            action = QAction(label, self)
            action.triggered.connect(lambda _, g=generator: save_csv_dialog(self, "analytics_report", g))
            csv_menu.addAction(action)
        
        # DOCX экспорт (если доступен)
        if DOCX_AVAILABLE:
            menu.addSeparator()
            docx_action = QAction("📝 Полный отчёт (DOCX)", self)
            docx_action.triggered.connect(self._export_full_report)
            menu.addAction(docx_action)
            
            docx_detail_action = QAction("📄 Детальный отчёт (DOCX)", self)
            docx_detail_action.triggered.connect(self._export_detailed_report)
            menu.addAction(docx_detail_action)
        
        menu.exec_(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))
    
    def _export_full_report(self):
        """Экспорт полного отчёта в DOCX"""
        if not self.analyzer or not self.analyzer.alarms:
            QMessageBox.warning(self, "⚠️ Нет данных", "Нет данных для экспорта")
            return
        
        if not DOCX_AVAILABLE:
            QMessageBox.warning(self, "⚠️ Библиотека не установлена", "Установите python-docx")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить полный отчёт",
            f"полный_отчёт_демонтажи_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            "Word документ (*.docx);;Все файлы (*)"
        )
        if not filepath:
            return
        
        if not filepath.lower().endswith(".docx"):
            filepath += ".docx"
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.export_thread = ExportThread(self.analyzer, "full_report", filepath)
        self.export_thread.finished.connect(self._on_export_finished)
        self.export_thread.start()
    
    def _export_detailed_report(self):
        """Экспорт детального отчёта в DOCX"""
        if not self.analyzer or not self.analyzer.alarms:
            QMessageBox.warning(self, "⚠️ Нет данных", "Нет данных для экспорта")
            return
        
        if not DOCX_AVAILABLE:
            QMessageBox.warning(self, "⚠️ Библиотека не установлена", "Установите python-docx")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить детальный отчёт",
            f"детальный_отчёт_демонтажи_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            "Word документ (*.docx);;Все файлы (*)"
        )
        if not filepath:
            return
        
        if not filepath.lower().endswith(".docx"):
            filepath += ".docx"
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.export_thread = ExportThread(self.analyzer, "docx", filepath)
        self.export_thread.finished.connect(self._on_export_finished)
        self.export_thread.start()
    
    def _on_export_finished(self, success, message):
        """Обработчик завершения экспорта"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "✅ Экспорт завершён", message)
        else:
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось экспортировать отчёт:\n{message}")