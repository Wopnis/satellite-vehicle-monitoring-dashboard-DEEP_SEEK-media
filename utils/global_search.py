# utils/global_search.py
"""Модуль глобального поиска по всем данным"""

import json
import os
from datetime import datetime
from typing import List, Dict

from config.paths import PATHS
from utils.logger import logger


def global_search(keyword: str) -> List[Dict]:
    """Выполняет глобальный поиск по всем данным системы"""
    if not keyword:
        return []
    
    keyword = keyword.lower().strip()
    results = []

    # Поиск в тревогах
    if os.path.exists(PATHS["alarms"]):
        try:
            with open(PATHS["alarms"], "r", encoding="utf-8") as f:
                alarms = json.load(f)
                for alarm in alarms:
                    combined = " ".join([
                        alarm.get("vin", ""), alarm.get("contract", ""),
                        alarm.get("brand", ""), alarm.get("license", ""),
                        alarm.get("message", ""), alarm.get("comment", ""),
                        alarm.get("lessee", "")
                    ]).lower()
                    if keyword in combined:
                        timestamp = alarm.get("timestamp", "-")
                        closed_at = alarm.get("closed_at")
                        has_media = bool(alarm.get("media", []))

                        results.append({
                            "source": "alarm",
                            "type": "Тревога",
                            "icon": "🚨",
                            "text": f"[Тревога] {timestamp} | {alarm.get('vin')} | {alarm.get('contract')} | {alarm.get('message', '')[:50]}",
                            "title": f"{timestamp} | {alarm.get('vin')} | {alarm.get('contract')}",
                            "preview": alarm.get("message", "")[:60].replace("\n", " "),
                            "data": alarm,
                            "timestamp": timestamp,
                            "created_at": alarm.get("timestamp"),
                            "closed_at": closed_at,
                            "has_media": has_media,
                            "search_match": keyword
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении alarms.json: {e}")

    # Поиск в заметках
    if os.path.exists(PATHS["notes"]):
        try:
            with open(PATHS["notes"], "r", encoding="utf-8") as f:
                notes = json.load(f)
                for note in notes:
                    combined = f"{note.get('title', '')} {note.get('content', '')}".lower()
                    if keyword in combined:
                        results.append({
                            "source": "note",
                            "type": "Заметка",
                            "icon": "📝",
                            "text": f"[Заметка] {note.get('title', 'Без заголовка')} | {note.get('content', '')[:60]}",
                            "title": note.get("title", "Без заголовка"),
                            "preview": note.get("content", "")[:60].replace("\n", " "),
                            "data": note,
                            "created_at": note.get("created_at", datetime.now().isoformat()),
                            "search_match": keyword
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении notes_data.json: {e}")

    # Поиск в чёрном списке
    if os.path.exists(PATHS["blacklist"]):
        try:
            with open(PATHS["blacklist"], "r", encoding="utf-8") as f:
                entries = json.load(f)
                for entry in entries:
                    combined = f"{entry.get('vin', '')} {entry.get('contract', '')} {entry.get('reason', '')}".lower()
                    if keyword in combined:
                        results.append({
                            "source": "blacklist",
                            "type": "Чёрный список",
                            "icon": "🚫",
                            "text": f"[Чёрный список] {entry.get('vin')} | {entry.get('reason')[:40]}",
                            "title": f"{entry.get('vin')} | {entry.get('reason')[:40]}",
                            "preview": entry.get("reason", ""),
                            "data": entry,
                            "created_at": entry.get("date_added", datetime.now().isoformat()),
                            "search_match": keyword
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении blacklist_data.json: {e}")

    # Поиск в журнале смен
    if os.path.exists(PATHS["shifts"]):
        try:
            with open(PATHS["shifts"], "r", encoding="utf-8") as f:
                shifts = json.load(f)
                for shift in shifts:
                    journal_text = shift.get("journal_text", "")
                    comment = shift.get("comment", "")
                    full_text = (journal_text + " " + comment).lower()
                    
                    if keyword in full_text:
                        started_at = shift.get("started_at", "—")
                        ended_at = shift.get("ended_at", "в процессе")
                        
                        preview = (journal_text or comment)[:100].strip()
                        if not preview:
                            preview = "Нет записей"

                        results.append({
                            "source": "shift_journal",
                            "type": "Журнал смены",
                            "icon": "📅",
                            "text": f"[Журнал смены] {started_at} → {ended_at} | {preview[:50]}",
                            "title": f"{started_at} → {ended_at}",
                            "preview": preview.replace("\n", " "),
                            "data": shift,
                            "created_at": started_at,
                            "ended_at": ended_at,
                            "search_match": keyword
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении shifts_data.json: {e}")

    # Поиск в изъятых ТС
    seized_file = os.path.join(os.path.dirname(PATHS["alarms"]), "seized_vehicles.json")
    if os.path.exists(seized_file):
        try:
            with open(seized_file, "r", encoding="utf-8") as f:
                seized_vehicles = json.load(f)
                for vehicle in seized_vehicles:
                    combined = " ".join([
                        vehicle.get("vin", ""),
                        vehicle.get("contract_number", ""),
                        vehicle.get("license_plate", ""),
                        vehicle.get("vehicle_brand", ""),
                        vehicle.get("lessee", ""),
                        vehicle.get("lessor", ""),
                        vehicle.get("storage_address", ""),
                        vehicle.get("comment", "")
                    ]).lower()
                    
                    if keyword in combined:
                        storage = vehicle.get("storage_address", "—")
                        results.append({
                            "source": "seized_vehicle",
                            "type": "Изъятое ТС",
                            "icon": "🚗",
                            "text": f"[Изъятое ТС] {vehicle.get('vin', '—')} | {vehicle.get('license_plate', '—')} | {storage[:40]}",
                            "title": f"{vehicle.get('vin', '—')} | {vehicle.get('contract_number', '—')}",
                            "preview": f"Стоянка: {storage}",
                            "data": vehicle,
                            "created_at": vehicle.get("created_at", datetime.now().isoformat()),
                            "search_match": keyword
                        })
        except Exception as e:
            logger.error(f"Ошибка при чтении seized_vehicles.json: {e}")

    # Сортировка по времени
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results