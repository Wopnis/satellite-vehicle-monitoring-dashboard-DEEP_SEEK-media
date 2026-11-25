# analytics/analyzer.py
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import csv

from utils.logger import logger


class AlarmAnalyzer:
    """Анализатор базы тревог для выявления паттернов и аномалий"""
    
    def __init__(self, alarms_file: str = "data/alarms.json"):
        self.alarms_file = alarms_file
        self.alarms = self._load_alarms()
        self._load_errors = []
    
    def _load_alarms(self) -> List[Dict]:
        if not os.path.exists(self.alarms_file):
            self._load_errors.append(f"Файл {self.alarms_file} не найден")
            return []
        try:
            with open(self.alarms_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    self._load_errors.append("Неверный формат JSON: ожидается список")
                    return []
        except json.JSONDecodeError as e:
            self._load_errors.append(f"Ошибка парсинга JSON: {e}")
            logger.error(f"Ошибка парсинга {self.alarms_file}: {e}")
            return []
        except Exception as e:
            self._load_errors.append(f"Неожиданная ошибка: {e}")
            logger.error(f"Ошибка загрузки {self.alarms_file}: {e}")
            return []
    
    def get_load_errors(self) -> List[str]:
        return self._load_errors.copy()
    
    def get_basic_stats(self) -> Dict[str, any]:
        total = len(self.alarms)
        active = sum(1 for a in self.alarms if a.get("status") == "active")
        closed = total - active
        
        timestamps = [a.get("timestamp") for a in self.alarms if a.get("timestamp")]
        date_range = "н/д"
        if timestamps:
            try:
                dates = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in timestamps]
                date_range = f"{min(dates).strftime('%d.%m.%Y')} — {max(dates).strftime('%d.%m.%Y')}"
            except Exception as e:
                logger.warning(f"Ошибка парсинга дат: {e}")
        
        return {
            "total": total,
            "active": active,
            "closed": closed,
            "date_range": date_range,
            "errors": self._load_errors
        }
    
    def find_duplicates(self, by_fields: List[str] = None, min_count: int = 2) -> List[Dict]:
        if by_fields is None:
            by_fields = ["vin", "contract"]
        
        seen = defaultdict(list)
        
        for alarm in self.alarms:
            key_parts = []
            for field in by_fields:
                value = str(alarm.get(field, "")).strip().lower()
                if value:
                    key_parts.append(value)
            
            if key_parts:
                key = "|".join(key_parts)
                seen[key].append(alarm)
        
        duplicates = []
        for key, group in seen.items():
            if len(group) >= min_count:
                all_messages = []
                for alarm in group:
                    all_messages.append({
                        'timestamp': alarm.get('timestamp', ''),
                        'message': alarm.get('message', ''),
                        'vin': alarm.get('vin', ''),
                        'contract': alarm.get('contract', ''),
                        'lessee': alarm.get('lessee', ''),
                        'brand': alarm.get('brand', '')
                    })
                
                duplicates.append({
                    "key": key,
                    "fields": by_fields,
                    "count": len(group),
                    "first_seen": min(a.get("timestamp", "") for a in group if a.get("timestamp")),
                    "last_seen": max(a.get("timestamp", "") for a in group if a.get("timestamp")),
                    "sample_message": group[0].get("message", "")[:80],
                    "alarms": all_messages
                })
        
        return sorted(duplicates, key=lambda x: x["count"], reverse=True)
    
    def get_frequency_stats(self, field: str, top_n: int = 20, min_length: int = 2) -> List[Dict]:
        counter = Counter()
        for alarm in self.alarms:
            value = alarm.get(field, "").strip()
            if value and len(value) >= min_length:
                if field == "vin":
                    value = value.upper()
                counter[value] += 1
        
        total = sum(counter.values())
        return [
            {"value": val, "count": cnt, "percentage": round(cnt/total*100, 1) if total else 0}
            for val, cnt in counter.most_common(top_n)
        ]
    
    def get_alarm_types_distribution(self) -> Dict[str, int]:
        patterns = {
            "Демонтаж/вмешательство": r"демонт|вмешательств|снятие|глуш|tamper",
            "Передвижение": r"передвиж|движ|move|travel",
            "Нет связи": r"нет\s*связ|оффлайн|offline|no\s*signal",
            "Геозона": r"въезд\s*в\s*зону|выезд\s*из\s*зоны|историч|geofence",
            "Питание/АКБ": r"питани|акб|разряд|батаре|power|battery",
            "Блокировка": r"блокировк|финансов|block|financial",
            "Прочее": r".*"
        }
        
        stats = Counter()
        for alarm in self.alarms:
            msg = (alarm.get("message", "") + " " + alarm.get("comment", "")).lower()
            matched = False
            for label, pattern in patterns.items():
                if label == "Прочее":
                    continue
                if re.search(pattern, msg, re.I):
                    stats[label] += 1
                    matched = True
                    break
            if not matched and msg.strip():
                stats["Прочее"] += 1
        
        return dict(stats)
    
    def get_time_distribution(self, interval: str = "hour") -> Dict[str, int]:
        stats = Counter()
        for alarm in self.alarms:
            ts = alarm.get("timestamp")
            if not ts:
                continue
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            
            if interval == "hour":
                key = f"{dt.hour:02d}:00"
            elif interval == "day_of_week":
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                key = days[dt.weekday()]
            elif interval == "date":
                key = dt.strftime("%d.%m")
            else:
                key = "unknown"
            stats[key] += 1
        
        if interval == "hour":
            return {f"{h:02d}:00": stats.get(f"{h:02d}:00", 0) for h in range(24)}
        return dict(stats)
    
    def filter_by_date_range(self, start_date: str = None, end_date: str = None) -> 'AlarmAnalyzer':
        filtered = AlarmAnalyzer.__new__(AlarmAnalyzer)
        filtered.alarms_file = self.alarms_file
        filtered._load_errors = []
        
        filtered_alarms = []
        for alarm in self.alarms:
            ts = alarm.get("timestamp")
            if not ts:
                continue
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                if start_date:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    if dt < start:
                        continue
                if end_date:
                    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    if dt >= end:
                        continue
                filtered_alarms.append(alarm)
            except Exception as e:
                logger.warning(f"Ошибка фильтрации даты: {e}")
                continue
        
        filtered.alarms = filtered_alarms
        return filtered
    
    def export_to_csv(self, output_path: str, data_type: str, **kwargs) -> Tuple[bool, str]:
        rows = []
        fieldnames = None
        
        try:
            if data_type == "duplicates":
                dups = self.find_duplicates(kwargs.get("by_fields"), kwargs.get("min_count", 2))
                if dups:
                    fieldnames = ["Группа", "Поля", "Количество", "Первое появление", "Последнее", "Пример"]
                    for dup in dups:
                        rows.append({
                            "Группа": dup["key"],
                            "Поля": ", ".join(dup["fields"]),
                            "Количество": dup["count"],
                            "Первое появление": dup["first_seen"],
                            "Последнее": dup["last_seen"],
                            "Пример": dup["sample_message"]
                        })
            
            elif data_type == "frequency":
                stats = self.get_frequency_stats(
                    kwargs.get("field", "vin"),
                    kwargs.get("top_n", 100),
                    kwargs.get("min_length", 2)
                )
                if stats:
                    fieldnames = ["Значение", "Количество", "Процент"]
                    for item in stats:
                        rows.append({
                            "Значение": item["value"],
                            "Количество": item["count"],
                            "Процент": f"{item['percentage']}%"
                        })
            
            elif data_type == "alarm_types":
                stats = self.get_alarm_types_distribution()
                if stats:
                    fieldnames = ["Тип тревоги", "Количество"]
                    for label, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                        rows.append({"Тип тревоги": label, "Количество": count})
            
            elif data_type == "time_distribution":
                stats = self.get_time_distribution(kwargs.get("interval", "hour"))
                if stats:
                    fieldnames = ["Период", "Количество"]
                    for period, count in stats.items():
                        rows.append({"Период": period, "Количество": count})
            
            if not rows:
                return False, "Нет данных для экспорта"
            
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            return True, f"Экспортировано {len(rows)} строк"
        
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            return False, f"Ошибка экспорта: {e}"