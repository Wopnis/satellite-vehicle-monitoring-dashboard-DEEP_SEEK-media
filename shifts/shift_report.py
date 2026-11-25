# shifts/shift_report.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, 
    QHBoxLayout, QWidget, QFileDialog, QMessageBox, QGridLayout
)
from PyQt5.QtGui import QFont, QTextDocument
from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter
from typing import Optional, List
import json
from datetime import datetime

from utils.logger import logger

# Попытка импорта python-docx
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx не установлен. Установите: pip install python-docx")


def _get_alarm_status_text(alarm: dict) -> str:
    status = alarm.get("status", "active")
    if status == "closed":
        return "✅ ЗАКРЫТА"
    elif status == "worked":
        return "🟢 ОТРАБОТАНА (не закрыта)"
    else:
        return "🔴 АКТИВНАЯ"


def _is_alarm_closed(alarm: dict) -> bool:
    if not alarm:
        return False
    if alarm.get("closed_at"):
        return True
    st = str(alarm.get("status", "")).lower()
    if any(tok in st for tok in ("closed", "закрыт", "закрыта", "закрытие")):
        return True
    return False


def _is_alarm_worked(alarm: dict) -> bool:
    if not alarm:
        return False
    return alarm.get("status") == "worked"


def _is_alarm_active(alarm: dict) -> bool:
    if not alarm:
        return False
    return alarm.get("status") == "active"


def _format_alarm_details(alarm: dict) -> str:
    lines = []
    status_text = _get_alarm_status_text(alarm)
    lines.append(f"  {status_text}")
    lines.append(f"  🚨 VIN: {alarm.get('vin', '—')}")
    lines.append(f"  📄 Договор: {alarm.get('contract', '—')}")
    lines.append(f"  🚗 Марка: {alarm.get('brand', '—')}")
    lines.append(f"  👤 Лизингополучатель: {alarm.get('lessee', '—')}")
    lines.append(f"  📢 Сообщение: {alarm.get('message', '—')}")
    lines.append(f"  🕒 Открыта: {alarm.get('timestamp', '—')}")
    
    closed_at = alarm.get('closed_at', '—')
    if closed_at != '—':
        lines.append(f"  🛑 Закрыта: {closed_at}")
    
    comment = alarm.get('comment', '').strip()
    if comment:
        lines.append(f"  💬 Комментарий: {comment}")
    
    return "\n".join(lines)


def _format_alarm_details_html(alarm: dict) -> str:
    lines = []
    status_text = _get_alarm_status_text(alarm)
    
    status = alarm.get("status", "active")
    if status == "closed":
        color = "#2E7D32"
    elif status == "worked":
        color = "#FF8F00"
    else:
        color = "#C62828"
    
    lines.append(f'<b><font color="{color}">{status_text}</font></b>')
    lines.append(f"🚨 <b>VIN:</b> {alarm.get('vin', '—')}")
    lines.append(f"📄 <b>Договор:</b> {alarm.get('contract', '—')}")
    lines.append(f"🚗 <b>Марка:</b> {alarm.get('brand', '—')}")
    lines.append(f"👤 <b>Лизингополучатель:</b> {alarm.get('lessee', '—')}")
    lines.append(f"📢 <b>Сообщение:</b> {alarm.get('message', '—')}")
    lines.append(f"🕒 <b>Открыта:</b> {alarm.get('timestamp', '—')}")
    
    closed_at = alarm.get('closed_at', '—')
    if closed_at != '—':
        lines.append(f"🛑 <b>Закрыта:</b> {closed_at}")
    
    comment = alarm.get('comment', '').strip()
    if comment:
        lines.append(f"💬 <b>Комментарий:</b> {comment}")
    
    return "<br>".join(lines)


