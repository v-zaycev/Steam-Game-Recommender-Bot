import pytest
import psycopg2
from unittest.mock import Mock, patch, MagicMock

from sources.database_client import PgsqlClient

class TestPgsqlClientInitialization:  
    def test_init_loads_env_file(self):

        with patch('sources.database_client.load_dotenv') as mock_load_dotenv, \
             patch('sources.database_client.os.getenv') as mock_getenv:
            
            mock_getenv.side_effect = lambda key, default=None: {
                'DB_HOST': 'test_host',
                'DB_PORT': '5432',
                'DB_NAME': 'test_db',
                'DB_USER': 'test_user',
                'DB_PASSWORD': 'test_pass'
            }.get(key, default)
            
            client = PgsqlClient("test.env")
            
            mock_load_dotenv.assert_called_once_with("test.env")
            assert client.db_host == 'test_host'
            assert client.db_port == 5432
            assert client.db_base == 'test_db'
            assert client.db_user == 'test_user'
            assert client.db_pass == 'test_pass'
            assert client.connection is None
    
    def test_init_with_defaults(self):
        with patch('sources.database_client.load_dotenv') as mock_load_dotenv, \
             patch('sources.database_client.os.getenv') as mock_getenv:
            
            mock_getenv.side_effect = lambda key, default=None: {
                'DB_NAME': 'test_db',
                'DB_USER': 'test_user',
                'DB_PASSWORD': 'test_pass'
            }.get(key, default)
            
            client = PgsqlClient("test.env")
            
            assert client.db_host == 'localhost'  # Значение по умолчанию
            assert client.db_port == 5432         # Значение по умолчанию
            assert client.db_base == 'test_db'
            assert client.db_user == 'test_user'
            assert client.db_pass == 'test_pass'


class TestGetConnection:    
    @patch('sources.database_client.psycopg2.connect')
    def test_get_connection_success(self, mock_connect):
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
            
            connection = client.get_connection()
            
            mock_connect.assert_called_once_with(
                host='localhost',
                port=5432,
                database='test_db',
                user='test_user',
                password='test_pass'
            )
            assert connection == mock_connection


