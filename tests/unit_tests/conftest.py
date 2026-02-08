# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def simple_mock_db():
    """Самая простая фикстура для начала"""
    mock = Mock()
    mock.get_steam_id.return_value = 76561198000000000
    return mock

@pytest.fixture
def simple_message():
    """Простое сообщение для тестов"""
    msg = Mock()
    msg.from_user.id = 123456
    msg.text = "test"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_cursor():
    """Создает мок курсора с поддержкой контекстного менеджера"""
    mock = Mock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    return mock


@pytest.fixture
def mock_connection(mock_cursor):
    """Создает мок подключения с курсором"""
    mock = Mock()
    mock.cursor.return_value = mock_cursor
    return mock