def _generate_report_text(shift: dict, alarms: List[dict]) -> str:
    report_lines = []
    
    report_lines.append("=" * 80)
    report_lines.append("                    ОТЧЁТ ПО СМЕНЕ")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    started = shift.get("started_at", "—")
    ended = shift.get("ended_at", "в процессе")
    report_lines.append(f"📅 Смена: {started} → {ended}")
    report_lines.append(f"🆔 ID смены: {shift.get('id', '—')}")
    
    comment = shift.get("comment", "").strip()
    if comment:
        report_lines.append(f"💬 Комментарий к смене: {comment}")
    
    report_lines.append("")
    
    total = len(alarms)
    closed = sum(1 for a in alarms if _is_alarm_closed(a))
    worked = sum(1 for a in alarms if _is_alarm_worked(a))
    active = total - closed - worked
    
    report_lines.append("=" * 80)
    report_lines.append("                        СТАТИСТИКА ТРЕВОГ")
    report_lines.append("=" * 80)
    report_lines.append(f"📌 Всего тревог: {total}")
    report_lines.append(f"✅ Закрыто: {closed}")
    report_lines.append(f"🟢 Отработано (не закрыто): {worked}")
    report_lines.append(f"🔴 Активных: {active}")
    report_lines.append("")
    
    if total > 0:
        report_lines.append("=" * 80)
        report_lines.append("                    ПОДРОБНЫЙ СПИСОК ТРЕВОГ")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        active_alarms = [a for a in alarms if _is_alarm_active(a)]
        if active_alarms:
            report_lines.append("🔴 АКТИВНЫЕ ТРЕВОГИ:")
            report_lines.append("-" * 80)
            for i, alarm in enumerate(active_alarms, 1):
                report_lines.append(f"\nТревога #{i}:")
                report_lines.append(_format_alarm_details(alarm))
                report_lines.append("-" * 80)
            report_lines.append("")
        
        worked_alarms = [a for a in alarms if _is_alarm_worked(a)]
        if worked_alarms:
            report_lines.append("🟢 ОТРАБОТАННЫЕ (но не закрытые) ТРЕВОГИ:")
            report_lines.append("-" * 80)
            for i, alarm in enumerate(worked_alarms, 1):
                report_lines.append(f"\nТревога #{i}:")
                report_lines.append(_format_alarm_details(alarm))
                report_lines.append("-" * 80)
            report_lines.append("")
        
        closed_alarms = [a for a in alarms if _is_alarm_closed(a)]
        if closed_alarms:
            report_lines.append("✅ ЗАКРЫТЫЕ ТРЕВОГИ:")
            report_lines.append("-" * 80)
            for i, alarm in enumerate(closed_alarms, 1):
                report_lines.append(f"\nТревога #{i}:")
                report_lines.append(_format_alarm_details(alarm))
                report_lines.append("-" * 80)
            report_lines.append("")
    
    journal = shift.get("journal_text", "") or ""
    if journal.strip():
        report_lines.append("=" * 80)
        report_lines.append("                        ЖУРНАЛ СМЕНЫ")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(journal)
    
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("Отчёт сформирован автоматически системой мониторинга")
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)


