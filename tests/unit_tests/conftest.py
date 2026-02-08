import pytest
from unittest.mock import Mock, AsyncMock, patch
from sources.database_client import PgsqlClient
from sources.database_api import PgsqlApiClient


@pytest.fixture
def mock_cursor():
    mock = Mock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    return mock


@pytest.fixture
def mock_connection(mock_cursor):
    mock = Mock()
    mock.cursor.return_value = mock_cursor
    return mock

@pytest.fixture
def mock_client():
    with patch('sources.database_api.PgsqlClient'):
        client = PgsqlApiClient(env='test.env')
        client.select = Mock()
        client.insert = Mock()
        client.update = Mock()
        client.delete = Mock()
        client.get_connection = Mock()
        client.connection = None
        yield client

@pytest.fixture
def mock_connection_cursor():
    mock_cursor = Mock()
    mock_cursor.execute = Mock()
    mock_cursor.fetchall = Mock()
    
    mock_connection = Mock()
    mock_connection.cursor = Mock(return_value=mock_cursor)
    mock_connection.commit = Mock()
    mock_connection.rollback = Mock()
    
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)
    
    return mock_connection, mock_cursor

@pytest.fixture
def mock_cursor():
    mock = Mock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    return mock


@pytest.fixture
def mock_connection(mock_cursor):
    mock = Mock()
    mock.cursor.return_value = mock_cursor
    return mock


@pytest.fixture
def pgsql_client_with_mocks(mock_connection):
    with patch('sources.database_client.load_dotenv'), \
         patch('sources.database_client.os.getenv') as mock_getenv:
        
        mock_getenv.side_effect = lambda key, default=None: {
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass'
        }.get(key, default)
        
        client = PgsqlClient("test.env")
        client.connection = mock_connection
        return client
