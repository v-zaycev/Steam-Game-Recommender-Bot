def test_simple_mock(simple_mock_db):
    """Проверяем, что фикстура работает"""
    result = simple_mock_db.get_steam_id(123)
    assert result == 76561198000000000
    
def test_mock_called(simple_mock_db):
    """Проверяем, что метод вызвался с правильным аргументом"""
    simple_mock_db.get_steam_id(999)
    simple_mock_db.get_steam_id.assert_called_with(999)