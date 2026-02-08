"""
Тесты для класса PgsqlClient из sources/database_client.py
"""
import pytest
import psycopg2
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Импортируем тестируемый класс из sources
from sources.database_client import PgsqlClient


# Вспомогательные фикстуры для создания моков
@pytest.fixture
def mock_cursor():
    """Создает мок курсора с поддержкой контекстного менеджера"""
    mock = Mock()
    mock.__enter__ = Mock(return_value=mock)  # При входе в контекст возвращает сам себя
    mock.__exit__ = Mock(return_value=None)   # При выходе ничего не возвращает
    return mock


@pytest.fixture
def mock_connection(mock_cursor):
    """Создает мок подключения с курсором"""
    mock = Mock()
    mock.cursor.return_value = mock_cursor
    return mock


@pytest.fixture
def pgsql_client_with_mocks(mock_connection):
    """Создает клиент PgsqlClient с подмененными зависимостями"""
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


class TestPgsqlClientInitialization:
    """Тесты инициализации клиента базы данных"""
    
    def test_init_loads_env_file(self):
        """Тест, что клиент загружает env файл при инициализации"""
        # Arrange
        with patch('sources.database_client.load_dotenv') as mock_load_dotenv, \
             patch('sources.database_client.os.getenv') as mock_getenv:
            
            mock_getenv.side_effect = lambda key, default=None: {
                'DB_HOST': 'test_host',
                'DB_PORT': '5432',
                'DB_NAME': 'test_db',
                'DB_USER': 'test_user',
                'DB_PASSWORD': 'test_pass'
            }.get(key, default)
            
            # Act
            client = PgsqlClient("test.env")
            
            # Assert
            mock_load_dotenv.assert_called_once_with("test.env")
            assert client.db_host == 'test_host'
            assert client.db_port == 5432
            assert client.db_base == 'test_db'
            assert client.db_user == 'test_user'
            assert client.db_pass == 'test_pass'
            assert client.connection is None
    
    def test_init_with_defaults(self):
        """Тест инициализации с значениями по умолчанию"""
        # Arrange
        with patch('sources.database_client.load_dotenv') as mock_load_dotenv, \
             patch('sources.database_client.os.getenv') as mock_getenv:
            
            mock_getenv.side_effect = lambda key, default=None: {
                'DB_NAME': 'test_db',
                'DB_USER': 'test_user',
                'DB_PASSWORD': 'test_pass'
                # DB_HOST и DB_PORT не заданы - должны использоваться значения по умолчанию
            }.get(key, default)
            
            # Act
            client = PgsqlClient("test.env")
            
            # Assert
            assert client.db_host == 'localhost'  # Значение по умолчанию
            assert client.db_port == 5432         # Значение по умолчанию
            assert client.db_base == 'test_db'
            assert client.db_user == 'test_user'
            assert client.db_pass == 'test_pass'


class TestGetConnection:
    """Тесты метода get_connection"""
    
    @patch('sources.database_client.psycopg2.connect')
    def test_get_connection_success(self, mock_connect):
        """Тест успешного создания подключения"""
        # Arrange
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
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
            
            # Act
            connection = client.get_connection()
            
            # Assert
            mock_connect.assert_called_once_with(
                host='localhost',
                port=5432,
                database='test_db',
                user='test_user',
                password='test_pass'
            )
            assert connection == mock_connection


