# utils/exact_search.py
"""Модуль точного поиска по VIN и договору"""

import json
import os
import re
from typing import List, Dict, Optional

from config.paths import PATHS
from utils.logger import logger


def exact_search_by_vin_or_contract(vin: Optional[str] = None, contract: Optional[str] = None) -> List[Dict]:
    """Выполняет точный поиск по VIN и/или номеру договора"""
    if not vin and not contract:
        return []

    results = []

    # Поиск в тревогах
    if os.path.exists(PATHS["alarms"]):
        try:
            with open(PATHS["alarms"], "r", encoding="utf-8") as f:
                alarms = json.load(f)
                for alarm in alarms:
                    match = False
                    if vin and alarm.get("vin") == vin:
                        match = True
                    if contract and alarm.get("contract") == contract:
                        match = True
                    if not (vin or contract):
                        continue

                    if match:
                        timestamp = alarm.get("timestamp", "-")
                        closed_at = alarm.get("closed_at")
                        tooltip_parts = [
                            f"Марка: {alarm.get('brand', '')}",
                            f"Лизингополучатель: {alarm.get('lessee', '')}",
                            f"Открыта: {timestamp}"
                        ]
                        if closed_at:
                            tooltip_parts.append(f"Закрыта: {closed_at}")

                        results.append({
                            "source": "alarm",
                            "text": f"[Тревога] {timestamp} | {alarm.get('vin')} | {alarm.get('contract')} | {alarm.get('message')}",
                            "tooltip": " | ".join(tooltip_parts),
                            "data": alarm
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении alarms.json: {e}")

    # Поиск в заметках
    if os.path.exists(PATHS["notes"]):
        try:
            with open(PATHS["notes"], "r", encoding="utf-8") as f:
                notes = json.load(f)
                for note in notes:
                    title = note.get("title", "")
                    content = note.get("content", "")
                    match = False

                    if vin:
                        pattern = rf'\b{re.escape(vin)}\b'
                        if re.search(pattern, title, re.IGNORECASE) or re.search(pattern, content, re.IGNORECASE):
                            match = True
                    if contract:
                        pattern = rf'\b{re.escape(contract)}\b'
                        if re.search(pattern, title, re.IGNORECASE) or re.search(pattern, content, re.IGNORECASE):
                            match = True

                    if match:
                        results.append({
                            "source": "note",
                            "text": f"[Заметка] {note.get('title')} | {note.get('content')[:40]}...",
                            "tooltip": note.get("content"),
                            "data": note
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении notes_data.json: {e}")

    return results