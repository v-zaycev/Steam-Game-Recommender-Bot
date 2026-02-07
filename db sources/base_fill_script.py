# fill_database.py
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

def get_db_connection():
    """Создаёт подключение к БД из .env"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def parse_steam_date(date_str):
    """Конвертирует Steam дату в формат PostgreSQL"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%b %d, %Y').date()
    except ValueError:
        return None

def fill_games_table():
    """Заполняет таблицу games из JSON файла"""
    json_path = os.getenv('GAMES_JSON_PATH', './games.json')
    
    if not os.path.exists(json_path):
        print(f"Файл {json_path} не найден")
        return
    
    print(f"Загружаем данные из {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        games_data = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        total = len(games_data)
        processed = 0
        
        for appid_str, game in games_data.items():
            appid = int(appid_str)
            
            # Парсим дату
            release_date = parse_steam_date(game.get('release_date'))
            
            # Теги как JSON
            tags = json.dumps(game.get('tags', {}))
            
            # Категории и жанры как массивы
            categories = game.get('categories', [])
            genres = game.get('genres', [])
            
            # Вставляем или обновляем
            cursor.execute("""
                INSERT INTO games (
                    steam_app_id, name, release_date, required_age,
                    short_description, header_image_url, categories,
                    genres, positive, negative, estimated_owners,
                    average_playtime_forever, average_playtime_2weeks,
                    median_playtime_forever, median_playtime_2weeks,
                    tags
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                appid,
                game.get('name'),
                release_date,
                game.get('required_age', 0),
                game.get('short_description'),
                game.get('header_image'),
                categories,
                genres,
                game.get('positive', 0),
                game.get('negative', 0),
                game.get('estimated_owners', ''),
                game.get('average_playtime_forever', 0),
                game.get('average_playtime_2weeks', 0),
                game.get('median_playtime_forever', 0),
                game.get('median_playtime_2weeks', 0),
                tags
            ))
            
            processed += 1
            if processed % 100 == 0:
                print(f"Обработано {processed}/{total} игр...")
        
        conn.commit()
        print(f"\nУспешно загружено {processed} игр в базу данных!")
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        sys.exit(1)
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    load_dotenv(".\\db sources\\db_config.env")
    print("Начинаем заполнение базы данных...")
    fill_games_table()
    print("Готово!")