class TestSelectMethod:
    """Тесты метода select"""
    
    def test_select_basic_query(self, pgsql_client_with_mocks, mock_cursor):
        """Тест простого SELECT запроса без условий"""
        # Arrange
        mock_cursor.fetchall.return_value = [('row1', 'data1'), ('row2', 'data2')]
        mock_cursor.description = [('col1',), ('col2',)]
        
        # Act
        result = pgsql_client_with_mocks.select(
            attributes=['col1', 'col2'],
            table='users'
        )
        
        # Assert
        assert result == ([('row1', 'data1'), ('row2', 'data2')], [('col1',), ('col2',)])
        mock_cursor.execute.assert_called_once_with("SELECT col1, col2 FROM users")
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_select_with_where_clause(self, pgsql_client_with_mocks, mock_cursor):
        """Тест SELECT запроса с условием WHERE"""
        # Arrange
        mock_cursor.fetchall.return_value = [('user1',)]
        mock_cursor.description = [('username',)]
        
        # Act
        result = pgsql_client_with_mocks.select(
            attributes=['username'],
            table='users',
            where='id = 123'
        )
        
        # Assert
        mock_cursor.execute.assert_called_once_with("SELECT username FROM users WHERE id = 123")
        assert result == ([('user1',)], [('username',)])
    
    def test_select_with_complex_where(self, pgsql_client_with_mocks, mock_cursor):
        """Тест SELECT запроса со сложным условием WHERE"""
        # Arrange
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        
        # Act
        pgsql_client_with_mocks.select(
            attributes=['*'],
            table='games',
            where="release_date > '2023-01-01' AND price < 50"
        )
        
        # Assert
        expected_query = "SELECT * FROM games WHERE release_date > '2023-01-01' AND price < 50"
        mock_cursor.execute.assert_called_once_with(expected_query)
    
    def test_select_empty_result(self, pgsql_client_with_mocks, mock_cursor):
        """Тест SELECT запроса с пустым результатом"""
        # Arrange
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        
        # Act
        result = pgsql_client_with_mocks.select(
            attributes=['id', 'name'],
            table='games',
            where='id = 999'
        )
        
        # Assert
        assert result == ([], [])
        mock_cursor.execute.assert_called_once_with("SELECT id, name FROM games WHERE id = 999")
    
    def test_select_creates_connection_if_none(self, mock_connection, mock_cursor):
        """Тест, что select создаёт подключение если его нет"""
        # Arrange
        with patch('sources.database_client.load_dotenv'), \
             patch('sources.database_client.os.getenv'):
            
            client = PgsqlClient("test.env")
            mock_cursor.fetchall.return_value = [('test',)]
            mock_cursor.description = [('data',)]
            
            with patch.object(client, 'get_connection', return_value=mock_connection) as mock_get_conn:
                # Act
                result = client.select(['data'], 'test_table')
                
                # Assert
                mock_get_conn.assert_called_once()
                assert client.connection == mock_connection
                assert result == ([('test',)], [('data',)])
    
    def test_select_with_psycopg2_error(self, pgsql_client_with_mocks, mock_cursor):
        """Тест обработки ошибки psycopg2 при SELECT"""
        # Arrange
        mock_cursor.execute.side_effect = psycopg2.Error("SQL error")
        
        # Act & Assert
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.select(['col'], 'table')
        
        # Должен быть вызван rollback
        pgsql_client_with_mocks.connection.rollback.assert_called_once()
    
    def test_select_with_psycopg2_error_and_rollback_fails(self, pgsql_client_with_mocks, mock_cursor):
        """Тест, когда и execute и rollback выбрасывают ошибки"""
        # Arrange
        mock_cursor.execute.side_effect = psycopg2.Error("SQL error")
        pgsql_client_with_mocks.connection.rollback.side_effect = psycopg2.Error("Rollback failed")
        
        # Act & Assert
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.select(['col'], 'table')
        
        # Проверяем, что connection был сброшен в None
        assert pgsql_client_with_mocks.connection is None


class TestInsertMethod:
    """Тесты метода insert"""
    
    def test_insert_basic(self, pgsql_client_with_mocks, mock_cursor):
        """Тест простого INSERT запроса"""
        # Act
        pgsql_client_with_mocks.insert(
            attributes=['username', 'email'],
            table='users',
            data=['john_doe', 'john@example.com']
        )
        
        # Assert
        expected_query = "INSERT INTO users (username, email) VALUES (%s, %s)"
        mock_cursor.execute.assert_called_once_with(expected_query, ['john_doe', 'john@example.com'])
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_insert_multiple_values(self, pgsql_client_with_mocks, mock_cursor):
        """Тест INSERT запроса с несколькими значениями"""
        # Act
        pgsql_client_with_mocks.insert(
            attributes=['id', 'name', 'price', 'release_date'],
            table='games',
            data=[123, 'Cyberpunk 2077', 59.99, '2020-12-10']
        )
        
        # Assert
        expected_query = "INSERT INTO games (id, name, price, release_date) VALUES (%s, %s, %s, %s)"
        mock_cursor.execute.assert_called_once_with(
            expected_query, 
            [123, 'Cyberpunk 2077', 59.99, '2020-12-10']
        )
    
    def test_insert_with_special_characters(self, pgsql_client_with_mocks, mock_cursor):
        """Тест INSERT запроса со специальными символами в данных"""
        # Act
        pgsql_client_with_mocks.insert(
            attributes=['name', 'description'],
            table='games',
            data=["O'Brien's Game", "It's a test game with 'quotes'"]
        )
        
        # Assert
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args[0][0] == "INSERT INTO games (name, description) VALUES (%s, %s)"
        assert "O'Brien's Game" in call_args[0][1]
    
    def test_insert_creates_connection_if_none(self, mock_connection, mock_cursor):
        """Тест, что insert создаёт подключение если его нет"""
        # Arrange
        with patch('sources.database_client.load_dotenv'), \
             patch('sources.database_client.os.getenv'):
            
            client = PgsqlClient("test.env")
            
            with patch.object(client, 'get_connection', return_value=mock_connection) as mock_get_conn:
                # Act
                client.insert(['col'], 'table', ['value'])
                
                # Assert
                mock_get_conn.assert_called_once()
                assert client.connection == mock_connection
    
    def test_insert_with_psycopg2_error(self, pgsql_client_with_mocks, mock_cursor):
        """Тест обработки ошибки psycopg2 при INSERT"""
        # Arrange
        mock_cursor.execute.side_effect = psycopg2.Error("Duplicate key")
        
        # Act & Assert
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.insert(['col'], 'table', ['value'])
        
        # Должен быть вызван rollback
        pgsql_client_with_mocks.connection.rollback.assert_called_once()


