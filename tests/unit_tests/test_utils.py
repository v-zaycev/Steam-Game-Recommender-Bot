import pytest
from datetime import date

from sources.utils import parse_steam_date, is_valid_steamid64

class TestParseSteamDate:
    def test_parse_valid_date(self):
        steam_date = "Dec 25, 2023"
        
        result = parse_steam_date(steam_date)
        
        assert result == date(2023, 12, 25)
    
    def test_parse_invalid_date_format(self):
        steam_date = "25-12-2023"
        
        result = parse_steam_date(steam_date)
        
        assert result is None
    
    def test_parse_none_date(self):
        result = parse_steam_date(None)
        
        assert result is None
    
    def test_parse_empty_string(self):
        result = parse_steam_date("")
        
        assert result is None
    
    def test_parse_whitespace_string(self):
        result = parse_steam_date("   ")
        
        assert result is None
    
    @pytest.mark.parametrize("month_abbr", [
        "Jan", "Jun", "Oct"])
    def test_parse_months(self, month_abbr):
        """Параметризованный тест для всех месяцев"""
        steam_date = f"{month_abbr} 1, 2026"
        
        result = parse_steam_date(steam_date)
        
        assert result is not None
        assert result.year == 2026
        assert result.day == 1

class TestIsValidSteamId64:    
    @pytest.mark.parametrize("steam_id, expected", [
        ("76561198000000000", True), 
        ("7656119abc8000000000", False),
        ("123", False),                
        ("not_a_number", False),       
        ("", False),
        (None, False),        
        ("999999999999999999999", False)
    ])
    def test_steamid64_parametrized(self, steam_id, expected):
        result = is_valid_steamid64(steam_id)
        assert result == expected

class TestEdgeCases:    
    def test_parse_date_with_special_characters(self):
        steam_date = "Dec. 25, 2023" 
        
        result = parse_steam_date(steam_date)

        assert result is None
    
    def test_parse_date_with_different_locale(self):
        steam_date = "дек 25, 2023"
        
        result = parse_steam_date(steam_date)

        assert result is None
    