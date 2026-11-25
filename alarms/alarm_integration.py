# alarms/alarm_integration.py
"""Интеграция тревог с базой изъятых ТС"""

from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtCore import Qt

from seized_vehicles.seized_manager import seized_manager
from utils.logger import logger


def check_seized_vehicle(vin: str, contract: str) -> dict:
    """
    Проверяет, находится ли ТС в базе изъятых
    
    Returns:
        dict с результатами проверки
    """
    result = {
        "found": False,
        "vehicles": [],
        "message": ""
    }
    
    if not vin and not contract:
        return result
    
    vehicles = []
    
    if vin:
        vehicles.extend(seized_manager.search_by_vin(vin))
    
    if contract:
        vehicles.extend(seized_manager.search_by_contract(contract))
    
    # Убираем дубликаты
    seen = set()
    unique_vehicles = []
    for v in vehicles:
        v_id = v.get("id", "")
        if v_id not in seen:
            seen.add(v_id)
            unique_vehicles.append(v)
    
    if unique_vehicles:
        result["found"] = True
        result["vehicles"] = unique_vehicles
        result["message"] = _format_seized_message(unique_vehicles)
    
    return result


def _format_seized_message(vehicles: list) -> str:
    """Форматирует сообщение о найденных изъятых ТС"""
    lines = []
    lines.append("=" * 70)
    lines.append("⚠️  ВНИМАНИЕ! ОБНАРУЖЕНЫ ТС В БАЗЕ ИЗЪЯТЫХ!")
    lines.append("=" * 70)
    lines.append("")
    
    for i, v in enumerate(vehicles, 1):
        lines.append(f"📋 ЗАПИСЬ #{i}")
        lines.append("─" * 60)
        lines.append(f"  📅 Дата изъятия:      {v.get('date', '—')}")
        lines.append(f"  📄 Договор:           {v.get('contract_number', '—')}")
        lines.append(f"  🏢 Лизингодатель:     {v.get('lessor', '—')}")
        lines.append(f"  👤 Лизингополучатель: {v.get('lessee', '—')}")
        lines.append(f"  🚗 Марка ТС:          {v.get('vehicle_brand', '—')}")
        lines.append(f"  🔑 VIN:               {v.get('vin', '—')}")
        lines.append(f"  📛 Госномер:          {v.get('license_plate', '—')}")
        lines.append(f"  📍 Стоянка:           {v.get('storage_address', '—')}")
        lines.append(f"  📤 Выдано со стоянки: {v.get('released_to', '—')}")
        
        flags = []
        if v.get('act_signed'):
            flags.append("Акт составлен")
        if v.get('sts_available'):
            flags.append("СТС в наличии")
        if v.get('photos_in_rososmotr'):
            flags.append("Фото в приложении")
        if flags:
            lines.append(f"  📋 Статус:           {', '.join(flags)}")
        
        if v.get('comment'):
            lines.append(f"  💬 Комментарий:      {v.get('comment')}")
        
        if i < len(vehicles):
            lines.append("")
    
    lines.append("")
    lines.append("═" * 70)
    lines.append("  💡 Рекомендуется проверить актуальность данных по стоянке")
    lines.append("═" * 70)
    
    return "\n".join(lines)


def show_seized_alert(vehicles: list, parent=None):
    """
    Показывает диалог с информацией об изъятых ТС
    """
    if not vehicles:
        return
    
    message = _format_seized_message(vehicles)
    
    dialog = QDialog(parent)
    dialog.setWindowTitle("⚠️ ВНИМАНИЕ! ТС В БАЗЕ ИЗЪЯТЫХ")
    dialog.resize(750, 600)
    dialog.setModal(True)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
    
    layout = QVBoxLayout()
    layout.setSpacing(12)
    
    text_edit = QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setFont(QFont("Consolas", 10))
    text_edit.setPlainText(message)
    layout.addWidget(text_edit)
    
    btn_layout = QHBoxLayout()
    
    close_btn = QPushButton("✅ Принять к сведению")
    close_btn.clicked.connect(dialog.accept)
    close_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px 24px;")
    btn_layout.addStretch()
    btn_layout.addWidget(close_btn)
    
    layout.addLayout(btn_layout)
    
    dialog.setLayout(layout)
    dialog.exec_()