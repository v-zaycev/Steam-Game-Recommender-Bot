import pytest
import psycopg2
import os
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def db_config():
    return {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'dbname': os.getenv('DB_NAME', 'steam_data'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '159753')
    }

@pytest.fixture(autouse=True)
def clean_database(db_config):
    conn = psycopg2.connect(**db_config)
    
    with conn.cursor() as cursor:
        tables = [
            'user_games',
            'friends', 
            'bot_users',
            'steam_users',
            'games'
        ]
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        
        cursor.execute("""
            SELECT setval(pg_get_serial_sequence('friends', 'id'), 1, false);
            SELECT setval(pg_get_serial_sequence('user_games', 'id'), 1, false);
        """)
        
        conn.commit()
    
    conn.close()
    
    yield
 
@pytest.fixture(autouse=True)
def setup_test_database(self, db_config):
    self.test_db_config = db_config

@pytest.fixture
def mock_telegram_api():
    mock_message = AsyncMock()
    mock_message.from_user.id = 123456789
    mock_message.answer = AsyncMock()
    mock_message.answer_photo = AsyncMock()
    
    mock_state = AsyncMock()
    mock_state.set_state = AsyncMock()
    mock_state.clear = AsyncMock()
    
    return mock_message, mock_state    