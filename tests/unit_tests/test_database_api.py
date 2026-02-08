import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from psycopg2 import Error as Psycopg2Error
from sources.database_api import PgsqlApiClient
from sources.utils import parse_steam_date


class TestPgsqlApiClient:
    """Тесты для PgsqlApiClient"""
    
    @pytest.fixture
    def mock_client(self):
        """Создание мок-клиента с подменой родительского класса"""
        with patch('sources.database_api.PgsqlClient') as mock_parent:
            client = PgsqlApiClient(env='test.env')
            client.select = Mock()
            client.insert = Mock()
            client.update = Mock()
            client.delete = Mock()
            client.get_connection = Mock()
            client.connection = None
            yield client
    
    @pytest.fixture
    def mock_connection_cursor(self):
        """Создание мок-соединения и курсора с правильным контекстным менеджером"""
        # Создаем мок курсора
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        mock_cursor.fetchall = Mock()
        
        # Создаем мок соединения
        mock_connection = Mock()
        mock_connection.cursor = Mock(return_value=mock_cursor)
        mock_connection.commit = Mock()
        mock_connection.rollback = Mock()
        
        # Настраиваем контекстный менеджер для курсора
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        return mock_connection, mock_cursor

    def test_init(self, mock_client):
        """Тест инициализации клиента"""
        assert isinstance(mock_client, PgsqlApiClient)

    def test_get_game_info_success(self, mock_client):
        """Тест успешного получения информации об игре"""
        # Arrange
        expected_result = (
            [('Test Game', 'Short description', 'http://example.com/image.jpg')],
            [('name',), ('short_description',), ('header_image_url',)]
        )
        mock_client.select.return_value = expected_result
        
        # Act
        result = mock_client.get_game_info(730)
        
        # Assert
        mock_client.select.assert_called_once_with(
            ['name', 'short_description', 'header_image_url'],
            "games",
            "steam_app_id = 730"
        )
        assert result == ('Test Game', 'Short description', 'http://example.com/image.jpg')

    def test_get_game_info_not_found(self, mock_client):
        """Тест получения информации об игре, которой нет"""
        # Arrange
        mock_client.select.return_value = ([], [])
        
        # Act
        result = mock_client.get_game_info(999999)
        
        # Assert
        assert result is None

    def test_add_telegram_user_new(self, mock_client):
        """Тест добавления нового пользователя Telegram"""
        # Arrange
        mock_client.select.return_value = ([], [('tg_id',)])
        
        # Act
        result = mock_client.add_telegram_user(123456789)
        
        # Assert
        assert result is True
        mock_client.select.assert_called_once_with(['tg_id'], 'bot_users', "tg_id = 123456789")
        mock_client.insert.assert_called_once_with(['tg_id', 'steam_id'], 'bot_users', [123456789, None])

    def test_add_telegram_user_exists(self, mock_client):
        """Тест попытки добавления существующего пользователя Telegram"""
        # Arrange
        mock_client.select.return_value = ([(123456789,)], [('tg_id',)])
        
        # Act
        result = mock_client.add_telegram_user(123456789)
        
        # Assert
        assert result is False
        mock_client.select.assert_called_once_with(['tg_id'], 'bot_users', "tg_id = 123456789")
        mock_client.insert.assert_not_called()

    def test_add_game(self, mock_client):
        """Тест добавления игры"""
        # Arrange
        game_data = (
            730,
            {
                'name': 'Counter-Strike: Global Offensive',
                'release_date': {'date': 'Aug 21, 2012'},
                'tags': {'Action': True, 'FPS': True},
                'categories': [{'description': 'Multi-player'}],
                'genres': [{'description': 'Action'}],
                'required_age': 0,
                'short_description': 'Counter-Strike: Global Offensive',
                'header_image': 'http://example.com/image.jpg',
                'positive': 1000000,
                'negative': 10000,
                'estimated_owners': '10000000-20000000',
                'average_playtime_forever': 100,
                'average_playtime_2weeks': 10,
                'median_playtime_forever': 50,
                'median_playtime_2weeks': 5
            }
        )
        
        # Act
        PgsqlApiClient.add_game(mock_client, game_data)
        
        # Assert
        expected_categories = ['Multi-player']
        expected_genres = ['Action']
        expected_tags = json.dumps({'Action': True, 'FPS': True})
        expected_release_date = parse_steam_date('Aug 21, 2012')
        
        mock_client.insert.assert_called_once_with(
            [
                'steam_app_id', 'name', 'release_date', 'required_age',
                'short_description', 'header_image_url', 'categories',
                'genres', 'positive', 'negative', 'estimated_owners',
                'average_playtime_forever', 'average_playtime_2weeks',
                'median_playtime_forever', 'median_playtime_2weeks', 'tags'
            ],
            'games',
            [
                730,
                'Counter-Strike: Global Offensive',
                expected_release_date,
                0,
                'Counter-Strike: Global Offensive',
                'http://example.com/image.jpg',
                expected_categories,
                expected_genres,
                1000000,
                10000,
                '10000000-20000000',
                100,
                10,
                50,
                5,
                expected_tags
            ]
        )

    def test_get_steam_id_found(self, mock_client):
        """Тест получения Steam ID пользователя"""
        # Arrange
        mock_client.select.return_value = ([(76561197960265729,)], [('steam_id',)])
        
        # Act
        result = mock_client.get_steam_id(123456789)
        
        # Assert
        assert result == 76561197960265729
        mock_client.select.assert_called_once_with(['steam_id'], 'bot_users', "tg_id = 123456789")

    def test_get_steam_id_not_found(self, mock_client):
        """Тест получения Steam ID, когда его нет"""
        # Arrange
        mock_client.select.return_value = ([(None,)], [('steam_id',)])
        
        # Act
        result = mock_client.get_steam_id(123456789)
        
        # Assert
        assert result is None

    def test_get_steam_id_no_result(self, mock_client):
        """Тест получения Steam ID, когда пользователь не найден"""
        # Arrange
        mock_client.select.return_value = ([], [('steam_id',)])
        
        # Act
        result = mock_client.get_steam_id(123456789)
        
        # Assert
        assert result is None

    def test_add_steam_friends(self, mock_client):
        """Тест добавления друзей Steam"""
        # Arrange
        user_id = 76561197960265728
        friend_ids = [76561197960265729, 76561197960265730]
        
        # Act
        mock_client.add_steam_friends(user_id, friend_ids)
        
        # Assert
        assert mock_client.insert.call_count == 2
        mock_client.insert.assert_any_call(
            ['user1', 'user2'], 
            'friends', 
            [min(user_id, friend_ids[0]), max(user_id, friend_ids[0])]
        )
        mock_client.insert.assert_any_call(
            ['user1', 'user2'], 
            'friends', 
            [min(user_id, friend_ids[1]), max(user_id, friend_ids[1])]
        )

    def test_add_steam_users(self, mock_client):
        """Тест добавления пользователей Steam"""
        # Arrange
        steam_users = [
            {
                'steamid': '76561197960265728',
                'personaname': 'User1',
                'profileurl': 'http://steamcommunity.com/id/user1',
                'avatarmedium': 'http://example.com/avatar1.jpg'
            },
            {
                'steamid': '76561197960265729',
                'personaname': 'User2',
                'profileurl': 'http://steamcommunity.com/id/user2',
                'avatarmedium': 'http://example.com/avatar2.jpg'
            }
        ]
        
        # Act
        mock_client.add_steam_users(steam_users)
        
        # Assert
        assert mock_client.insert.call_count == 2
        mock_client.insert.assert_any_call(
            ['steam_user_id', 'username', 'profile_url', 'avatarmedium_url'],
            'steam_users',
            ['76561197960265728', 'User1', 'http://steamcommunity.com/id/user1', 'http://example.com/avatar1.jpg']
        )

    def test_add_user_games(self, mock_client):
        """Тест добавления игр пользователя"""
        # Arrange
        user_id = 76561197960265728
        games_info = [
            {'appid': 730, 'playtime_forever': 1000},
            {'appid': 570, 'playtime_forever': 500}
        ]
        
        # Act
        mock_client.add_user_games(user_id, games_info)
        
        # Assert
        assert mock_client.insert.call_count == 2
        mock_client.insert.assert_any_call(
            ['user_id', 'game_id', 'playtime_total'],
            'user_games',
            [user_id, 730, 1000]
        )

    def test_get_friends_updates_success(self, mock_client, mock_connection_cursor):
        """Тест успешного получения обновлений друзей"""
        # Arrange
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(730, 'Counter-Strike: Global Offensive'), (570, 'Dota 2')]
        
        # Act
        result = mock_client.get_friends_updates(76561197960265728)
        
        # Assert
        mock_client.get_connection.assert_called_once()
        # Проверяем что execute был вызван
        mock_cursor.execute.assert_called_once()
        
        # Получаем фактические аргументы вызова
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        # Проверяем что SQL содержит нужные элементы
        assert "SELECT game_id, game_name" in sql_query
        assert "FROM get_top_new_friend_games" in sql_query
        assert params == (76561197960265728, 5, 14)
        
        mock_connection.commit.assert_called_once()
        assert result == [(730, 'Counter-Strike: Global Offensive'), (570, 'Dota 2')]

    def test_get_friends_updates_with_existing_connection(self, mock_client, mock_connection_cursor):
        """Тест получения обновлений друзей с уже существующим соединением"""
        # Arrange
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.connection = mock_connection
        mock_cursor.fetchall.return_value = [(730, 'Counter-Strike: Global Offensive')]
        
        # Act
        result = mock_client.get_friends_updates(76561197960265728)
        
        # Assert
        mock_client.get_connection.assert_not_called()
        
        # Проверяем что execute был вызван
        mock_cursor.execute.assert_called_once()
        
        # Получаем аргументы вызова
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        # Проверяем содержание SQL запроса
        assert "SELECT game_id, game_name" in sql_query
        assert "FROM get_top_new_friend_games" in sql_query
        assert params == (76561197960265728, 5, 14)
        
        assert result == [(730, 'Counter-Strike: Global Offensive')]

    def test_get_friends_updates_error(self, mock_client):
        """Тест обработки ошибки при получении обновлений друзей (rollback успешен)"""
        # Arrange
        # Создаем мок соединения
        mock_connection = Mock()
        mock_cursor = Mock()
        
        # Настраиваем контекстный менеджер
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute = Mock(side_effect=Psycopg2Error("Connection error"))
        
        mock_connection.cursor = Mock(return_value=mock_cursor)
        mock_connection.rollback = Mock()  # rollback успешен
        
        # Устанавливаем соединение в клиенте
        mock_client.connection = mock_connection
        mock_client.get_connection = Mock(return_value=mock_connection)
        
        # Act & Assert
        with pytest.raises(Psycopg2Error):
            mock_client.get_friends_updates(76561197960265728)
        
        # Проверяем что rollback был вызван
        mock_connection.rollback.assert_called_once()
        # Соединение НЕ должно быть сброшено в None, так как rollback успешен
        assert mock_client.connection is not None
        assert mock_client.connection == mock_connection

    def test_get_friends_updates_error_with_rollback_error(self, mock_client):
        """Тест обработки ошибки при rollback"""
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        
        # Настраиваем контекстный менеджер
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute = Mock(side_effect=Psycopg2Error("Cursor error"))
        
        mock_connection.cursor = Mock(return_value=mock_cursor)
        # rollback тоже выбрасывает ошибку
        mock_connection.rollback = Mock(side_effect=Psycopg2Error("Rollback error"))
        
        mock_client.connection = mock_connection
        mock_client.get_connection = Mock(return_value=mock_connection)
        
        # Act & Assert
        with pytest.raises(Psycopg2Error):
            mock_client.get_friends_updates(76561197960265728)
        
        # Проверяем что rollback был вызван
        mock_connection.rollback.assert_called_once()
        # Соединение должно быть сброшено в None, так как rollback не удался
        assert mock_client.connection is None

    def test_get_similar_games_success(self, mock_client, mock_connection_cursor):
        """Тест успешного получения похожих игр"""
        # Arrange
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(570, 'Dota 2'), (440, 'Team Fortress 2')]
        
        # Act
        result = mock_client.get_similar_games(730, 5)
        
        # Assert
        mock_cursor.execute.assert_called_once()
        
        # Проверяем аргументы вызова
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM find_similar_games" in sql_query
        assert params == (730, 5)
        
        mock_connection.commit.assert_called_once()
        assert result == [(570, 'Dota 2'), (440, 'Team Fortress 2')]

    def test_get_similar_games_default_limit(self, mock_client, mock_connection_cursor):
        """Тест получения похожих игр с лимитом по умолчанию"""
        # Arrange
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(570, 'Dota 2')]
        
        # Act
        result = mock_client.get_similar_games(730)
        
        # Assert
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM find_similar_games" in sql_query
        assert params == (730, 5)
        
        assert result == [(570, 'Dota 2')]

    def test_get_recommendations_success(self, mock_client, mock_connection_cursor):
        """Тест успешного получения рекомендаций"""
        # Arrange
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [
            (730, 'Counter-Strike: Global Offensive'),
            (570, 'Dota 2'),
            (440, 'Team Fortress 2')
        ]
        
        # Act
        result = mock_client.get_recommendations(76561197960265728, 3)
        
        # Assert
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM recommend_by_user_profile" in sql_query
        assert params == (76561197960265728, 3)
        
        mock_connection.commit.assert_called_once()
        assert result == [
            (730, 'Counter-Strike: Global Offensive'),
            (570, 'Dota 2'),
            (440, 'Team Fortress 2')
        ]

    def test_get_recommendations_default_limit(self, mock_client, mock_connection_cursor):
        """Тест получения рекомендаций с лимитом по умолчанию"""
        # Arrange
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(730, 'Counter-Strike: Global Offensive')]
        
        # Act
        result = mock_client.get_recommendations(76561197960265728)
        
        # Assert
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM recommend_by_user_profile" in sql_query
        assert params == (76561197960265728, 5)
        
        assert result == [(730, 'Counter-Strike: Global Offensive')]

    def test_error_handling_in_select_methods(self, mock_client):
        """Тест обработки ошибок в методах с прямыми SQL-запросами"""
        test_cases = [
            ('get_friends_updates', (76561197960265728,)),
            ('get_similar_games', (730, 5)),
            ('get_recommendations', (76561197960265728, 5))
        ]
        
        for method_name, method_args in test_cases:
            # Arrange для каждого метода
            mock_connection = Mock()
            mock_cursor = Mock()
            
            # Настраиваем контекстный менеджер для курсора
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute = Mock(side_effect=Psycopg2Error("Test error"))
            
            # Настраиваем соединение
            mock_connection.cursor = Mock(return_value=mock_cursor)
            mock_connection.rollback = Mock()  # rollback успешен
            
            mock_client.connection = mock_connection
            mock_client.get_connection = Mock(return_value=mock_connection)
            
            # Act & Assert
            with pytest.raises(Psycopg2Error):
                method = getattr(mock_client, method_name)
                method(*method_args)
            
            # Проверяем, что был вызван rollback
            mock_connection.rollback.assert_called_once()
            
            # Соединение НЕ должно быть сброшено в None, так как rollback успешен
            assert mock_client.connection is not None
            assert mock_client.connection == mock_connection
            
            # Сбрасываем соединение для следующей итерации
            mock_client.connection = None

    def test_error_handling_with_rollback_error(self, mock_client):
        """Тест обработки ошибок когда rollback тоже падает"""
        test_cases = [
            ('get_friends_updates', (76561197960265728,)),
            ('get_similar_games', (730, 5)),
            ('get_recommendations', (76561197960265728, 5))
        ]
        
        for method_name, method_args in test_cases:
            # Arrange для каждого метода
            mock_connection = Mock()
            mock_cursor = Mock()
            
            # Настраиваем контекстный менеджер для курсора
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute = Mock(side_effect=Psycopg2Error("Test error"))
            
            # Настраиваем соединение
            mock_connection.cursor = Mock(return_value=mock_cursor)
            # rollback тоже выбрасывает ошибку
            mock_connection.rollback = Mock(side_effect=Psycopg2Error("Rollback error"))
            
            mock_client.connection = mock_connection
            mock_client.get_connection = Mock(return_value=mock_connection)
            
            # Act & Assert
            with pytest.raises(Psycopg2Error):
                method = getattr(mock_client, method_name)
                method(*method_args)
            
            # Проверяем, что был вызван rollback
            mock_connection.rollback.assert_called_once()
            
            # Соединение должно быть сброшено в None, так как rollback не удался
            assert mock_client.connection is None
            
            # Сбрасываем соединение для следующей итерации
            mock_client.connection = None

    def test_add_game_with_missing_fields(self, mock_client):
        """Тест добавления игры с отсутствующими полями"""
        # Arrange
        game_data = (
            730,
            {
                'name': 'Test Game',
                'release_date': {'date': 'Jan 1, 2020'},
                'tags': {},
                'categories': [],
                'genres': []
                # Отсутствуют другие поля
            }
        )
        
        # Act
        PgsqlApiClient.add_game(mock_client, game_data)
        
        # Assert
        mock_client.insert.assert_called_once()
        call_args = mock_client.insert.call_args[0]
        assert call_args[0] == [
            'steam_app_id', 'name', 'release_date', 'required_age',
            'short_description', 'header_image_url', 'categories',
            'genres', 'positive', 'negative', 'estimated_owners',
            'average_playtime_forever', 'average_playtime_2weeks',
            'median_playtime_forever', 'median_playtime_2weeks', 'tags'
        ]
        # Проверяем, что отсутствующие поля заменены значениями по умолчанию
        data = call_args[2]
        assert data[3] == 0  # required_age
        assert data[4] is None  # short_description
        assert data[5] is None  # header_image_url
        assert data[8] == 0  # positive
        assert data[9] == 0  # negative
        assert data[10] == ''  # estimated_owners