class TestUpdateMethod:
    """Тесты метода update"""
    
    def test_update_basic(self, pgsql_client_with_mocks, mock_cursor):
        """Тест простого UPDATE запроса"""
        # Act
        pgsql_client_with_mocks.update(
            attributes=['username', 'email'],
            table='users',
            data=['new_username', 'new_email@example.com'],
            id_column='user_id',
            id=123
        )
        
        # Assert
        expected_query = "UPDATE users SET username = 'new_username', email = 'new_email@example.com' WHERE user_id = 123"
        mock_cursor.execute.assert_called_once_with(expected_query)
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_update_single_field(self, pgsql_client_with_mocks, mock_cursor):
        """Тест UPDATE запроса с одним полем"""
        # Act
        pgsql_client_with_mocks.update(
            attributes=['last_login'],
            table='users',
            data=['2024-01-15 10:30:00'],
            id_column='id',
            id=456
        )
        
        # Assert
        expected_query = "UPDATE users SET last_login = '2024-01-15 10:30:00' WHERE id = 456"
        mock_cursor.execute.assert_called_once_with(expected_query)
    
    def test_update_with_numeric_id(self, pgsql_client_with_mocks, mock_cursor):
        """Тест UPDATE запроса с числовым ID"""
        # Act
        pgsql_client_with_mocks.update(
            attributes=['playtime'],
            table='user_games',
            data=[150],
            id_column='game_id',
            id=789
        )
        
        # Assert
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "playtime = '150'" in call_args[0][0]
        assert "WHERE game_id = 789" in call_args[0][0]
    
    def test_update_with_string_id(self, pgsql_client_with_mocks, mock_cursor):
        """Тест UPDATE запроса со строковым ID"""
        # Act
        pgsql_client_with_mocks.update(
            attributes=['status'],
            table='orders',
            data=['completed'],
            id_column='order_code',
            id='ABC-123-XYZ'
        )
        
        # Assert
        expected_query = "UPDATE orders SET status = 'completed' WHERE order_code = 'ABC-123-XYZ'"
        mock_cursor.execute.assert_called_once_with(expected_query)
    
    def test_update_creates_connection_if_none(self, mock_connection, mock_cursor):
        """Тест, что update создаёт подключение если его нет"""
        # Arrange
        with patch('sources.database_client.load_dotenv'), \
             patch('sources.database_client.os.getenv'):
            
            client = PgsqlClient("test.env")
            
            with patch.object(client, 'get_connection', return_value=mock_connection) as mock_get_conn:
                # Act
                client.update(['col'], 'table', ['value'], 'id', 1)
                
                # Assert
                mock_get_conn.assert_called_once()
                assert client.connection == mock_connection


