# seized_vehicles/seized_manager.py
"""Менеджер данных об изъятых ТС"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import uuid

from core.base_manager import BaseDataManager
from config.paths import PATHS, BASE_DIR
from utils.logger import logger


class SeizedVehicleManager(BaseDataManager):
    """Менеджер для работы с изъятыми ТС"""
    
    def __init__(self):
        self.filepath = os.path.join(BASE_DIR, "data", "seized_vehicles.json")
        logger.info(f"📁 Путь к файлу изъятых ТС: {self.filepath}")
        super().__init__(self.filepath)
        logger.info(f"📊 Загружено записей: {len(self._cache)}")
    
    def add_vehicle(self, data: Dict) -> bool:
        """Добавляет запись об изъятом ТС"""
        data["id"] = str(uuid.uuid4())[:8]
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["updated_at"] = data["created_at"]
        
        self._cache.append(data)
        success = self.save_data()
        if success:
            logger.info(f"✅ Добавлена запись об изъятом ТС: {data.get('vin', 'без VIN')}")
        return success
    
    def update_vehicle(self, old_data: Dict, new_data: Dict) -> bool:
        """Обновляет запись об изъятом ТС"""
        vin = old_data.get("vin", "")
        contract = old_data.get("contract_number", "")
        
        for i, item in enumerate(self._cache):
            if item.get("vin") == vin and item.get("contract_number") == contract:
                new_data["id"] = item.get("id")
                new_data["created_at"] = item.get("created_at")
                new_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._cache[i] = new_data
                return self.save_data()
        
        return False
    
    def search_by_vin(self, vin: str) -> List[Dict]:
        """Поиск по VIN (точное совпадение)"""
        if not vin:
            return []
        vin = vin.upper().strip()
        return [v for v in self._cache if v.get("vin", "").upper() == vin]
    
    def search_by_license(self, license_plate: str) -> List[Dict]:
        """Поиск по госномеру"""
        if not license_plate:
            return []
        license_plate = license_plate.upper().strip()
        return [v for v in self._cache if v.get("license_plate", "").upper() == license_plate]
    
    def search_by_contract(self, contract: str) -> List[Dict]:
        """Поиск по номеру договора"""
        if not contract:
            return []
        contract = contract.strip()
        return [v for v in self._cache if contract in v.get("contract_number", "")]
    
    def search_by_storage(self, storage: str) -> List[Dict]:
        """Поиск по адресу стоянки"""
        if not storage:
            return []
        storage = storage.lower().strip()
        return [v for v in self._cache if storage in v.get("storage_address", "").lower()]
    
    def search(self, query: str) -> List[Dict]:
        """Универсальный поиск по всем полям"""
        if not query:
            return []
        query = query.lower().strip()
        
        results = []
        for v in self._cache:
            search_fields = [
                v.get("vin", "").lower(),
                v.get("license_plate", "").lower(),
                v.get("contract_number", "").lower(),
                v.get("lessee", "").lower(),
                v.get("lessor", "").lower(),
                v.get("vehicle_brand", "").lower(),
                v.get("storage_address", "").lower(),
                v.get("released_to", "").lower(),
                v.get("comment", "").lower()
            ]
            
            if any(query in field for field in search_fields):
                results.append(v)
        
        return results
    
    def find_vehicle(self, vin: str, contract: str) -> Optional[Dict]:
        """Ищет ТС по VIN и договору"""
        if not vin and not contract:
            return None
        
        vin = vin.upper().strip() if vin else ""
        contract = contract.strip() if contract else ""
        
        for v in self._cache:
            v_vin = v.get("vin", "").upper()
            v_contract = v.get("contract_number", "")
            
            if vin and v_vin == vin:
                return v
            if contract and contract in v_contract:
                return v
        
        return None
    
    def get_by_storage(self, storage_address: str) -> List[Dict]:
        """Получить все ТС на конкретной стоянке"""
        if not storage_address:
            return []
        return [v for v in self._cache if storage_address.lower() in v.get("storage_address", "").lower()]
    
    def get_all_storages(self) -> List[str]:
        """Получить список всех стоянок"""
        storages = set()
        for v in self._cache:
            addr = v.get("storage_address", "")
            if addr:
                storages.add(addr)
        return sorted(list(storages))
    
    def get_statistics(self) -> Dict:
        """Статистика по изъятым ТС"""
        total = len(self._cache)
        
        lessors = {}
        storages = {}
        for v in self._cache:
            lessor = v.get("lessor", "Не указан")
            lessors[lessor] = lessors.get(lessor, 0) + 1
            
            addr = v.get("storage_address", "Не указана")
            storages[addr] = storages.get(addr, 0) + 1
        
        return {
            "total": total,
            "by_lessor": lessors,
            "by_storage": storages
        }
    
    def delete_vehicle(self, vehicle: Dict) -> bool:
        """Удаляет запись"""
        vin = vehicle.get("vin", "")
        contract = vehicle.get("contract_number", "")
        
        for i, v in enumerate(self._cache):
            if v.get("vin") == vin and v.get("contract_number") == contract:
                del self._cache[i]
                return self.save_data()
        
        return False


seized_manager = SeizedVehicleManager()