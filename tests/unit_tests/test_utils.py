import pytest
from datetime import date
from unittest.mock import patch, MagicMock

# Импортируем функции, которые будем тестировать
from sources.utils import parse_steam_date, is_valid_steamid64, States

class TestParseSteamDate:
    """Тесты для функции parse_steam_date"""
    
    def test_parse_valid_date(self):
        """Тест парсинга корректной даты из Steam"""
        # Arrange (подготовка)
        steam_date = "Dec 25, 2023"
        
        # Act (действие)
        result = parse_steam_date(steam_date)
        
        # Assert (проверка)
        assert result == date(2023, 12, 25)
    
    def test_parse_invalid_date_format(self):
        """Тест парсинга даты в неправильном формате"""
        # Неправильный формат (день-месяц-год)
        steam_date = "25-12-2023"
        
        result = parse_steam_date(steam_date)
        
        assert result is None
    
    def test_parse_none_date(self):
        """Тест парсинга None значения"""
        result = parse_steam_date(None)
        
        assert result is None
    
    def test_parse_empty_string(self):
        """Тест парсинга пустой строки"""
        result = parse_steam_date("")
        
        assert result is None
    
    def test_parse_whitespace_string(self):
        """Тест парсинга строки только с пробелами"""
        result = parse_steam_date("   ")
        
        assert result is None
    
    def test_parse_february_29_leap_year(self):
        """Тест парсинга 29 февраля в високосном году"""
        steam_date = "Feb 29, 2024"  # 2024 - високосный
        
        result = parse_steam_date(steam_date)
        
        assert result == date(2024, 2, 29)
    
    def test_parse_february_29_non_leap_year(self):
        """Тест парсинга 29 февраля в невисокосном году"""
        steam_date = "Feb 29, 2023"  # 2023 - невисокосный
        
        result = parse_steam_date(steam_date)
        
        # Должно вернуть None, так как дата некорректна
        assert result is None
    
    @pytest.mark.parametrize("month_abbr", [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ])
    def test_parse_all_months(self, month_abbr):
        """Параметризованный тест для всех месяцев"""
        steam_date = f"{month_abbr} 1, 2024"
        
        result = parse_steam_date(steam_date)
        
        assert result is not None
        assert result.year == 2024
        assert result.day == 1

class TestIsValidSteamId64:
    """Тесты для функции is_valid_steamid64"""
    
    def test_valid_steamid64_middle_range(self):
        """Тест валидного SteamID64 в середине диапазона"""
        # Arrange
        valid_id = "76561198061234567"  # Пример из середины диапазона
        
        # Act
        result = is_valid_steamid64(valid_id)
        
        # Assert
        assert result is True
    
    def test_valid_steamid64_lower_boundary(self):
        """Тест валидного SteamID64 на нижней границе диапазона"""
        valid_id = "76561197960265728"  # Минимальный валидный
        
        result = is_valid_steamid64(valid_id)
        
        assert result is True
    
    def test_valid_steamid64_upper_boundary(self):
        """Тест валидного SteamID64 на верхней границе диапазона"""
        valid_id = "76561202255233023"  # Максимальный валидный
        
        result = is_valid_steamid64(valid_id)
        
        assert result is True
    
    def test_invalid_steamid64_below_range(self):
        """Тест SteamID64 ниже допустимого диапазона"""
        invalid_id = "76561197960265727"  # На 1 меньше минимального
        
        result = is_valid_steamid64(invalid_id)
        
        assert result is False
    
    def test_invalid_steamid64_above_range(self):
        """Тест SteamID64 выше допустимого диапазона"""
        invalid_id = "76561202255233024"  # На 1 больше максимального
        
        result = is_valid_steamid64(invalid_id)
        
        assert result is False
    
    def test_steamid64_as_integer(self):
        """Тест SteamID64 переданного как целое число (строка с числом)"""
        valid_id = "76561198000000000"
        
        result = is_valid_steamid64(valid_id)
        
        assert result is True
    
    def test_non_numeric_string(self):
        """Тест нечисловой строки"""
        invalid_id = "not_a_number_123"
        
        result = is_valid_steamid64(invalid_id)
        
        assert result is False
    
    def test_empty_string(self):
        """Тест пустой строки"""
        result = is_valid_steamid64("")
        
        assert result is False
    
    def test_string_with_letters_and_numbers(self):
        """Тест строки с буквами и цифрами"""
        result = is_valid_steamid64("7656119abc8000000000")
        
        assert result is False
    
    def test_none_value(self):
        """Тест передачи None"""
        result = is_valid_steamid64(None)
        
        assert result is False
    
    def test_negative_number(self):
        """Тест отрицательного числа"""
        result = is_valid_steamid64("-76561198000000000")
        
        assert result is False
    
    def test_zero(self):
        """Тест нуля"""
        result = is_valid_steamid64("0")
        
        assert result is False
    
    def test_very_large_number(self):
        """Тест очень большого числа"""
        result = is_valid_steamid64("999999999999999999999")
        
        assert result is False
    
    @pytest.mark.parametrize("steam_id, expected", [
        # Валидные ID
        ("76561197960265728", True),   # нижняя граница
        ("76561198000000000", True),   # середина диапазона
        ("76561198123456789", True),   # случайный валидный
        ("76561202255233023", True),   # верхняя граница
        
        # Невалидные ID
        ("76561197960265727", False),  # чуть ниже границы
        ("76561202255233024", False),  # чуть выше границы
        ("123", False),                # слишком маленькое
        ("not_a_number", False),       # не число
        ("", False),                   # пустая строка
        ("-76561198000000000", False), # отрицательное
    ])
    def test_steamid64_parametrized(self, steam_id, expected):
        """Параметризованный тест для разных SteamID64"""
        result = is_valid_steamid64(steam_id)
        assert result == expected