class TestSelectMethod:    
    def test_select_basic_query(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.fetchall.return_value = [('row1', 'data1'), ('row2', 'data2')]
        mock_cursor.description = [('col1',), ('col2',)]
        
        result = pgsql_client_with_mocks.select(
            attributes=['col1', 'col2'],
            table='users'
        )
        
        assert result == ([('row1', 'data1'), ('row2', 'data2')], [('col1',), ('col2',)])
        mock_cursor.execute.assert_called_once_with("SELECT col1, col2 FROM users")
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_select_with_where_clause(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.fetchall.return_value = [('user1',)]
        mock_cursor.description = [('username',)]
        
        result = pgsql_client_with_mocks.select(
            attributes=['username'],
            table='users',
            where='id = 123'
        )
        
        mock_cursor.execute.assert_called_once_with("SELECT username FROM users WHERE id = 123")
        assert result == ([('user1',)], [('username',)])
    
    def test_select_with_complex_where(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        
        pgsql_client_with_mocks.select(
            attributes=['*'],
            table='games',
            where="release_date > '2023-01-01' AND price < 50"
        )
        
        expected_query = "SELECT * FROM games WHERE release_date > '2023-01-01' AND price < 50"
        mock_cursor.execute.assert_called_once_with(expected_query)
    
    def test_select_empty_result(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        
        result = pgsql_client_with_mocks.select(
            attributes=['id', 'name'],
            table='games',
            where='id = 999'
        )
        
        assert result == ([], [])
        mock_cursor.execute.assert_called_once_with("SELECT id, name FROM games WHERE id = 999")
    
    def test_select_creates_connection_if_none(self, mock_connection, mock_cursor):
        with patch('sources.database_client.load_dotenv'), \
             patch('sources.database_client.os.getenv'):
            
            client = PgsqlClient("test.env")
            mock_cursor.fetchall.return_value = [('test',)]
            mock_cursor.description = [('data',)]
            
            with patch.object(client, 'get_connection', return_value=mock_connection) as mock_get_conn:
                result = client.select(['data'], 'test_table')
                
                mock_get_conn.assert_called_once()
                assert client.connection == mock_connection
                assert result == ([('test',)], [('data',)])
    
    def test_select_with_psycopg2_error(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.execute.side_effect = psycopg2.Error("SQL error")
        
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.select(['col'], 'table')
        
        pgsql_client_with_mocks.connection.rollback.assert_called_once()
    
    def test_select_with_psycopg2_error_and_rollback_fails(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.execute.side_effect = psycopg2.Error("SQL error")
        pgsql_client_with_mocks.connection.rollback.side_effect = psycopg2.Error("Rollback failed")
        
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.select(['col'], 'table')
        
        assert pgsql_client_with_mocks.connection is None


class TestInsertMethod:
    def test_insert_basic(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.insert(
            attributes=['username', 'email'],
            table='users',
            data=['john_doe', 'john@example.com']
        )
        
        expected_query = "INSERT INTO users (username, email) VALUES (%s, %s)"
        mock_cursor.execute.assert_called_once_with(expected_query, ['john_doe', 'john@example.com'])
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_insert_multiple_values(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.insert(
            attributes=['id', 'name', 'price', 'release_date'],
            table='games',
            data=[123, 'Cyberpunk 2077', 59.99, '2020-12-10']
        )
        
        expected_query = "INSERT INTO games (id, name, price, release_date) VALUES (%s, %s, %s, %s)"
        mock_cursor.execute.assert_called_once_with(
            expected_query, 
            [123, 'Cyberpunk 2077', 59.99, '2020-12-10']
        )
    
    def test_insert_creates_connection_if_none(self, mock_connection):
        with patch('sources.database_client.load_dotenv'), patch('sources.database_client.os.getenv'):
            
            client = PgsqlClient("test.env")
            
            with patch.object(client, 'get_connection', return_value=mock_connection) as mock_get_conn:
                client.insert(['col'], 'table', ['value'])
                
                mock_get_conn.assert_called_once()
                assert client.connection == mock_connection
    
    def test_insert_with_psycopg2_error(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.execute.side_effect = psycopg2.Error("Duplicate key")
        
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.insert(['col'], 'table', ['value'])
        
        pgsql_client_with_mocks.connection.rollback.assert_called_once()


class TestUpdateMethod:
    def test_update_basic(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.update(
            attributes=['username', 'email'],
            table='users',
            data=['new_username', 'example'],
            id_column='user_id',
            id=123
        )
        
        expected_query = "UPDATE users SET username = 'new_username', email = 'example' WHERE user_id = 123"
        mock_cursor.execute.assert_called_once_with(expected_query)
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_update_single_field(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.update(
            attributes=['last_login'],
            table='users',
            data=['2024-01-15 10:30:00'],
            id_column='id',
            id=456
        )
        
        expected_query = "UPDATE users SET last_login = '2024-01-15 10:30:00' WHERE id = 456"
        mock_cursor.execute.assert_called_once_with(expected_query)
    
    def test_update_with_numeric_id(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.update(
            attributes=['playtime'],
            table='user_games',
            data=[150],
            id_column='game_id',
            id=789
        )
        
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "playtime = '150'" in call_args[0][0]
        assert "WHERE game_id = 789" in call_args[0][0]
    
    def test_update_creates_connection_if_none(self, mock_connection):
        with patch('sources.database_client.load_dotenv'), \
             patch('sources.database_client.os.getenv'):
            
            client = PgsqlClient("test.env")
            
            with patch.object(client, 'get_connection', return_value=mock_connection) as mock_get_conn:
                client.update(['col'], 'table', ['value'], 'id', 1)
                
                mock_get_conn.assert_called_once()
                assert client.connection == mock_connection


class TestDeleteMethod:
    """Тесты метода delete"""
    
    def test_delete_basic(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.delete(
            attributes=['1', '2', '3'],
            table='temp_data'
        )
        
        expected_query = "DELETE FROM temp_data WHERE id IN (1, 2, 3)"
        mock_cursor.execute.assert_called_once_with(expected_query)
        pgsql_client_with_mocks.connection.commit.assert_called_once()
    
    def test_delete_single_id(self, pgsql_client_with_mocks, mock_cursor):
        pgsql_client_with_mocks.delete(
            attributes=['999'],
            table='logs'
        )
        
        expected_query = "DELETE FROM logs WHERE id IN (999)"
        mock_cursor.execute.assert_called_once_with(expected_query)


class TestErrorHandling:    
    def test_all_methods_rollback_on_error(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.execute.side_effect = psycopg2.Error("Test error")
        
        methods_to_test = [
            ('select', (['col'], 'table')),
            ('insert', (['col'], 'table', ['value'])),
            ('update', (['col'], 'table', ['value'], 'id', 1)),
            ('delete', (['1'], 'table')),
        ]
        
        for method_name, args in methods_to_test:
            pgsql_client_with_mocks.connection.rollback.reset_mock()
            
            with pytest.raises(psycopg2.Error):
                method = getattr(pgsql_client_with_mocks, method_name)
                method(*args)
            
            pgsql_client_with_mocks.connection.rollback.assert_called_once()
    
    def test_rollback_failure_sets_connection_to_none(self, pgsql_client_with_mocks, mock_cursor):
        mock_cursor.execute.side_effect = psycopg2.Error("SQL error")
        pgsql_client_with_mocks.connection.rollback.side_effect = psycopg2.Error("Rollback failed")
        
        with pytest.raises(psycopg2.Error):
            pgsql_client_with_mocks.select(['col'], 'table')
        
        assert pgsql_client_with_mocks.connection is None


class TestSQLInjectionSafety:
    def test_select_sql_injection_attempt(self, pgsql_client_with_mocks, mock_cursor):
        dangerous_where = "id = 1; DROP TABLE users; --"
        
        pgsql_client_with_mocks.select(
            attributes=['*'],
            table='users',
            where=dangerous_where
        )
        
        call_args = mock_cursor.execute.call_args
        assert "DROP TABLE" in call_args[0][0]
    
    def test_insert_uses_parameterized_query(self, pgsql_client_with_mocks, mock_cursor):
        dangerous_data = ["test'; DROP TABLE users; --", "hacker@example.com"]
        
        pgsql_client_with_mocks.insert(
            attributes=['username', 'email'],
            table='users',
            data=dangerous_data
        )
        
        call_args = mock_cursor.execute.call_args
        assert '%s' in call_args[0][0]  
        assert call_args[0][1] == dangerous_data
