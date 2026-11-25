# alarms/alarm_report_dialog.py
"""Диалог для создания и просмотра отчёта по конкретной тревоге"""

import os
import tempfile
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QFileDialog, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QFont, QTextDocument, QPixmap
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

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


class AlarmReportDialog(QDialog):
    """Диалог для просмотра и экспорта отчёта по тревоге"""
    
    def __init__(self, alarm, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.setWindowTitle(f"📄 Отчёт по тревоге - {alarm.get('vin', '')}")
        self.setModal(True)
        self.resize(850, 700)
        self.setMinimumSize(650, 450)
        self.setSizeGripEnabled(True)
        
        self._temp_thumbnails = []
        
        self._init_ui()
        self._update_report()
    
    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel("📄 ОТЧЁТ ПО ТРЕВОГЕ")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFont(QFont("Consolas", 10))
        self.report_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.report_text.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.3;
            }
        """)
        main_layout.addWidget(self.report_text, 1)
        
        # ---- Кнопки ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.copy_btn = QPushButton("📋 Копировать текст")
        self.copy_btn.setFixedHeight(28)
        self.copy_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 10px;")
        self.copy_btn.clicked.connect(self._copy_report)
        btn_layout.addWidget(self.copy_btn)
        
        self.copy_html_btn = QPushButton("🖼️ Копировать с медиа")
        self.copy_html_btn.setFixedHeight(28)
        self.copy_html_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 10px;")
        self.copy_html_btn.clicked.connect(self._copy_report_html)
        btn_layout.addWidget(self.copy_html_btn)
        
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        btn_layout.addWidget(line)
        
        self.export_txt_btn = QPushButton("💾 TXT")
        self.export_txt_btn.setFixedHeight(28)
        self.export_txt_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 10px;")
        self.export_txt_btn.clicked.connect(self._export_txt)
        btn_layout.addWidget(self.export_txt_btn)
        
        self.export_pdf_btn = QPushButton("📄 PDF")
        self.export_pdf_btn.setFixedHeight(28)
        self.export_pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 10px;")
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        btn_layout.addWidget(self.export_pdf_btn)
        
        self.export_docx_btn = QPushButton("📝 DOCX")
        self.export_docx_btn.setFixedHeight(28)
        self.export_docx_btn.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 10px;")
        self.export_docx_btn.clicked.connect(self._export_docx)
        if not DOCX_AVAILABLE:
            self.export_docx_btn.setEnabled(False)
            self.export_docx_btn.setToolTip("Установите python-docx")
        btn_layout.addWidget(self.export_docx_btn)
        
        self.print_btn = QPushButton("🖨️ Печать")
        self.print_btn.setFixedHeight(28)
        self.print_btn.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 10px;")
        self.print_btn.clicked.connect(self._print_report)
        btn_layout.addWidget(self.print_btn)
        
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("❌ Закрыть")
        self.close_btn.setFixedHeight(28)
        self.close_btn.setStyleSheet("background-color: #888; color: white; font-weight: bold; padding: 4px 16px; border-radius: 4px; font-size: 10px;")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def _cleanup_temp_files(self):
        for path in self._temp_thumbnails:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        self._temp_thumbnails = []
    
    def reject(self):
        self._cleanup_temp_files()
        super().reject()
    
    def accept(self):
        self._cleanup_temp_files()
        super().accept()
    
    def _update_report(self):
        report_text = self._generate_report_text()
        media_html = self._get_media_thumbnails_html()
        
        if media_html:
            full_html = f"<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.3;'>{report_text}</pre><br>{media_html}"
        else:
            full_html = f"<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.3;'>{report_text}</pre>"
        
        self.report_text.setHtml(full_html)
    
    def _get_media_thumbnails_html(self) -> str:
        media_files = self.alarm.get("media", [])
        if not media_files:
            return ""
        
        self._cleanup_temp_files()
        
        html_parts = []
        html_parts.append("<div style='margin-top: 8px;'>")
        html_parts.append("<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.3;'>")
        html_parts.append("=" * 60)
        html_parts.append("  МЕДИАФАЙЛЫ")
        html_parts.append("=" * 60)
        html_parts.append("</pre>")
        html_parts.append("<div style='display: flex; flex-wrap: wrap; gap: 8px; padding: 4px;'>")
        
        for path in media_files:
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
            name = os.path.basename(path)
            ext = os.path.splitext(full_path)[1].lower()
            
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                try:
                    pixmap = QPixmap(full_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(130, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                        scaled.save(temp_file.name, 'PNG')
                        temp_file.close()
                        self._temp_thumbnails.append(temp_file.name)
                        
                        html_parts.append(f'''
                        <div style="display: inline-block; margin: 3px; padding: 3px; border: 1px solid #ddd; border-radius: 4px; background: white; text-align: center; width: 140px;">
                            <img src="{temp_file.name}" style="max-width: 130px; max-height: 100px; border-radius: 4px;" />
                            <br><span style="font-size: 8px; color: #555; word-break: break-all;">{name}</span>
                        </div>
                        ''')
                        continue
                except Exception as e:
                    logger.warning(f"Не удалось создать миниатюру: {e}")
            
            if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                icon = "🎬"
            else:
                icon = "📄"
            
            html_parts.append(f'''
            <div style="display: inline-block; margin: 3px; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; background: #f5f5f5; text-align: center; min-width: 80px;">
                <div style="font-size: 28px;">{icon}</div>
                <span style="font-size: 8px; color: #555; word-break: break-all;">{name}</span>
            </div>
            ''')
        
        html_parts.append("</div>")
        html_parts.append("</div>")
        
        return "".join(html_parts)
    
    def _generate_report_text(self) -> str:
        """Генерирует текст отчёта с компактными интервалами"""
        lines = []
        
        lines.append("=" * 60)
        lines.append("                    ОТЧЁТ ПО ТРЕВОГЕ")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"  Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("  СООБЩЕНИЕ")
        lines.append("-" * 60)
        lines.append(f"  {self.alarm.get('message', '—')}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("  ИНФОРМАЦИЯ О ТРЕВОГЕ")
        lines.append("-" * 60)
        
        status = self.alarm.get("status", "active")
        status_text = {
            "active": "🔴 Активная",
            "worked": "🟢 Отработана",
            "closed": "✅ Закрыта"
        }.get(status, status)
        
        # Компактное отображение информации
        lines.append(f"  Статус:               {status_text}")
        lines.append(f"  Марка ТС:             {self.alarm.get('brand', '—')}")
        lines.append(f"  VIN:                  {self.alarm.get('vin', '—')}")
        lines.append(f"  Госномер:             {self.alarm.get('license', '—')}")
        lines.append(f"  Договор:              {self.alarm.get('contract', '—')}")
        lines.append(f"  Лизингополучатель:    {self.alarm.get('lessee', '—')}")
        lines.append(f"  Открыта:              {self.alarm.get('timestamp', '—')}")
        lines.append(f"  Закрыта:              {self.alarm.get('closed_at', '—')}")
        lines.append("")
        
        comment = self.alarm.get("comment", "").strip()
        if comment:
            lines.append("-" * 60)
            lines.append("  КОММЕНТАРИЙ")
            lines.append("-" * 60)
            # Разбиваем длинный комментарий на строки для читаемости
            comment_lines = comment.split('\n')
            for cl in comment_lines:
                lines.append(f"  {cl}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("  Отчёт сформирован автоматически")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _copy_report(self):
        """Копирует только текст отчёта"""
        report_text = self._generate_report_text()
        clipboard = QApplication.clipboard()
        clipboard.setText(report_text)
        QMessageBox.information(self, "✅ Скопировано", "Текст отчёта скопирован в буфер обмена.")
    
    def _copy_report_html(self):
        """Копирует отчёт с миниатюрами в буфер обмена (HTML)"""
        report_text = self._generate_report_text()
        media_html = self._get_media_thumbnails_html()
        
        if media_html:
            full_html = f"""
            <html>
            <body style="font-family: Consolas, monospace; font-size: 11px; line-height: 1.3; background: #fafafa; padding: 12px;">
                <pre style="font-family: Consolas, monospace; font-size: 11px; line-height: 1.3;">{report_text}</pre>
                <br>
                {media_html}
            </body>
            </html>
            """
        else:
            full_html = f"""
            <html>
            <body style="font-family: Consolas, monospace; font-size: 11px; line-height: 1.3; background: #fafafa; padding: 12px;">
                <pre style="font-family: Consolas, monospace; font-size: 11px; line-height: 1.3;">{report_text}</pre>
            </body>
            </html>
            """
        
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setHtml(full_html)
        mime_data.setText(report_text)
        clipboard.setMimeData(mime_data)
        
        QMessageBox.information(
            self,
            "✅ Скопировано",
            "Отчёт с миниатюрами скопирован в буфер обмена.\n\n"
            "Можно вставить в Word, письмо и другие программы."
        )
    
    def _export_txt(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт как TXT",
            f"отчёт_тревога_{self.alarm.get('vin', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if not filepath:
            return
        
        if not filepath.lower().endswith(".txt"):
            filepath += ".txt"
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self._generate_report_text())
            QMessageBox.information(self, "✅ Экспорт", f"Отчёт сохранён:\n{filepath}")
        except Exception as e:
            logger.error(f"Ошибка экспорта TXT: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось сохранить:\n{str(e)}")
    
    def _export_pdf(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт как PDF",
            f"отчёт_тревога_{self.alarm.get('vin', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF файлы (*.pdf);;Все файлы (*)"
        )
        if not filepath:
            return
        
        if not filepath.lower().endswith(".pdf"):
            filepath += ".pdf"
        
        try:
            doc = QTextDocument()
            report_text = self._generate_report_text()
            html = f"<pre style='font-family: Consolas, monospace; font-size: 11pt; line-height: 1.3;'>{report_text}</pre>"
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(filepath)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            
            doc.print_(printer)
            QMessageBox.information(self, "✅ Экспорт", f"Отчёт сохранён:\n{filepath}")
        except Exception as e:
            logger.error(f"Ошибка экспорта PDF: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось сохранить:\n{str(e)}")
    
    def _export_docx(self):
        if not DOCX_AVAILABLE:
            QMessageBox.warning(self, "⚠️ Библиотека не установлена", "Установите python-docx")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт как DOCX",
            f"отчёт_тревога_{self.alarm.get('vin', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            "Word документ (*.docx);;Все файлы (*)"
        )
        if not filepath:
            return
        
        if not filepath.lower().endswith(".docx"):
            filepath += ".docx"
        
        try:
            doc = Document()
            
            title = doc.add_heading('ОТЧЁТ ПО ТРЕВОГЕ', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.add_paragraph(f'Дата: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
            doc.add_paragraph()
            
            doc.add_heading('Сообщение', level=1)
            doc.add_paragraph(self.alarm.get('message', '—'))
            doc.add_paragraph()
            
            doc.add_heading('Информация', level=1)
            
            status = self.alarm.get("status", "active")
            status_text = {
                "active": "🔴 Активная",
                "worked": "🟢 Отработана",
                "closed": "✅ Закрыта"
            }.get(status, status)
            
            info = [
                ("Статус", status_text),
                ("Марка ТС", self.alarm.get('brand', '—')),
                ("VIN", self.alarm.get('vin', '—')),
                ("Госномер", self.alarm.get('license', '—')),
                ("Договор", self.alarm.get('contract', '—')),
                ("Лизингополучатель", self.alarm.get('lessee', '—')),
                ("Открыта", self.alarm.get('timestamp', '—')),
                ("Закрыта", self.alarm.get('closed_at', '—')),
            ]
            
            for label, value in info:
                p = doc.add_paragraph()
                p.add_run(f'{label}: ').bold = True
                p.add_run(value)
            
            doc.add_paragraph()
            
            comment = self.alarm.get("comment", "").strip()
            if comment:
                doc.add_heading('Комментарий', level=1)
                doc.add_paragraph(comment)
                doc.add_paragraph()
            
            media_files = self.alarm.get("media", [])
            if media_files:
                doc.add_heading('Медиафайлы', level=1)
                for f in media_files:
                    doc.add_paragraph(f'📎 {os.path.basename(f)}')
            
            doc.add_paragraph()
            p = doc.add_paragraph()
            p.add_run('Отчёт сформирован автоматически').italic = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.save(filepath)
            QMessageBox.information(self, "✅ Экспорт", f"Отчёт сохранён:\n{filepath}")
        except Exception as e:
            logger.error(f"Ошибка экспорта DOCX: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось сохранить:\n{str(e)}")
    
    def _print_report(self):
        try:
            doc = QTextDocument()
            report_text = self._generate_report_text()
            html = f"<pre style='font-family: Consolas, monospace; font-size: 11pt; line-height: 1.3;'>{report_text}</pre>"
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec_() == QPrintDialog.Accepted:
                doc.print_(printer)
                QMessageBox.information(self, "✅ Печать", "Отчёт отправлен на печать.")
        except Exception as e:
            logger.error(f"Ошибка печати: {e}")
            QMessageBox.critical(self, "❌ Ошибка", f"Не удалось напечатать:\n{str(e)}")