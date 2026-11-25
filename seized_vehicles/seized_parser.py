# seized_vehicles/seized_parser.py
"""Парсер для автоматического извлечения данных из текста об изъятии ТС"""

import re
from typing import Dict, List


class SeizedTextParser:
    """Парсер текста об изъятии ТС"""
    
    PATTERNS = {
        "date": r'(\d{2}\.\d{2}\.\d{4})',
        "contract": r'ДЛ\s*(\d+[/\-]?\d*[/\-]?[А-Я]*\d*)|договор\s*([^\s,;]+)',
        "lessor": r'\(([^)]+)\)',
        "lessee": r'ООО\s*"([^"]+)"|ООО\s*([^\s,;]+)|ИП\s*([^\s,;]+)',
        "vin": r'vin[:\s]*([A-Z0-9]{17})|([A-Z0-9]{17})',
        "license_plate": r'г\.р\.з\.\s*([A-Z0-9]+)|госномер\s*([A-Z0-9]+)|г/н\s*([A-Z0-9]+)|р\.з\.\s*([A-Z0-9]+)',
        "storage": r'адресу[:\s]*([^;,.]+)|стоянку[:\s]*([^;,.]+)|помещены\s*на\s*[^:]*[:\s]*([^;,.]+)',
        "act_signed": r'акт[ы]*\s*(?:составлен|готов|составлены)',
        "sts_available": r'СТС\s*в\s*наличии|Ключи\s*и\s*стс\s*в\s*наличии|документы\s*переданы',
        "photos_in_rososmotr": r'Фото\s*в\s*приложении',
    }
    
    @classmethod
    def parse(cls, text: str) -> Dict:
        if not text or not text.strip():
            return {}
        
        result = {}
        text = text.strip()
        
        date_match = re.search(cls.PATTERNS["date"], text)
        if date_match:
            result["date"] = date_match.group(1)
        
        contract_match = re.search(cls.PATTERNS["contract"], text, re.IGNORECASE)
        if contract_match:
            for group in contract_match.groups():
                if group:
                    result["contract_number"] = group.strip()
                    break
        
        lessor_match = re.search(cls.PATTERNS["lessor"], text, re.IGNORECASE)
        if lessor_match:
            for group in lessor_match.groups():
                if group:
                    result["lessor"] = group.strip()
                    break
        
        lessee_match = re.search(cls.PATTERNS["lessee"], text, re.IGNORECASE)
        if lessee_match:
            for group in lessee_match.groups():
                if group:
                    result["lessee"] = group.strip()
                    break
        
        vin_match = re.search(r'([A-Z0-9]{17})', text, re.IGNORECASE)
        if vin_match:
            vin_pos = vin_match.start()
            vin_value = vin_match.group(1).upper()
            result["vin"] = vin_value
            
            text_before_vin = text[:vin_pos].strip()
            brand = None
            
            if '-' in text_before_vin:
                parts = text_before_vin.split('-')
                brand = parts[-1].strip()
                if ',' in brand:
                    brand = brand.split(',')[0].strip()
            
            if not brand or len(brand) < 2:
                ts_match = re.search(r'ТС\s*[-—]?\s*([^,;]+)', text_before_vin, re.IGNORECASE)
                if ts_match:
                    brand = ts_match.group(1).strip()
            
            if not brand or len(brand) < 2:
                parts = text_before_vin.split(',')
                if parts:
                    brand = parts[-1].strip()
            
            if brand:
                brand = re.sub(r'^[,;\s\-—]+|[,;\s\-—]+$', '', brand)
                brand = re.sub(r'^\d{2}\.\d{2}\.\d{4}\s+', '', brand)
                brand = re.sub(r'^от\s+', '', brand, flags=re.IGNORECASE)
                brand = re.sub(r'\s*vin\s*$', '', brand, flags=re.IGNORECASE)
                brand = re.sub(r'^vin\s*', '', brand, flags=re.IGNORECASE)
                if brand and len(brand) > 1 and not brand.isdigit():
                    result["vehicle_brand"] = brand
        
        license_match = re.search(cls.PATTERNS["license_plate"], text, re.IGNORECASE)
        if license_match:
            for group in license_match.groups():
                if group:
                    result["license_plate"] = group.strip().upper()
                    break
        
        storage_match = re.search(cls.PATTERNS["storage"], text, re.IGNORECASE)
        if storage_match:
            for group in storage_match.groups():
                if group:
                    result["storage_address"] = group.strip()
                    break
        
        result["act_signed"] = bool(re.search(cls.PATTERNS["act_signed"], text, re.IGNORECASE))
        result["sts_available"] = bool(re.search(cls.PATTERNS["sts_available"], text, re.IGNORECASE))
        result["photos_in_rososmotr"] = bool(re.search(cls.PATTERNS["photos_in_rososmotr"], text, re.IGNORECASE))
        
        return result
    
    @classmethod
    def parse_multiple(cls, text: str) -> List[Dict]:
        if not text or not text.strip():
            return []
        
        results = []
        entries = re.split(r'\n?\s*(\d+)\.\s*', text)
        
        if len(entries) <= 1:
            parsed = cls.parse(text)
            if parsed:
                results.append(parsed)
            return results
        
        header = entries[0] if entries else ""
        
        for i in range(1, len(entries), 2):
            if i + 1 <= len(entries):
                entry_text = entries[i + 1].strip()
                parsed = cls.parse(entry_text)
                if parsed:
                    if not parsed.get("date") and header:
                        date_match = re.search(cls.PATTERNS["date"], header)
                        if date_match:
                            parsed["date"] = date_match.group(1)
                    results.append(parsed)
        
        if not results:
            parsed = cls.parse(text)
            if parsed:
                results.append(parsed)
        
        return results