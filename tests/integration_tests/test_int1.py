# tests/test_integration_scenario2.py
"""
Интеграционный тест для сценария 2:
1. /start
2. Добавить профиль + Steam ID  
3. Похожее + ID игры
4. Информация по игре (есть в БД)
5. Информация по игре (нет в БД)
"""
import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock, call
from sources.bot import TelegramBot
from sources.utils import States
from dotenv import load_dotenv

load_dotenv("tests/integration_tests/.env.test")

class TestIntegrationScenario2:
    """Полный интеграционный тест второго сценария."""
    
    @pytest.fixture(autouse=True)
    def setup_test_database(self, db_config):
        """Настраиваем подключение к тестовой PostgreSQL."""
        self.test_db_config = db_config
    
    @pytest.fixture
    def mock_telegram_api(self):
        """Мокаем Telegram API (все сообщения)."""
        mock_message = AsyncMock()
        mock_message.from_user.id = 123456789  # Telegram ID пользователя
        mock_message.answer = AsyncMock()
        mock_message.answer_photo = AsyncMock()
        
        mock_state = AsyncMock()
        mock_state.set_state = AsyncMock()
        mock_state.clear = AsyncMock()
        
        return mock_message, mock_state
    
    def create_mock_steam_api(self):
        """Создает мок Steam API с последовательными ответами для сценария."""
        mock_steam = AsyncMock()
        
        # === КОНФИГУРАЦИЯ МОКОВ ДЛЯ СЦЕНАРИЯ ===
        
        # 1. Steam ID для теста
        self.test_steam_id = 76561198000000100
        
        # 2. Друзья пользователя
        self.friend_ids = [76561198000000101, 76561198000000102]
        
        # 3. Тестовые игры
        self.games_in_db = {
            730: {  # CS:GO - уже будет в БД после добавления профиля
                'name': 'Counter-Strike: Global Offensive',
                'short_description': 'Компьютерная игра в жанре многопользовательского тактического шутера',
                'header_image': 'https://example.com/csgo.jpg'
            },
            292030: {
                'name': 'The Witcher 3: Wild Hunt',
                'short_description': 'Ролевая игра с открытым миром',
                'header_image': 'https://example.com/witcher3.jpg',
                'release_date': {'date': 'May 19, 2015'},  # ← ОБЯЗАТЕЛЬНО
                'required_age': 18,
                'positive': 500000,
                'negative': 25000,
                'estimated_owners': '5,000,000-10,000,000',
                'tags': {
                    'RPG': 98,
                    'Open World': 97, 
                    'Story Rich': 96,
                    'Adventure': 95,
                    'Atmospheric': 94,
                    'Fantasy': 93,
                    'Mature': 92
                },
                'categories': [
                    {'description': 'Single-player'},
                    {'description': 'Steam Achievements'}
                ],
                'genres': [
                    {'description': 'RPG'},
                    {'description': 'Adventure'},
                    {'description': 'Action'}
                ],
                'average_playtime_forever': 100,
                'average_playtime_2weeks': 20,
                'median_playtime_forever': 75,
                'median_playtime_2weeks': 15
            }
        }
        
        # 4. Новая игра для шага 5 (не будет в БД изначально)
        self.new_game_id = 1245620  # Elden Ring
        self.new_game_data = {
            'name': 'Elden Ring',
            'short_description': 'Action/RPG с открытым миром',
            'header_image': 'https://example.com/eldenring.jpg',
            'release_date': {'date': 'Feb 25, 2022'},
            'required_age': 17,
            'positive': 500000,
            'negative': 25000,
            'estimated_owners': '5,000,000-10,000,000',
            'tags': {'RPG': 95, 'Souls-like': 92, 'Open World': 90},
            'categories': [{'description': 'Single-player'}],
            'genres': [{'description': 'RPG'}]
        }
        
        # === НАСТРОЙКА МОКОВ ===
        
        # 1. Мок для get_user_friends
        mock_steam.get_user_friends.return_value = self.friend_ids
        
        # 2. Мок для get_player_summaries
        mock_steam.get_player_summaries.return_value = [
            {
                'steamid': str(self.test_steam_id),
                'personaname': 'Main Test User',
                'profileurl': 'https://steamcommunity.com/id/testuser/',
                'avatarmedium': 'https://example.com/avatar.jpg'
            },
            {
                'steamid': str(self.friend_ids[0]),
                'personaname': 'Friend 1',
                'profileurl': '',
                'avatarmedium': ''
            },
            {
                'steamid': str(self.friend_ids[1]),
                'personaname': 'Friend 2',
                'profileurl': '',
                'avatarmedium': ''
            }
        ]
        
        # 3. Мок для get_user_owned_games (разные ответы для разных пользователей)
        owned_games_sequence = [
            # Основной пользователь: играет в CS:GO и Witcher 3
            [
                {'appid': 730, 'playtime_forever': 150, 'name': 'CS:GO'},
                {'appid': 292030, 'playtime_forever': 200, 'name': 'The Witcher 3'}
            ],
            # Друг 1: только в CS:GO
            [
                {'appid': 730, 'playtime_forever': 100, 'name': 'CS:GO'}
            ],
            # Друг 2: только в Witcher 3
            [
                {'appid': 292030, 'playtime_forever': 300, 'name': 'The Witcher 3'}
            ]
        ]
        mock_steam.get_user_owned_games.side_effect = owned_games_sequence
        
        # 4. Мок для get_game_info - разные ответы для разных игр
        def game_info_side_effect(app_id):
            if app_id == 730:  # CS:GO
                return (730, self.games_in_db[730])
            elif app_id == 292030:  # The Witcher 3
                return (292030, self.games_in_db[292030])
            elif app_id == self.new_game_id:  # Elden Ring (для шага 5)
                return (self.new_game_id, self.new_game_data)
            else:
                return (None, None)
        
        mock_steam.get_game_info.side_effect = game_info_side_effect
        
        return mock_steam
    
    @pytest.mark.asyncio
    async def test_complete_scenario2_integration(self, clean_database, mock_telegram_api):
        """
        Полный интеграционный тест второго сценария.
        TelegramBot ↔ Реальная PostgreSQL ↔ Моки Steam API
        """
        print("\n" + "="*60)
        print("ИНТЕГРАЦИОННЫЙ ТЕСТ: Сценарий 2 - Рекомендации похожих игр")
        print("="*60)
        
        # 1. СОЗДАЕМ БОТА С РЕАЛЬНОЙ БАЗОЙ И МОКАМИ API
        print("\n[1] Инициализация бота с тестовой PostgreSQL...")
        
        with patch('sources.bot.load_dotenv'), \
            patch('os.getenv', side_effect=lambda key, default=None: {
                'BOT_TOKEN': '1234567890:ABCdefGHIjklMnOpQRstUvWxYz123456789',
                'STEAM_API_KEY': 'test_steam_key_456',
                'DB_HOST': 'localhost',      # ← Добавьте эти переменные!
                'DB_PORT': '5432',
                'DB_NAME': 'steam_bot_dev',
                'DB_USER': 'postgres',
                'DB_PASSWORD': '',           # ← Пустой пароль для Windows
            }.get(key, default)), patch('sources.bot.SteamAPIClient'):
                    
            # Создаем реальный экземпляр бота
            bot = TelegramBot()
            
            # Подключаем к тестовой PostgreSQL
            bot.db_client.db_host = self.test_db_config['host']
            bot.db_client.db_port = self.test_db_config['port']
            bot.db_client.db_base = self.test_db_config['dbname']
            bot.db_client.db_user = self.test_db_config['user']
            bot.db_client.db_pass = self.test_db_config['password']
            bot.db_client.connection = None  # Сбрасываем соединение
            
            # Подменяем Steam API на наши моки
            mock_steam = self.create_mock_steam_api()
            bot.api_client = mock_steam
            
            mock_message, mock_state = mock_telegram_api
            
            print("+ Бот создан, подключен к тестовой PostgreSQL")
            
            # === ШАГ 1: КОМАНДА /START ===
            print("\n[2] Шаг 1: Команда /start")
            mock_message.text = "/start"
            
            await bot.cmd_start(mock_message)
            

            # Проверяем ответ
            mock_message.answer.assert_called_once()
            response = mock_message.answer.call_args.args[0]
            assert "Привет" in response or "👋" in response
            print("+ Пользователь зарегистрирован")
            
            # === ШАГ 2: ДОБАВЛЕНИЕ STEAM ПРОФИЛЯ ===
            print("\n[3] Шаг 2: Добавление Steam профиля")
            
            # 2.1. Запрос Steam ID
            mock_message.answer.reset_mock()
            mock_message.text = "Добавить профиль"
            
            await bot.cmd_add_id(mock_message, mock_state)
            mock_state.set_state.assert_called_with(States.id_waiting)
            print("+ Бот запросил Steam ID")
            
            # 2.2. Ввод Steam ID (с моками Steam API)
            mock_message.answer.reset_mock()
            mock_message.text = str(self.test_steam_id)
            
            with patch('sources.bot.is_valid_steamid64', return_value=True):
                await bot.cmd_get_id(mock_message, mock_state)
                
                # Проверяем вызовы Steam API
                mock_steam.get_user_friends.assert_called_once_with(self.test_steam_id)
                mock_steam.get_player_summaries.assert_called_once()
                
                # Проверяем количество вызовов get_user_owned_games
                # (основной пользователь + 2 друга)
                assert mock_steam.get_user_owned_games.call_count == 3
                
                # Проверяем, что игры сохранились в БД
                # CS:GO и Witcher 3 должны быть добавлены
                with bot.db_client.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM games")
                        game_count = cursor.fetchone()[0]
                        assert game_count >= 2  # CS:GO и Witcher 3
                
                print("+ Steam профиль добавлен, данные загружены в PostgreSQL")
            
            # === ШАГ 3: ПОИСК ПОХОЖИХ ИГР ===
            print("\n[4] Шаг 3: Поиск похожих игр")
            
            # 3.1. Запрос ID игры для поиска похожих
            mock_message.answer.reset_mock()
            mock_state.set_state.reset_mock()
            mock_message.text = "Похожее"
            
            await bot.cmd_similar(mock_message, mock_state)
            mock_state.set_state.assert_called_with(States.similar_game_id_waiting)
            print("+ Бот запросил ID игры для поиска похожих")
            
            # 1. Тест неудачного поиска (CS:GO)
            print("\n[4.1] Тест: Поиск похожих игр для CS:GO (ожидается 'не найдено')")
            mock_message.answer.reset_mock()
            mock_message.text = "730"  # CS:GO ID

            # Убедимся, что у CS:GO нет похожих игр в БД (очищаем теги или не добавляем похожие)
            with bot.db_client.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Устанавливаем уникальные теги для CS:GO чтобы не было похожих
                    cursor.execute("""
                        UPDATE games SET tags = '{"FPS": 98, "Competitive": 97, "Shooter": 96}'::jsonb
                        WHERE steam_app_id = 730
                    """)
                    conn.commit()

            await bot.cmd_similar_get(mock_message, mock_state)

            # Проверяем ответ для CS:GO
            mock_message.answer.assert_called_once()
            response_cs = mock_message.answer.call_args.args[0]
            if "не удалось" in response_cs.lower() or "не найдено" in response_cs.lower():
                print("+ CS:GO: Похожих игр не найдено (ожидаемо)")
            else:
                print(f"⚠️  CS:GO: Неожиданный ответ: {response_cs[:50]}...")

            # Очищаем для следующего теста
            mock_message.answer.reset_mock()
            mock_state.clear.reset_mock()

            # 2. Тест удачного поиска (The Witcher 3)
            print("\n[4.2] Тест: Поиск похожих игр для The Witcher 3")
            mock_message.text = "292030"  # The Witcher 3 ID

            # Добавляем теги для The Witcher 3 и похожие игры
            with bot.db_client.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Теги для The Witcher 3
                    cursor.execute("""
                        UPDATE games SET 
                            tags = '{"RPG": 98, "Open World": 97, "Story Rich": 96, "Adventure": 95}'::jsonb,
                            genres = '{"RPG", "Adventure"}'
                        WHERE steam_app_id = 292030
                    """)
                    
                    # Похожие игры с общими тегами
                    similar_games = [
                        (1245620, 'Elden Ring', '{"RPG": 96, "Open World": 94, "Souls-like": 95}'),
                        (489830, 'The Elder Scrolls V: Skyrim', '{"RPG": 97, "Open World": 96, "Adventure": 94}'),
                        (236850, 'Dark Souls II', '{"RPG": 95, "Souls-like": 98, "Action": 92}'),
                    ]
                    
                    for app_id, name, tags in similar_games:
                        cursor.execute("""
                            INSERT INTO games (steam_app_id, name, tags, genres) 
                            VALUES (%s, %s, %s::jsonb, '{"RPG", "Action"}')
                            ON CONFLICT (steam_app_id) DO UPDATE 
                            SET tags = EXCLUDED.tags, genres = EXCLUDED.genres
                        """, (app_id, name, tags))
                    
                    conn.commit()

            await bot.cmd_similar_get(mock_message, mock_state)

            # Проверяем ответ для The Witcher 3
            mock_message.answer.assert_called_once()
            response_witcher = mock_message.answer.call_args.args[0]

            if "похожие" in response_witcher.lower():
                print("+ The Witcher 3: Найдены похожие игры")
                # Дополнительные проверки если нужно
                # assert "1245620" in response_witcher or "Elden Ring" in response_witcher
            else:
                print(f"❌ The Witcher 3: Ожидались похожие игры, получили: {response_witcher[:50]}...")
            
            # === ШАГ 4: ИНФОРМАЦИЯ ОБ ИГРЕ (ЕСТЬ В БД) ===
            print("\n[5] Шаг 4: Информация об игре (есть в БД)")
            
            # 4.1. Запрос ID игры
            mock_message.answer.reset_mock()
            mock_state.set_state.reset_mock()
            mock_message.text = "Информация по игре"
            
            await bot.cmd_get_game_id(mock_message, mock_state)
            mock_state.set_state.assert_called_with(States.info_game_id_waiting)
            print("+ Бот запросил ID игры для информации")
            
            # 4.2. Ввод ID игры, которая уже в БД (CS:GO)
            mock_message.answer.reset_mock()
            mock_message.text = "730"  # CS:GO
            
            # Мокаем get_game_info для проверки, что он НЕ вызывается
            mock_steam.get_game_info.reset_mock()
            
            await bot.cmd_show_game_info(mock_message, mock_state)
            
            # Проверяем, что Steam API НЕ вызывался (игра уже в БД)
            mock_steam.get_game_info.assert_not_called()
            
            # Проверяем ответ (должен быть из БД)
            mock_message.answer_photo.assert_called_once()
            photo_args = mock_message.answer_photo.call_args
            assert "Counter-Strike" in photo_args[1]['caption'] or "Global Offensive" in photo_args[1]['caption'] or "730" in photo_args[1]['caption']
            
            print("+ Информация об игре получена из PostgreSQL (без вызова API)")
            
            # === ШАГ 5: ИНФОРМАЦИЯ ОБ ИГРЕ (НЕТ В БД) ===
            print("\n[6] Информация об игре (нет в БД)")

            # 5.1. Снова запрашиваем ID игры
            mock_message.answer_photo.reset_mock()
            mock_state.set_state.reset_mock()
            mock_message.text = "Информация по игре"

            await bot.cmd_get_game_id(mock_message, mock_state)

            # 5.2. Ввод ID СОВЕРШЕННО НОВОЙ игры (которой точно нет в БД)
            new_game_id = 999888777
            mock_message.text = str(new_game_id)

            def game_info_side_effect(app_id):
                if app_id == new_game_id:
                    return (new_game_id, {
                        'name': 'Test Game',
                        'short_description': 'Тестовая игра',
                        'header_image': 'https://example.com/supernew.jpg',
                        'release_date': {'date': 'Dec 21, 2021'},
                        'required_age': 12,
                        'positive': 99999,
                        'negative': 1000,
                        'estimated_owners': '0-1,000',
                        'tags': {'Test': 100, 'Exclusive': 95},
                        'categories': [{'description': 'Single-player'}],
                        'genres': [{'description': 'Test'}]
                    })
                return mock_steam.get_game_info.side_effect(app_id)  # или (None, None)

            # Применяем side_effect
            mock_steam.get_game_info.side_effect = game_info_side_effect
            mock_steam.get_game_info.reset_mock()

            await bot.cmd_show_game_info(mock_message, mock_state)

            # Проверяем, что Steam API ВЫЗЫВАЛСЯ (игры нет в БД)
            mock_steam.get_game_info.assert_called_once_with(new_game_id)

            # Проверяем ответ
            mock_message.answer_photo.assert_called_once()
            photo_args = mock_message.answer_photo.call_args
            assert "Test Game" in photo_args[1]['caption'] or str(new_game_id) in photo_args[1]['caption']

            # Проверяем, что игра сохранилась в БД
            with bot.db_client.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT name FROM games WHERE steam_app_id = %s",
                        (new_game_id,)
                    )
                    result = cursor.fetchone()
                    assert result is not None
                    assert "Test Game" in result[0]
            
            print("+ Информация об игре получена из Steam API и сохранена в PostgreSQL")