def _export_to_docx(shift: dict, alarms: List[dict], filepath: str) -> bool:
    """Экспорт отчёта в DOCX с красивым форматированием"""
    if not DOCX_AVAILABLE:
        return False
    
    try:
        doc = Document()
        
        # Заголовок
        title = doc.add_heading('ОТЧЁТ ПО СМЕНЕ', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Информация о смене
        started = shift.get("started_at", "—")
        ended = shift.get("ended_at", "в процессе")
        
        doc.add_paragraph(f'📅 Смена: {started} → {ended}')
        doc.add_paragraph(f'🆔 ID смены: {shift.get("id", "—")}')
        
        comment = shift.get("comment", "").strip()
        if comment:
            doc.add_paragraph(f'💬 Комментарий к смене: {comment}')
        
        doc.add_paragraph()
        
        # Статистика
        total = len(alarms)
        closed = sum(1 for a in alarms if _is_alarm_closed(a))
        worked = sum(1 for a in alarms if _is_alarm_worked(a))
        active = total - closed - worked
        
        doc.add_heading('СТАТИСТИКА ТРЕВОГ', level=1)
        
        # Таблица статистики
        table = doc.add_table(rows=4, cols=2)
        table.style = 'Table Grid'
        
        cells = table.rows[0].cells
        cells[0].text = '📌 Всего тревог'
        cells[1].text = str(total)
        
        cells = table.rows[1].cells
        cells[0].text = '✅ Закрыто'
        cells[1].text = str(closed)
        
        cells = table.rows[2].cells
        cells[0].text = '🟢 Отработано (не закрыто)'
        cells[1].text = str(worked)
        
        cells = table.rows[3].cells
        cells[0].text = '🔴 Активных'
        cells[1].text = str(active)
        
        doc.add_paragraph()
        
        # Подробный список тревог
        if total > 0:
            doc.add_heading('ПОДРОБНЫЙ СПИСОК ТРЕВОГ', level=1)
            
            # Активные тревоги
            active_alarms = [a for a in alarms if _is_alarm_active(a)]
            if active_alarms:
                doc.add_heading('🔴 АКТИВНЫЕ ТРЕВОГИ', level=2)
                for i, alarm in enumerate(active_alarms, 1):
                    p = doc.add_paragraph()
                    p.add_run(f'Тревога #{i}').bold = True
                    doc.add_paragraph(f'  🚨 VIN: {alarm.get("vin", "—")}')
                    doc.add_paragraph(f'  📄 Договор: {alarm.get("contract", "—")}')
                    doc.add_paragraph(f'  🚗 Марка: {alarm.get("brand", "—")}')
                    doc.add_paragraph(f'  👤 Лизингополучатель: {alarm.get("lessee", "—")}')
                    doc.add_paragraph(f'  📢 Сообщение: {alarm.get("message", "—")}')
                    doc.add_paragraph(f'  🕒 Открыта: {alarm.get("timestamp", "—")}')
                    comment = alarm.get('comment', '').strip()
                    if comment:
                        doc.add_paragraph(f'  💬 Комментарий: {comment}')
                    doc.add_paragraph()
            
            # Отработанные тревоги
            worked_alarms = [a for a in alarms if _is_alarm_worked(a)]
            if worked_alarms:
                doc.add_heading('🟢 ОТРАБОТАННЫЕ (но не закрытые) ТРЕВОГИ', level=2)
                for i, alarm in enumerate(worked_alarms, 1):
                    p = doc.add_paragraph()
                    p.add_run(f'Тревога #{i}').bold = True
                    doc.add_paragraph(f'  🚨 VIN: {alarm.get("vin", "—")}')
                    doc.add_paragraph(f'  📄 Договор: {alarm.get("contract", "—")}')
                    doc.add_paragraph(f'  🚗 Марка: {alarm.get("brand", "—")}')
                    doc.add_paragraph(f'  👤 Лизингополучатель: {alarm.get("lessee", "—")}')
                    doc.add_paragraph(f'  📢 Сообщение: {alarm.get("message", "—")}')
                    doc.add_paragraph(f'  🕒 Открыта: {alarm.get("timestamp", "—")}')
                    comment = alarm.get('comment', '').strip()
                    if comment:
                        doc.add_paragraph(f'  💬 Комментарий: {comment}')
                    doc.add_paragraph()
            
            # Закрытые тревоги
            closed_alarms = [a for a in alarms if _is_alarm_closed(a)]
            if closed_alarms:
                doc.add_heading('✅ ЗАКРЫТЫЕ ТРЕВОГИ', level=2)
                for i, alarm in enumerate(closed_alarms, 1):
                    p = doc.add_paragraph()
                    p.add_run(f'Тревога #{i}').bold = True
                    doc.add_paragraph(f'  🚨 VIN: {alarm.get("vin", "—")}')
                    doc.add_paragraph(f'  📄 Договор: {alarm.get("contract", "—")}')
                    doc.add_paragraph(f'  🚗 Марка: {alarm.get("brand", "—")}')
                    doc.add_paragraph(f'  👤 Лизингополучатель: {alarm.get("lessee", "—")}')
                    doc.add_paragraph(f'  📢 Сообщение: {alarm.get("message", "—")}')
                    doc.add_paragraph(f'  🕒 Открыта: {alarm.get("timestamp", "—")}')
                    doc.add_paragraph(f'  🛑 Закрыта: {alarm.get("closed_at", "—")}')
                    comment = alarm.get('comment', '').strip()
                    if comment:
                        doc.add_paragraph(f'  💬 Комментарий: {comment}')
                    doc.add_paragraph()
        
        # Журнал смены
        journal = shift.get("journal_text", "") or ""
        if journal.strip():
            doc.add_heading('ЖУРНАЛ СМЕНЫ', level=1)
            p = doc.add_paragraph()
            p.add_run(journal)
        
        # Подвал
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.add_run('Отчёт сформирован автоматически системой мониторинга').italic = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Сохраняем
        doc.save(filepath)
        return True
        
    except Exception as e:
        logger.error(f"Ошибка экспорта в DOCX: {e}")
        return False


def generate_shift_report(shift: dict, alarm_manager: Optional[object] = None):
    if not shift:
        return
    
    dlg = QDialog()
    dlg.setWindowTitle("📑 Отчёт по смене")
    dlg.resize(900, 750)
    dlg.setModal(True)
    
    layout = QVBoxLayout()
    
    title = QLabel("📑 ОТЧЁТ ПО СМЕНЕ")
    title.setFont(QFont("Segoe UI", 16, QFont.Bold))
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    
    layout.addSpacing(5)
    
    started = shift.get("started_at", "—")
    ended = shift.get("ended_at", "в процессе")
    
    info_layout = QGridLayout()
    info_layout.addWidget(QLabel("<b>📅 Смена:</b>"), 0, 0)
    info_layout.addWidget(QLabel(f"{started} → {ended}"), 0, 1)
    info_layout.addWidget(QLabel("<b>🆔 ID смены:</b>"), 1, 0)
    info_layout.addWidget(QLabel(f"{shift.get('id', '—')}"), 1, 1)
    
    comment = shift.get("comment", "").strip()
    if comment:
        info_layout.addWidget(QLabel("<b>💬 Комментарий:</b>"), 2, 0)
        info_layout.addWidget(QLabel(comment), 2, 1)
    
    layout.addLayout(info_layout)
    layout.addSpacing(10)
    
    alarms = []
    shift_id = shift.get("id")
    if alarm_manager and hasattr(alarm_manager, "alarms"):
        try:
            for a in alarm_manager.alarms:
                if a.get("shift_id") == shift_id:
                    alarms.append(a)
        except Exception as e:
            logger.error(f"Ошибка получения тревог: {e}")
            alarms = []
    
    if not alarms:
        alarms = shift.get("alarms") or shift.get("alarms_list") or []
    
    total = len(alarms)
    closed = sum(1 for a in alarms if _is_alarm_closed(a))
    worked = sum(1 for a in alarms if _is_alarm_worked(a))
    active = total - closed - worked
    
    stats_group = QLabel("<b>📊 СТАТИСТИКА ТРЕВОГ</b>")
    stats_group.setFont(QFont("Segoe UI", 12, QFont.Bold))
    layout.addWidget(stats_group)
    
    stats_layout = QGridLayout()
    stats_layout.setColumnStretch(1, 1)
    stats_layout.setColumnStretch(3, 1)
    
    stats_layout.addWidget(QLabel("📌 Всего тревог:"), 0, 0)
    stats_layout.addWidget(QLabel(f"<span style='font-size:14pt; font-weight:bold;'>{total}</span>"), 0, 1)
    
    stats_layout.addWidget(QLabel("✅ Закрыто:"), 1, 0)
    stats_layout.addWidget(QLabel(f"<span style='color:#2E7D32; font-size:14pt; font-weight:bold;'>{closed}</span>"), 1, 1)
    
    stats_layout.addWidget(QLabel("🟢 Отработано (не закрыто):"), 2, 0)
    stats_layout.addWidget(QLabel(f"<span style='color:#FF8F00; font-size:14pt; font-weight:bold;'>{worked}</span>"), 2, 1)
    
    stats_layout.addWidget(QLabel("🔴 Активных:"), 3, 0)
    stats_layout.addWidget(QLabel(f"<span style='color:#C62828; font-size:14pt; font-weight:bold;'>{active}</span>"), 3, 1)
    
    if total > 0:
        stats_layout.addWidget(QLabel(""), 0, 2)
        stats_layout.addWidget(QLabel(f"<span style='color:#666;'>{round(closed/total*100)}%</span>"), 0, 3)
        stats_layout.addWidget(QLabel(""), 1, 2)
        stats_layout.addWidget(QLabel(f"<span style='color:#FF8F00;'>{round(worked/total*100)}%</span>"), 1, 3)
        stats_layout.addWidget(QLabel(""), 2, 2)
        stats_layout.addWidget(QLabel(f"<span style='color:#C62828;'>{round(active/total*100)}%</span>"), 2, 3)
    
    layout.addLayout(stats_layout)
    layout.addSpacing(10)
    
    line = QLabel("─" * 80)
    line.setStyleSheet("color: #999;")
    layout.addWidget(line)
    layout.addSpacing(5)
    
    list_title = QLabel("<b>📋 ПОДРОБНЫЙ СПИСОК ТРЕВОГ</b>")
    list_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
    layout.addWidget(list_title)
    
    details_box = QTextEdit()
    details_box.setReadOnly(True)
    details_box.setFont(QFont("Segoe UI", 10))
    details_box.setMinimumHeight(300)
    
    details_lines = []
    
    active_alarms = [a for a in alarms if _is_alarm_active(a)]
    if active_alarms:
        details_lines.append(f"<b><span style='color:#C62828;'>🔴 АКТИВНЫЕ ТРЕВОГИ ({len(active_alarms)}):</span></b>")
        details_lines.append("<br>")
        for i, alarm in enumerate(active_alarms, 1):
            details_lines.append(f"<b>Тревога #{i}</b>")
            details_lines.append(_format_alarm_details_html(alarm))
            if i < len(active_alarms):
                details_lines.append("<hr style='border: 1px dashed #ddd;'>")
        details_lines.append("<br>")
    
    worked_alarms = [a for a in alarms if _is_alarm_worked(a)]
    if worked_alarms:
        if active_alarms:
            details_lines.append("<hr style='border: 2px solid #666;'>")
        details_lines.append(f"<b><span style='color:#FF8F00;'>🟢 ОТРАБОТАННЫЕ (но не закрытые) ({len(worked_alarms)}):</span></b>")
        details_lines.append("<br>")
        for i, alarm in enumerate(worked_alarms, 1):
            details_lines.append(f"<b>Тревога #{i}</b>")
            details_lines.append(_format_alarm_details_html(alarm))
            if i < len(worked_alarms):
                details_lines.append("<hr style='border: 1px dashed #ddd;'>")
        details_lines.append("<br>")
    
    closed_alarms = [a for a in alarms if _is_alarm_closed(a)]
    if closed_alarms:
        if active_alarms or worked_alarms:
            details_lines.append("<hr style='border: 2px solid #666;'>")
        details_lines.append(f"<b><span style='color:#2E7D32;'>✅ ЗАКРЫТЫЕ ТРЕВОГИ ({len(closed_alarms)}):</span></b>")
        details_lines.append("<br>")
        for i, alarm in enumerate(closed_alarms, 1):
            details_lines.append(f"<b>Тревога #{i}</b>")
            details_lines.append(_format_alarm_details_html(alarm))
            if i < len(closed_alarms):
                details_lines.append("<hr style='border: 1px dashed #ddd;'>")
        details_lines.append("<br>")
    
    if not details_lines:
        details_lines.append("ℹ️ Нет тревог в этой смене")
    
    details_box.setHtml("<br>".join(details_lines))
    layout.addWidget(details_box)
    
    journal = shift.get("journal_text", "") or ""
    if journal.strip():
        layout.addSpacing(5)
        line2 = QLabel("─" * 80)
        line2.setStyleSheet("color: #999;")
        layout.addWidget(line2)
        
        journal_title = QLabel("<b>🗒️ ЖУРНАЛ СМЕНЫ</b>")
        journal_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(journal_title)
        
        jbox = QTextEdit()
        jbox.setReadOnly(True)
        jbox.setFont(QFont("Courier New", 9))
        jbox.setMaximumHeight(150)
        
        lines = journal.splitlines()
        if len(lines) > 40:
            snippet = "\n".join(lines[:40])
            snippet += "\n...\n(полный текст доступен при экспорте)"
        else:
            snippet = journal
        jbox.setPlainText(snippet)
        layout.addWidget(jbox)
    
    btn_widget = QWidget()
    btn_layout = QHBoxLayout(btn_widget)
    btn_layout.setSpacing(10)
    
    print_btn = QPushButton("🖨️ Печать отчёта")
    print_btn.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
    print_btn.clicked.connect(lambda: _print_report(dlg, shift, alarms))
    
    export_txt_btn = QPushButton("💾 Экспорт в TXT")
    export_txt_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
    export_txt_btn.clicked.connect(lambda: _export_to_txt(dlg, shift, alarms))
    
    export_pdf_btn = QPushButton("📄 Экспорт в PDF")
    export_pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
    export_pdf_btn.clicked.connect(lambda: _export_to_pdf(dlg, shift, alarms))
    
    # Кнопка экспорта в DOCX
    export_docx_btn = QPushButton("📝 Экспорт в DOCX")
    export_docx_btn.setStyleSheet("background-color: #1565C0; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
    export_docx_btn.clicked.connect(lambda: _export_to_docx_dialog(dlg, shift, alarms))
    if not DOCX_AVAILABLE:
        export_docx_btn.setEnabled(False)
        export_docx_btn.setToolTip("Установите python-docx: pip install python-docx")
    
    close_btn = QPushButton("❌ Закрыть")
    close_btn.setStyleSheet("background-color: #888; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
    close_btn.clicked.connect(dlg.accept)
    
    btn_layout.addWidget(print_btn)
    btn_layout.addWidget(export_txt_btn)
    btn_layout.addWidget(export_pdf_btn)
    btn_layout.addWidget(export_docx_btn)
    btn_layout.addStretch()
    btn_layout.addWidget(close_btn)
    
    layout.addWidget(btn_widget)
    
    dlg.setLayout(layout)
    dlg.exec_()


def _export_to_docx_dialog(parent, shift: dict, alarms: List[dict]):
    """Диалог для экспорта в DOCX"""
    if not DOCX_AVAILABLE:
        QMessageBox.warning(
            parent,
            "⚠️ Библиотека не установлена",
            "Для экспорта в DOCX установите:\n\npip install python-docx"
        )
        return
    
    fname, _ = QFileDialog.getSaveFileName(
        parent, 
        "Сохранить отчёт как DOCX", 
        f"отчёт_смена_{shift.get('id', 'unknown')[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
        "Word документ (*.docx);;Все файлы (*)"
    )
    if not fname:
        return
    
    if not fname.lower().endswith(".docx"):
        fname += ".docx"
    
    try:
        success = _export_to_docx(shift, alarms, fname)
        if success:
            QMessageBox.information(parent, "✅ Экспорт", f"Отчёт успешно сохранён:\n{fname}")
        else:
            QMessageBox.warning(parent, "⚠️ Ошибка", "Не удалось сохранить DOCX файл.")
    except Exception as e:
        logger.error(f"Ошибка экспорта DOCX: {e}")
        QMessageBox.critical(parent, "❌ Ошибка", f"Ошибка при сохранении:\n{str(e)}")


def _print_report(parent, shift: dict, alarms: List[dict]):
    try:
        doc = QTextDocument()
        report_text = _generate_report_text(shift, alarms)
        html = f"<pre style='font-family: Courier New, monospace; font-size: 10pt;'>{report_text}</pre>"
        doc.setHtml(html)
        
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, parent)
        if dialog.exec_() == QPrintDialog.Accepted:
            doc.print_(printer)
        
        QMessageBox.information(parent, "Печать", "Отчёт отправлен на печать.")
    except Exception as e:
        logger.error(f"Ошибка печати: {e}")
        QMessageBox.warning(parent, "Ошибка", f"Не удалось напечатать отчёт:\n{str(e)}")


def _export_to_txt(parent, shift: dict, alarms: List[dict]):
    fname, _ = QFileDialog.getSaveFileName(
        parent, 
        "Сохранить отчёт как TXT", 
        f"отчёт_смена_{shift.get('id', 'unknown')[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "Текстовый файл (*.txt);;Все файлы (*)"
    )
    if not fname:
        return
    
    if not fname.lower().endswith(".txt"):
        fname += ".txt"
    
    try:
        report_text = _generate_report_text(shift, alarms)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(report_text)
        QMessageBox.information(parent, "Экспорт", f"Отчёт успешно сохранён:\n{fname}")
    except Exception as e:
        logger.error(f"Ошибка экспорта TXT: {e}")
        QMessageBox.warning(parent, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")


def _export_to_pdf(parent, shift: dict, alarms: List[dict]):
    fname, _ = QFileDialog.getSaveFileName(
        parent, 
        "Сохранить отчёт как PDF", 
        f"отчёт_смена_{shift.get('id', 'unknown')[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        "PDF файл (*.pdf);;Все файлы (*)"
    )
    if not fname:
        return
    
    if not fname.lower().endswith(".pdf"):
        fname += ".pdf"
    
    try:
        doc = QTextDocument()
        report_text = _generate_report_text(shift, alarms)
        html = f"<pre style='font-family: Courier New, monospace; font-size: 10pt; white-space: pre-wrap;'>{report_text}</pre>"
        doc.setHtml(html)
        
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(fname)
        printer.setPageSize(QPrinter.A4)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        
        doc.print_(printer)
        QMessageBox.information(parent, "Экспорт", f"Отчёт успешно сохранён:\n{fname}")
    except Exception as e:
        logger.error(f"Ошибка экспорта PDF: {e}")
        QMessageBox.warning(parent, "Ошибка", f"Не удалось сохранить PDF:\n{str(e)}")