class TestStatesClass:
    """Тесты для класса States"""
    
    def test_states_class_exists(self):
        """Тест, что класс States существует и создаётся"""
        # Проверяем, что класс можно создать
        states = States()
        
        assert states is not None
        assert isinstance(states, States)
    
    def test_states_has_expected_states(self):
        """Тест, что класс имеет ожидаемые состояния"""
        # Проверяем наличие всех ожидаемых состояний
        assert hasattr(States, 'id_waiting')
        assert hasattr(States, 'info_game_id_waiting')
        assert hasattr(States, 'similar_game_id_waiting')
    
    def test_states_are_state_objects(self):
        """Тест, что атрибуты являются объектами State"""
        from aiogram.fsm.state import State
        
        assert isinstance(States.id_waiting, State)
        assert isinstance(States.info_game_id_waiting, State)
        assert isinstance(States.similar_game_id_waiting, State)
    
    def test_states_have_correct_names(self):
        """Тест, что состояния имеют правильные имена"""
        # Проверяем имена состояний (если доступны)
        assert States.id_waiting.state == "States:id_waiting"
        assert States.info_game_id_waiting.state == "States:info_game_id_waiting"
        assert States.similar_game_id_waiting.state == "States:similar_game_id_waiting"

class TestEdgeCases:
    """Тесты граничных случаев и особых ситуаций"""
    
    def test_parse_date_with_special_characters(self):
        """Тест парсинга даты с особыми символами"""
        # Steam API обычно возвращает чистые даты, но на всякий случай
        steam_date = "Dec. 25, 2023"  # Точка после сокращения месяца
        
        result = parse_steam_date(steam_date)
        
        # Должно вернуть None, так как формат не совпадает
        assert result is None
    
    def test_parse_date_with_different_locale(self):
        """Тест парсинга даты на другом языке"""
        steam_date = "дек 25, 2023"  # Русский
        
        result = parse_steam_date(steam_date)
        
        assert result is None
    
    def test_steamid64_with_leading_zeros(self):
        """Тест SteamID64 с ведущими нулями"""
        # Числа с ведущими нулями обычно не встречаются,
        # но проверим поведение
        steam_id = "076561198000000000"  # С ведущим нулём
        
        result = is_valid_steamid64(steam_id)
        
        # int() преобразует "0765..." в 765...
        assert result is True
    
    def test_steamid64_hexadecimal(self):
        """Тест шестнадцатеричного представления"""
        steam_id = "0x110000100000000"  # Шестнадцатеричное представление
        
        result = is_valid_steamid64(steam_id)
        
        # int() с base=0 понимает 0x, но это невалидный формат для SteamID
        # Функция вернёт False из-за проверки диапазона
        assert result is False
