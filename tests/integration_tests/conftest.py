import pytest
import psycopg2
import os
from dotenv import load_dotenv

# Загружаем тестовый конфиг
load_dotenv("tests/integration_tests/.env.test")

@pytest.fixture(scope="session")
def db_config():
    """Конфиг для подключения к dev БД."""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'dbname': os.getenv('DB_NAME', 'steam_data'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '159753')
    }

@pytest.fixture(scope="session", autouse=True)
def setup_database_schema(db_config):
    """Один раз создаём таблицы и функции в dev БД."""
    conn = psycopg2.connect(**db_config)
    
    with conn.cursor() as cursor:
        # Выполняем ВСЕ SQL файлы (если их ещё нет)
        sql_files = [
            'create_tables.sql',
            'create_triggers.sql', 
            'friends_updates_function.sql',
            'recommendation_function.sql',
            'silimar_games_function.sql'
        ]
        
        for sql_file in sql_files:
            if os.path.exists(sql_file):
                with open(sql_file, 'r') as f:
                    try:
                        cursor.execute(f.read())
                    except psycopg2.Error as e:
                        print(f"Note: {sql_file} already applied: {e}")
                        conn.rollback()
                        continue
        
        conn.commit()
    conn.close()

@pytest.fixture(autouse=True)
def clean_database(db_config):
    """Перед КАЖДЫМ тестом полностью очищаем БД."""
    conn = psycopg2.connect(**db_config)
    
    with conn.cursor() as cursor:
        # Очищаем ВСЕ таблицы в правильном порядке (из-за foreign keys)
        tables = [
            'user_games',
            'friends', 
            'bot_users',
            'steam_users',
            'games'
        ]
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        
        # Сбрасываем sequence если нужно
        cursor.execute("""
            SELECT setval(pg_get_serial_sequence('friends', 'id'), 1, false);
            SELECT setval(pg_get_serial_sequence('user_games', 'id'), 1, false);
        """)
        
        conn.commit()
    
    conn.close()
    
    yield  # Тест запускается здесь
    
    # После теста можно дополнительно почистить,
    # но autouse=True уже сделает это перед следующим тестом