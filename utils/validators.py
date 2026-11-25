# utils/validators.py
"""Модуль валидации данных"""

import re
from typing import Tuple, Optional, List
from config.settings import settings


class ValidationResult:
    """Результат валидации"""
    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message
    
    def __bool__(self):
        return self.is_valid


class Validators:
    """Класс с методами валидации"""
    
    @staticmethod
    def validate_vin(vin: str) -> ValidationResult:
        """
        Проверяет корректность VIN-кода
        ВАЖНО: теперь проверяет только наличие значения, без ограничения длины!
        """
        if not vin or not vin.strip():
            return ValidationResult(False, "VIN не может быть пустым")
        
        # Только проверка, что поле не пустое и не состоит из одних пробелов
        vin = vin.strip()
        if len(vin) < 1:
            return ValidationResult(False, "VIN не может быть пустым")
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_contract(contract: str) -> ValidationResult:
        """Проверяет корректность номера договора"""
        if not contract or not contract.strip():
            return ValidationResult(False, "Договор не может быть пустым")
        
        contract = contract.strip()
        if len(contract) < settings.MIN_CONTRACT_LENGTH:
            return ValidationResult(False, f"Договор должен содержать минимум {settings.MIN_CONTRACT_LENGTH} символа")
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_brand(brand: str) -> ValidationResult:
        """Проверяет корректность марки ТС"""
        if not brand or not brand.strip():
            return ValidationResult(False, "Марка ТС не может быть пустой")
        
        brand = brand.strip()
        if len(brand) < settings.MIN_BRAND_LENGTH:
            return ValidationResult(False, f"Марка ТС должна содержать минимум {settings.MIN_BRAND_LENGTH} символа")
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_message(message: str) -> ValidationResult:
        """Проверяет корректность сообщения"""
        if not message or not message.strip():
            return ValidationResult(False, "Сообщение не может быть пустым")
        
        message = message.strip()
        if len(message) < settings.MIN_MESSAGE_LENGTH:
            return ValidationResult(False, f"Сообщение должно содержать минимум {settings.MIN_MESSAGE_LENGTH} символа")
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_license_plate(plate: str) -> ValidationResult:
        """Проверяет корректность госномера"""
        if not plate or not plate.strip():
            return ValidationResult(True)
        
        plate = plate.strip()
        if len(plate) < 2 or len(plate) > 15:
            return ValidationResult(False, "Госномер должен содержать от 2 до 15 символов")
        
        return ValidationResult(True)