class TestDeleteMethod:
    """Тесты метода delete"""
    
    def test_delete_basic(self, pgsql_client_with_mocks, mock_cursor):
        """Тест простого DELETE запроса"""
        # Act
        pgsql_client_with_mocks.delete(
            attributes=['1', '2', '3'],
            table='temp_data'
        )
        
        # Assert
        expected_query = "DELETE FROM temp_data WHERE id IN (1, 2, 3)"
        mock_cursor.execute.assert_called_once_with(expected_query)
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_delete_single_id(self, pgsql_client_with_mocks, mock_cursor):
        """Тест DELETE запроса с одним ID"""
        # Act
        pgsql_client_with_mocks.delete(
            attributes=['999'],
            table='logs'
        )
        
        # Assert
        expected_query = "DELETE FROM logs WHERE id IN (999)"
        mock_cursor.execute.assert_called_once_with(expected_query)


class TestErrorHandling:
    """Тесты обработки ошибок во всех методах"""
    
    def test_all_methods_rollback_on_error(self, pgsql_client_with_mocks, mock_cursor):
        """Тест, что все методы вызывают rollback при ошибке"""
        # Настраиваем курсор так, чтобы он всегда выбрасывал ошибку
        mock_cursor.execute.side_effect = psycopg2.Error("Test error")
        
        methods_to_test = [
            ('select', (['col'], 'table')),
            ('insert', (['col'], 'table', ['value'])),
            ('update', (['col'], 'table', ['value'], 'id', 1)),
            ('delete', (['1'], 'table')),
        ]
        
        for method_name, args in methods_to_test:
            # Сбрасываем счетчик rollback перед каждым тестом
            pgsql_client_with_mocks.connection.rollback.reset_mock()
            
            # Test each method
            with pytest.raises(psycopg2.Error):
                method = getattr(pgsql_client_with_mocks, method_name)
                method(*args)
            
            # Verify rollback was called
            pgsql_client_with_mocks.connection.rollback.assert_called_once()
    
    def test_rollback_failure_sets_connection_to_none(self, pgsql_client_with_mocks, mock_cursor):
        """Тест, что при ошибке rollback connection устанавливается в None"""
        # Arrange
        mock_cursor.execute.side_effect = psycopg2.Error("SQL error")
        pgsql_client_with_mocks.connection.rollback.side_effect = psycopg2.Error("Rollback failed")
        
        # Act & Assert
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.select(['col'], 'table')
        
        # Connection should be set to None
        assert pgsql_client_with_mocks.connection is None


class TestSQLInjectionSafety:
    """Тесты безопасности от SQL-инъекций"""
    
    def test_select_sql_injection_attempt(self, pgsql_client_with_mocks, mock_cursor):
        """Тест попытки SQL-инъекции в WHERE условие"""
        # Потенциально опасное условие
        dangerous_where = "id = 1; DROP TABLE users; --"
        
        # Act
        pgsql_client_with_mocks.select(
            attributes=['*'],
            table='users',
            where=dangerous_where
        )
        
        # Assert
        call_args = mock_cursor.execute.call_args
        assert "DROP TABLE" in call_args[0][0]
    
    def test_insert_uses_parameterized_query(self, pgsql_client_with_mocks, mock_cursor):
        """Тест, что INSERT использует параметризованные запросы"""
        # Потенциально опасные данные
        dangerous_data = ["test'; DROP TABLE users; --", "hacker@example.com"]
        
        # Act
        pgsql_client_with_mocks.insert(
            attributes=['username', 'email'],
            table='users',
            data=dangerous_data
        )
        
        # Assert
        call_args = mock_cursor.execute.call_args
        assert '%s' in call_args[0][0]  # Должны быть placeholders
        # Данные передаются отдельно от запроса
        assert call_args[0][1] == dangerous_data


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_empty_attributes_list(self, pgsql_client_with_mocks, mock_cursor):
        """Тест с пустым списком атрибутов"""
        # Act & Assert
        with pytest.raises(Exception):
            # Вызовет исключение при формировании SQL
            pgsql_client_with_mocks.select([], 'table')
    
    def test_empty_data_list_for_insert(self, pgsql_client_with_mocks, mock_cursor):
        """Тест INSERT с пустым списком данных"""
        # Act & Assert
        with pytest.raises(Exception):
            # Вызовет исключение при формировании SQL
            pgsql_client_with_mocks.insert(['col'], 'table', [])


# Минимальный тест для быстрой проверки
def test_simple_import():
    """Простой тест для проверки что импорт работает"""
    try:
        from sources.database_client import PgsqlClient
        assert True
    except ImportError:
        assert False, "Не удалось импортировать PgsqlClient из sources.database_client"


if __name__ == "__main__":
    # Для отладки
    pytest.main([__file__, "-v"])