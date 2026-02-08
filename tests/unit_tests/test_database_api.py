import pytest
import json
from unittest.mock import Mock, patch
from psycopg2 import Error as Psycopg2Error

from sources.database_api import PgsqlApiClient
from sources.utils import parse_steam_date

class TestPgsqlApiClient:
    def test_get_game_info_success(self, mock_client):
        expected_result = (
            [('Test Game', 'Short description', 'example')],
            [('name',), ('short_description',), ('header_image_url',)]
        )
        mock_client.select.return_value = expected_result
        
        result = mock_client.get_game_info(730)
        
        mock_client.select.assert_called_once_with(
            ['name', 'short_description', 'header_image_url'],
            "games",
            "steam_app_id = 730"
        )
        assert result == ('Test Game', 'Short description', 'example')

    def test_get_game_info_not_found(self, mock_client):
        mock_client.select.return_value = ([], [])
        
        result = mock_client.get_game_info(999999)
        
        assert result is None

    def test_add_telegram_user_new(self, mock_client):
        mock_client.select.return_value = ([], [('tg_id',)])
        
        result = mock_client.add_telegram_user(123456789)
        
        assert result is True
        mock_client.select.assert_called_once_with(['tg_id'], 'bot_users', "tg_id = 123456789")
        mock_client.insert.assert_called_once_with(['tg_id', 'steam_id'], 'bot_users', [123456789, None])

    def test_add_telegram_user_exists(self, mock_client):
        mock_client.select.return_value = ([(123456789,)], [('tg_id',)])
        
        result = mock_client.add_telegram_user(123456789)
        
        assert result is False
        mock_client.select.assert_called_once_with(['tg_id'], 'bot_users', "tg_id = 123456789")
        mock_client.insert.assert_not_called()

    def test_add_game(self, mock_client):
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
        
        PgsqlApiClient.add_game(mock_client, game_data)
        
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
        mock_client.select.return_value = ([(76561197960265729,)], [('steam_id',)])
        
        # Act
        result = mock_client.get_steam_id(123456789)
        
        # Assert
        assert result == 76561197960265729
        mock_client.select.assert_called_once_with(['steam_id'], 'bot_users', "tg_id = 123456789")

    def test_get_steam_id_not_found(self, mock_client):
        mock_client.select.return_value = ([(None,)], [('steam_id',)])
        
        result = mock_client.get_steam_id(123456789)
        
        assert result is None

    def test_get_steam_id_no_result(self, mock_client):
        mock_client.select.return_value = ([], [('steam_id',)])
        
        result = mock_client.get_steam_id(123456789)
        
        assert result is None

    def test_add_steam_friends(self, mock_client):
        user_id = 76561197960265728
        friend_ids = [76561197960265729, 76561197960265730]
        
        mock_client.add_steam_friends(user_id, friend_ids)
        
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
        
        mock_client.add_steam_users(steam_users)
        
        assert mock_client.insert.call_count == 2
        mock_client.insert.assert_any_call(
            ['steam_user_id', 'username', 'profile_url', 'avatarmedium_url'],
            'steam_users',
            ['76561197960265728', 'User1', 'http://steamcommunity.com/id/user1', 'http://example.com/avatar1.jpg']
        )

    def test_add_user_games(self, mock_client):
        user_id = 76561197960265728
        games_info = [
            {'appid': 730, 'playtime_forever': 1000},
            {'appid': 570, 'playtime_forever': 500}
        ]
        
        mock_client.add_user_games(user_id, games_info)
        
        assert mock_client.insert.call_count == 2
        mock_client.insert.assert_any_call(
            ['user_id', 'game_id', 'playtime_total'],
            'user_games',
            [user_id, 730, 1000]
        )

    def test_get_friends_updates_success(self, mock_client, mock_connection_cursor):
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(730, 'Counter-Strike: Global Offensive'), (570, 'Dota 2')]
        
        result = mock_client.get_friends_updates(76561197960265728)
        
        mock_client.get_connection.assert_called_once()
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT game_id, game_name" in sql_query
        assert "FROM get_top_new_friend_games" in sql_query
        assert params == (76561197960265728, 5, 14)
        
        mock_connection.commit.assert_called_once()
        assert result == [(730, 'Counter-Strike: Global Offensive'), (570, 'Dota 2')]

    def test_get_friends_updates_with_existing_connection(self, mock_client, mock_connection_cursor):
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.connection = mock_connection
        mock_cursor.fetchall.return_value = [(730, 'Counter-Strike: Global Offensive')]
        
        result = mock_client.get_friends_updates(76561197960265728)
        
        mock_client.get_connection.assert_not_called()
        
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT game_id, game_name" in sql_query
        assert "FROM get_top_new_friend_games" in sql_query
        assert params == (76561197960265728, 5, 14)
        
        assert result == [(730, 'Counter-Strike: Global Offensive')]

    def test_get_friends_updates_error(self, mock_client):
        mock_connection = Mock()
        mock_cursor = Mock()
        
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute = Mock(side_effect=Psycopg2Error("Connection error"))
        
        mock_connection.cursor = Mock(return_value=mock_cursor)
        mock_connection.rollback = Mock()  # rollback успешен
        
        mock_client.connection = mock_connection
        mock_client.get_connection = Mock(return_value=mock_connection)
        
        with pytest.raises(Psycopg2Error):
            mock_client.get_friends_updates(76561197960265728)
        
        mock_connection.rollback.assert_called_once()
        assert mock_client.connection is not None
        assert mock_client.connection == mock_connection

    def test_get_friends_updates_error_with_rollback_error(self, mock_client):
        mock_connection = Mock()
        mock_cursor = Mock()
        
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor.execute = Mock(side_effect=Psycopg2Error("Cursor error"))
        
        mock_connection.cursor = Mock(return_value=mock_cursor)
        mock_connection.rollback = Mock(side_effect=Psycopg2Error("Rollback error"))
        
        mock_client.connection = mock_connection
        mock_client.get_connection = Mock(return_value=mock_connection)
        
        with pytest.raises(Psycopg2Error):
            mock_client.get_friends_updates(76561197960265728)
        
        mock_connection.rollback.assert_called_once()

        assert mock_client.connection is None

    def test_get_similar_games_success(self, mock_client, mock_connection_cursor):
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(570, 'Dota 2'), (440, 'Team Fortress 2')]
        
        result = mock_client.get_similar_games(730, 5)
        
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM find_similar_games" in sql_query
        assert params == (730, 5)
        
        mock_connection.commit.assert_called_once()
        assert result == [(570, 'Dota 2'), (440, 'Team Fortress 2')]

    def test_get_similar_games_default_limit(self, mock_client, mock_connection_cursor):
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(570, 'Dota 2')]
        
        result = mock_client.get_similar_games(730)
        
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM find_similar_games" in sql_query
        assert params == (730, 5)
        
        assert result == [(570, 'Dota 2')]

    def test_get_recommendations_success(self, mock_client, mock_connection_cursor):
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [
            (730, 'Counter-Strike: Global Offensive'),
            (570, 'Dota 2'),
            (440, 'Team Fortress 2')
        ]
        
        result = mock_client.get_recommendations(76561197960265728, 3)
        
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
        mock_connection, mock_cursor = mock_connection_cursor
        mock_client.get_connection.return_value = mock_connection
        mock_cursor.fetchall.return_value = [(730, 'Counter-Strike: Global Offensive')]
        
        result = mock_client.get_recommendations(76561197960265728)
        
        mock_cursor.execute.assert_called_once()
        
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        assert "SELECT app_id, game_name" in sql_query
        assert "FROM recommend_by_user_profile" in sql_query
        assert params == (76561197960265728, 5)
        
        assert result == [(730, 'Counter-Strike: Global Offensive')]

    def test_error_handling_in_select_methods(self, mock_client):
        test_cases = [
            ('get_friends_updates', (76561197960265728,)),
            ('get_similar_games', (730, 5)),
            ('get_recommendations', (76561197960265728, 5))
        ]
        
        for method_name, method_args in test_cases:
            mock_connection = Mock()
            mock_cursor = Mock()
            
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute = Mock(side_effect=Psycopg2Error("Test error"))
            
            mock_connection.cursor = Mock(return_value=mock_cursor)
            mock_connection.rollback = Mock()  # rollback успешен
            
            mock_client.connection = mock_connection
            mock_client.get_connection = Mock(return_value=mock_connection)
            
            with pytest.raises(Psycopg2Error):
                method = getattr(mock_client, method_name)
                method(*method_args)
            
            mock_connection.rollback.assert_called_once()
            
            assert mock_client.connection is not None
            assert mock_client.connection == mock_connection
            
            mock_client.connection = None

    def test_error_handling_with_rollback_error(self, mock_client):
        """Тест обработки ошибок когда rollback тоже падает"""
        test_cases = [
            ('get_friends_updates', (76561197960265728,)),
            ('get_similar_games', (730, 5)),
            ('get_recommendations', (76561197960265728, 5))
        ]
        
        for method_name, method_args in test_cases:
            mock_connection = Mock()
            mock_cursor = Mock()
            
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.execute = Mock(side_effect=Psycopg2Error("Test error"))
            
            mock_connection.cursor = Mock(return_value=mock_cursor)
            mock_connection.rollback = Mock(side_effect=Psycopg2Error("Rollback error"))
            
            mock_client.connection = mock_connection
            mock_client.get_connection = Mock(return_value=mock_connection)
            
            with pytest.raises(Psycopg2Error):
                method = getattr(mock_client, method_name)
                method(*method_args)
            
            mock_connection.rollback.assert_called_once()
            
            assert mock_client.connection is None
            
            mock_client.connection = None

    def test_add_game_with_missing_fields(self, mock_client):
        game_data = (
            730,
            {
                'name': 'Test Game',
                'release_date': {'date': 'Jan 1, 2020'},
                'tags': {},
                'categories': [],
                'genres': []
            }
        )
        
        PgsqlApiClient.add_game(mock_client, game_data)
        
        mock_client.insert.assert_called_once()
        call_args = mock_client.insert.call_args[0]
        assert call_args[0] == [
            'steam_app_id', 'name', 'release_date', 'required_age',
            'short_description', 'header_image_url', 'categories',
            'genres', 'positive', 'negative', 'estimated_owners',
            'average_playtime_forever', 'average_playtime_2weeks',
            'median_playtime_forever', 'median_playtime_2weeks', 'tags'
        ]
        data = call_args[2]
        assert data[3] == 0  # required_age
        assert data[4] is None  # short_description
        assert data[5] is None  # header_image_url
        assert data[8] == 0  # positive
        assert data[9] == 0  # negative
        assert data[10] == ''  # estimated_owners
