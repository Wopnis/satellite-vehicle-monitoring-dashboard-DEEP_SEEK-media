# analytics_clicker/clicker_log_parser.py
import os
import re
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

from utils.logger import logger

ALARM_PATTERNS = [
    re.compile(r"отключение питания ТС", re.IGNORECASE),
    re.compile(r"разряд аккумулятора ТС", re.IGNORECASE),
    re.compile(r"передвижение с блокировкой", re.IGNORECASE),
    re.compile(r"передвижение без зажигания", re.IGNORECASE),
    re.compile(r"передвижение без АКБ", re.IGNORECASE),
    re.compile(r"въезд в зону: Московская обл.", re.IGNORECASE),
    re.compile(r"нет связи > 4320 мин", re.IGNORECASE),
    re.compile(r"передвижение с финансовой блокировкой", re.IGNORECASE),
    re.compile(r"нет связи > 180 мин", re.IGNORECASE),
]

NO_AUTO_CLOSE_PATTERNS = [
    re.compile(r"выезд из зоны", re.IGNORECASE),
    re.compile(r"нет связи > 720 мин", re.IGNORECASE),
    re.compile(r"въезд в зону", re.IGNORECASE),
    re.compile(r"нет связи > 4320 мин", re.IGNORECASE)
]


class ClickerLogParser:
    """Парсер логов кликера Playwright с оптимизацией по имени файла"""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        self.df = None
        self.parse_errors = []
        self.files_processed = 0
        self.files_skipped = 0
    
    def parse_all_logs(self, start_date: str = None, end_date: str = None, max_records: int = 10000) -> bool:
        self.df = None
        self.parse_errors = []
        self.files_processed = 0
        self.files_skipped = 0
        
        log_files = glob.glob(os.path.join(self.logs_dir, "*.log"))
        
        if not log_files:
            self.parse_errors.append(f"Не найдено файлов *.log в {self.logs_dir}")
            return False
        
        filtered_files = self._filter_files_by_name(log_files, start_date, end_date)
        
        if not filtered_files:
            self.parse_errors.append(f"Не найдено файлов за период {start_date} — {end_date}")
            return False
        
        all_records = []
        filtered_files.sort(key=os.path.getmtime, reverse=True)
        
        for log_file in filtered_files:
            try:
                records = self._parse_file(log_file)
                all_records.extend(records)
                if max_records and len(all_records) >= max_records:
                    all_records = all_records[:max_records]
                    break
            except Exception as e:
                self.parse_errors.append(f"{os.path.basename(log_file)}: {e}")
                logger.error(f"Ошибка парсинга {log_file}: {e}")
        
        if all_records:
            self.df = pd.DataFrame(all_records)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
            return True
        
        return False
    
    def _filter_files_by_name(self, log_files: List[str], start_date: str, end_date: str) -> List[str]:
        if not start_date and not end_date:
            return log_files
        
        filtered = []
        
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) if end_date else None
        except Exception as e:
            self.parse_errors.append(f"Ошибка парсинга дат: {e}")
            return log_files
        
        file_date_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})')
        
        for file_path in log_files:
            file_name = os.path.basename(file_path)
            match = file_date_pattern.match(file_name)
            
            if not match:
                self.files_skipped += 1
                continue
            
            try:
                file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                
                if start and file_date < start:
                    self.files_skipped += 1
                    continue
                
                if end and file_date >= end:
                    self.files_skipped += 1
                    continue
                
                filtered.append(file_path)
                self.files_processed += 1
                
            except Exception as e:
                logger.warning(f"Ошибка парсинга даты файла {file_name}: {e}")
                self.files_skipped += 1
                continue
        
        return filtered
    
    def _parse_file(self, filepath: str) -> List[Dict]:
        log_pattern = re.compile(
            r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.*)$'
        )
        
        alarm_pattern = re.compile(
            r'\[!\]\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})\s+Обнаружена тревога:\s*([^,]+)(?:,\s*Договор:\s*([^\s]+))?'
        )
        
        vin_pattern = re.compile(r'([A-Z0-9]{16,17})', re.IGNORECASE)
        
        records = []
        
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    match = log_pattern.match(line)
                    if not match:
                        continue
                    
                    log_time, level, message = match.groups()
                    
                    alarm_match = alarm_pattern.search(message)
                    if alarm_match:
                        alarm_time, alarm_text, contract = alarm_match.groups()
                        alarm_type = self._classify_alarm(alarm_text)
                        vin_match = vin_pattern.search(message)
                        vin = vin_match.group(1).upper() if vin_match else ""
                        
                        records.append({
                            "timestamp": alarm_time,
                            "alarm_text": alarm_text.strip(),
                            "alarm_type": alarm_type,
                            "contract": contract.strip() if contract else "",
                            "vin": vin,
                            "lessee": "",
                            "log_file": os.path.basename(filepath),
                        })
        except Exception as e:
            logger.error(f"Ошибка чтения файла {filepath}: {e}")
            raise
        
        return records
    
    def _classify_alarm(self, alarm_text: str) -> str:
        for pattern in ALARM_PATTERNS:
            if pattern.search(alarm_text):
                return "auto_close"
        
        for pattern in NO_AUTO_CLOSE_PATTERNS:
            if pattern.search(alarm_text):
                return "manual_close"
        
        return "other"
    
    def get_basic_stats(self) -> Dict[str, any]:
        if self.df is None or len(self.df) == 0:
            return {
                "total_alarms": 0,
                "auto_close": 0,
                "manual_close": 0,
                "other": 0,
                "with_vin": 0,
                "with_contract": 0,
                "parse_errors": len(self.parse_errors),
                "files_processed": self.files_processed,
                "files_skipped": self.files_skipped
            }
        
        total = len(self.df)
        by_type = self.df['alarm_type'].value_counts().to_dict()
        with_vin = len(self.df[self.df['vin'].notna() & (self.df['vin'] != '')])
        with_contract = len(self.df[self.df['contract'].notna() & (self.df['contract'] != '')])
        
        return {
            "total_alarms": int(total),
            "auto_close": int(by_type.get("auto_close", 0)),
            "manual_close": int(by_type.get("manual_close", 0)),
            "other": int(by_type.get("other", 0)),
            "with_vin": int(with_vin),
            "with_contract": int(with_contract),
            "parse_errors": len(self.parse_errors),
            "files_processed": self.files_processed,
            "files_skipped": self.files_skipped
        }
    
    def get_frequency_stats(self, field: str, top_n: int = 20) -> List[Dict]:
        if self.df is None or len(self.df) == 0 or field not in self.df.columns:
            return []
        
        df_filtered = self.df[self.df[field].notna() & (self.df[field].astype(str).str.len() >= 2)]
        
        if len(df_filtered) == 0:
            return []
        
        stats = df_filtered[field].value_counts().head(top_n)
        total = len(df_filtered)
        
        return [
            {"value": val, "count": int(cnt), "percentage": round(cnt/total*100, 1)}
            for val, cnt in stats.items()
        ]
    
    def get_alarm_types_distribution(self) -> Dict[str, int]:
        if self.df is None or len(self.df) == 0:
            return {}
        
        patterns = {
            "Питание": r"отключение питания",
            "Аккумулятор": r"разряд аккумулятора",
            "Передвижение с блокировкой": r"передвижение.*блокировк",
            "Передвижение без зажигания": r"передвижение.*без зажигания",
            "Передвижение без АКБ": r"передвижение.*без АКБ",
            "Финансовая блокировка": r"финансов",
            "Геозона (въезд)": r"въезд",
            "Геозона (выезд)": r"выезд",
            "Нет связи": r"нет связи",
        }
        
        result = {}
        for label, pattern in patterns.items():
            count = self.df['alarm_text'].str.contains(pattern, case=False, regex=True, na=False).sum()
            if count > 0:
                result[label] = int(count)
        
        return result
    
    def get_time_distribution(self, interval: str = "hour") -> Dict[str, int]:
        if self.df is None or len(self.df) == 0 or 'timestamp' not in self.df.columns:
            return {}
        
        df = self.df.dropna(subset=['timestamp'])
        
        if interval == "hour":
            df['hour'] = df['timestamp'].dt.hour
            stats = df['hour'].value_counts().sort_index()
            return {f"{h:02d}:00": int(stats.get(h, 0)) for h in range(24)}
        
        elif interval == "day_of_week":
            days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            df['day'] = df['timestamp'].dt.dayofweek
            stats = df['day'].value_counts().sort_index()
            return {days[i]: int(stats.get(i, 0)) for i in range(7)}
        
        elif interval == "date":
            df['date'] = df['timestamp'].dt.strftime("%d.%m.%Y")
            stats = df['date'].value_counts().sort_index()
            return {str(k): int(v) for k, v in stats.items()}
        
        return {}
    
    def export_to_csv(self, output_path: str, data_type: str, **kwargs) -> Tuple[bool, str]:
        if self.df is None or len(self.df) == 0:
            return False, "Нет данных"
        
        try:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            if data_type == "alarms_raw":
                export_df = self.df.copy()
                export_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                return True, f"Экспортировано {len(export_df)} строк"
            
            elif data_type == "frequency":
                stats = self.get_frequency_stats(kwargs.get("field", "vin"), kwargs.get("top_n", 100))
                if stats:
                    df_stats = pd.DataFrame(stats)
                    df_stats.columns = ["Значение", "Количество", "Процент"]
                    df_stats.to_csv(output_path, index=False, encoding='utf-8-sig')
                    return True, f"Экспортировано {len(df_stats)} строк"
            
            elif data_type == "alarm_types":
                stats = self.get_alarm_types_distribution()
                if stats:
                    df_stats = pd.DataFrame(list(stats.items()), columns=["Тип тревоги", "Количество"])
                    df_stats.to_csv(output_path, index=False, encoding='utf-8-sig')
                    return True, f"Экспортировано {len(df_stats)} строк"
            
            elif data_type == "time_distribution":
                stats = self.get_time_distribution(kwargs.get("interval", "hour"))
                if stats:
                    df_stats = pd.DataFrame(list(stats.items()), columns=["Период", "Количество"])
                    df_stats.to_csv(output_path, index=False, encoding='utf-8-sig')
                    return True, f"Экспортировано {len(df_stats)} строк"
            
            return False, "Нет данных для экспорта"
        
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            return False, f"Ошибка экспорта: {e}"