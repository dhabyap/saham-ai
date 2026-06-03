"""
Validation functions for CLI inputs
"""

import re
import os
from typing import Union, Tuple


class Validator:
    """Input validation helper class"""

    @staticmethod
    def validate_api_key(value: str, min_length: int = 5) -> Tuple[bool, str]:
        """Validate API key format"""
        if not value or len(value.strip()) == 0:
            return False, "API key tidak boleh kosong"
        
        if len(value) < min_length:
            return False, f"API key minimal {min_length} karakter"
        
        return True, ""

    @staticmethod
    def validate_token(value: str) -> Tuple[bool, str]:
        """Validate token format"""
        if not value or len(value.strip()) == 0:
            return False, "Token tidak boleh kosong"
        
        # Basic token format check
        if len(value) < 10:
            return False, "Token format tidak valid"
        
        return True, ""

    @staticmethod
    def validate_chat_id(value: str) -> Tuple[bool, str]:
        """Validate Telegram Chat ID"""
        if not value or len(value.strip()) == 0:
            return False, "Chat ID tidak boleh kosong"
        
        # Chat ID should be numeric (positive or negative)
        if not re.match(r'^-?\d+$', value.strip()):
            return False, "Chat ID harus angka (contoh: 123456789 atau -123456789)"
        
        return True, ""

    @staticmethod
    def validate_integer(value: str, min_val: int = 1, max_val: int = None) -> Tuple[bool, str]:
        """Validate integer input"""
        if not value or len(value.strip()) == 0:
            return False, "Input tidak boleh kosong"
        
        try:
            num = int(value.strip())
            if num < min_val:
                return False, f"Nilai minimal {min_val}"
            if max_val and num > max_val:
                return False, f"Nilai maksimal {max_val}"
            return True, ""
        except ValueError:
            return False, "Harus berupa angka"

    @staticmethod
    def validate_yes_no(value: str) -> Tuple[bool, str]:
        """Validate yes/no input"""
        if value.lower() not in ['y', 'n', 'yes', 'no']:
            return False, "Input harus 'y' atau 'n'"
        return True, ""

    @staticmethod
    def validate_choice(value: str, choices: list) -> Tuple[bool, str]:
        """Validate choice from list"""
        try:
            num = int(value.strip())
            if num < 1 or num > len(choices):
                return False, f"Pilih antara 1-{len(choices)}"
            return True, ""
        except ValueError:
            return False, "Harus berupa angka"

    @staticmethod
    def validate_url(value: str) -> Tuple[bool, str]:
        """Validate URL format"""
        if not value or len(value.strip()) == 0:
            return False, "URL tidak boleh kosong"
        
        # Simple URL validation
        url_pattern = r'^https?://'
        if not re.match(url_pattern, value.strip()):
            return False, "URL harus dimulai dengan http:// atau https://"
        
        return True, ""

    @staticmethod
    def validate_path(value: str) -> Tuple[bool, str]:
        """Validate path exists or can be created"""
        if not value or len(value.strip()) == 0:
            return False, "Path tidak boleh kosong"
        
        path = value.strip()
        # Check if parent directory exists
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            return False, f"Parent directory tidak ada: {parent}"
        
        return True, ""


def get_validator():
    """Get validator instance"""
    return Validator()
