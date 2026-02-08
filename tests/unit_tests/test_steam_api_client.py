import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from sources.steam_api_client import SteamAPIClient
import asyncio

class TestSteamAPIClient:
    
    @pytest.fixture
    def api_key(self):
        return "test_api_key"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, api_key):
        """Тест контекстного менеджера"""
        async with SteamAPIClient(api_key) as client:
            assert client.session is not None
            assert isinstance(client.session, aiohttp.ClientSession)
            assert client.api_key == api_key
        
        # После выхода из контекста сессия закрыта
        assert client.session.closed
    
    @pytest.mark.asyncio
    async def test_get_user_friends_success(self, api_key):
        """Тест успешного получения списка друзей"""
        steam_id = 76561197960265728
        
        # Создаем клиент
        client = SteamAPIClient(api_key)
        
        # Создаем мок сессии с помощью MagicMock вместо AsyncMock
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        # Создаем мок для асинхронного контекстного менеджера response
        async def mock_json():
            return {
                "friendslist": {
                    "friends": [
                        {"steamid": "76561197960265729"},
                        {"steamid": "76561197960265730"},
                        {"steamid": "76561197960265731"}
                    ]
                }
            }
        
        # Создаем асинхронный контекстный менеджер для response
        class MockResponseContext:
            def __init__(self, status=200):
                self.status = status
                self._json_result = None
            
            async def json(self):
                if self._json_result is None:
                    return await mock_json()
                return self._json_result
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        # Создаем асинхронный контекстный менеджер для session.get()
        class MockGetContext:
            def __init__(self, status=200, json_result=None):
                self.response = MockResponseContext(status)
                if json_result is not None:
                    self.response._json_result = json_result
            
            async def __aenter__(self):
                return self.response
            
            async def __aexit__(self, *args):
                pass
        
        # Настраиваем mock
        mock_session.get.return_value = MockGetContext(status=200)
        
        # Подменяем сессию в клиенте
        client.session = mock_session
        
        # Вызываем метод
        friends = await client.get_user_friends(steam_id)
        
        # Проверяем результат
        assert len(friends) == 3
        assert friends == [76561197960265729, 76561197960265730, 76561197960265731]
        
        # Проверяем вызов API
        mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_friends_empty_response(self, api_key):
        """Тест получения пустого списка друзей"""
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {}  # Пустой ответ
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        friends = await client.get_user_friends(steam_id)
        assert friends == []
    
    @pytest.mark.asyncio
    async def test_get_user_friends_error_response(self, api_key):
        """Тест обработки ошибки API"""
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 500  # Серверная ошибка
            
            async def json(self):
                return {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        friends = await client.get_user_friends(steam_id)
        assert friends == []
    
    @pytest.mark.asyncio
    async def test_get_user_owned_games_success(self, api_key):
        """Тест успешного получения списка игр пользователя"""
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {
                    "response": {
                        "games": [
                            {"appid": 730, "playtime_forever": 1500, "name": "Counter-Strike: Global Offensive"},
                            {"appid": 570, "playtime_forever": 500, "name": "Dota 2"}
                        ]
                    }
                }
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        games = await client.get_user_owned_games(steam_id)
        
        assert len(games) == 2
        assert games[0]["appid"] == 730
        assert games[0]["playtime_forever"] == 1500
        assert games[1]["appid"] == 570
    
    @pytest.mark.asyncio
    async def test_get_user_owned_games_empty(self, api_key):
        """Тест получения пустого списка игр"""
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        games = await client.get_user_owned_games(steam_id)
        assert games == {}  # Согласно вашему коду, возвращается {}
    
    @pytest.mark.asyncio
    async def test_get_player_summaries_success(self, api_key):
        """Тест получения информации о пользователях"""
        steam_ids = [76561197960265729, 76561197960265730]
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {
                    "response": {
                        "players": [
                            {
                                "steamid": "76561197960265729",
                                "personaname": "User1",
                                "profileurl": "https://steamcommunity.com/id/user1/"
                            },
                            {
                                "steamid": "76561197960265730",
                                "personaname": "User2",
                                "profileurl": "https://steamcommunity.com/id/user2/"
                            }
                        ]
                    }
                }
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        players = await client.get_player_summaries(steam_ids)
        
        assert len(players) == 2
        assert players[0]["steamid"] == "76561197960265729"
        assert players[0]["personaname"] == "User1"
        assert players[1]["steamid"] == "76561197960265730"
    
    @pytest.mark.asyncio
    async def test_get_player_summaries_empty_list(self, api_key):
        """Тест с пустым списком ID"""
        client = SteamAPIClient(api_key)
        
        # Даже без мока сессии, метод должен вернуть пустой список
        players = await client.get_player_summaries([])
        assert players == []
    
    @pytest.mark.asyncio
    async def test_get_game_info_success(self, api_key):
        """Тест успешного получения информации об игре"""
        app_id = 730
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {
                    "730": {
                        "success": True,
                        "data": {
                            "name": "Counter-Strike: Global Offensive",
                            "short_description": "A competitive shooter",
                            "price_overview": {
                                "final": 1499
                            }
                        }
                    }
                }
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        result_id, game_data = await client.get_game_info(app_id)
        
        assert result_id == 730
        assert game_data["name"] == "Counter-Strike: Global Offensive"
        assert game_data["short_description"] == "A competitive shooter"
    
    @pytest.mark.asyncio
    async def test_get_game_info_not_found(self, api_key):
        """Тест получения информации о несуществующей игре"""
        app_id = 999999  # Несуществующий ID
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {
                    "999999": {
                        "success": False
                    }
                }
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockGetContext:
            async def __aenter__(self):
                return MockResponseContext()
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext()
        client.session = mock_session
        
        result_id, game_data = await client.get_game_info(app_id)
        assert result_id is None
        assert game_data is None
    
    @pytest.mark.asyncio
    async def test_get_featured_games_summary_success(self, api_key):
        """Тест получения списка популярных игр"""
        client = SteamAPIClient(api_key)
        
        # Создаем мок для ClientSession
        class MockResponse:
            def __init__(self):
                self.status = 200
            
            async def json(self):
                return {
                    "top_sellers": {
                        "items": [
                            {"id": 730, "name": "CS:GO", "final_price": 1499},
                            {"id": 570, "name": "Dota 2", "final_price": 0},
                            {"id": 1172470, "name": "Apex Legends", "final_price": 0},
                            {"id": 578080, "name": "PUBG", "final_price": 2999, "discount_percent": 50},
                            {"id": 271590, "name": "GTA V", "final_price": 1499}
                        ]
                    },
                    "new_releases": {
                        "items": [
                            {"id": 1234560, "name": "New Game 1", "final_price": 2999},
                            {"id": 1234561, "name": "New Game 2", "final_price": 1999, "discount_percent": 20},
                            {"id": 1234562, "name": "New Game 3", "final_price": 1499},
                            {"id": 1234563, "name": "New Game 4", "final_price": 999},
                            {"id": 1234564, "name": "New Game 5", "final_price": 499}
                        ]
                    },
                    "coming_soon": {
                        "items": [
                            {"id": 2234560, "name": "Upcoming Game 1", "release_date": "Oct 15, 2023"},
                            {"id": 2234561, "name": "Upcoming Game 2", "release_date": "Nov 1, 2023"},
                            {"id": 2234562, "name": "Upcoming Game 3", "release_date": "Dec 1, 2023"},
                            {"id": 2234563, "name": "Upcoming Game 4", "release_date": "Jan 15, 2024"},
                            {"id": 2234564, "name": "Upcoming Game 5", "release_date": "Feb 1, 2024"}
                        ]
                    }
                }
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        class MockSession:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
            
            async def get(self, url, params=None):
                # Важно: метод get должен вернуть контекстный менеджер, а не response
                class MockResponseContext:
                    async def __aenter__(self):
                        return MockResponse()
                    
                    async def __aexit__(self, *args):
                        pass
                
                return MockResponseContext()
        
        # Патчим aiohttp.ClientSession чтобы вернуть наш мок
        with patch('aiohttp.ClientSession', return_value=MockSession()):
            result = await client.get_featured_games_summary()
            
            # Проверяем структуру
            assert 'top_sellers' in result
            assert 'new_releases' in result
            assert 'coming_soon' in result
            
            # Проверяем данные
            assert len(result['top_sellers']) == 5
            assert result['top_sellers'][0]['id'] == 730
            assert result['top_sellers'][0]['name'] == 'CS:GO'
            assert result['top_sellers'][0]['price'] == 1499
            
            # Проверяем что PUBG имеет скидку
            pubg_game = next(g for g in result['top_sellers'] if g['id'] == 578080)
            assert pubg_game['discount'] == 50
            
            # Проверяем coming_soon
            assert result['coming_soon'][0]['release_date'] == 'Oct 15, 2023'
            assert 'price' not in result['coming_soon'][0]


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    async def test_methods_without_context_manager(self, api_key="test_key"):
        """Тест вызова методов без использования контекстного менеджера"""
        client = SteamAPIClient(api_key)
        
        # Session не инициализирован
        assert client.session is None
        
        # Попытка вызвать метод без сессии вызовет AttributeError
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'get'"):
            await client.get_user_friends(76561197960265728)
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, api_key):
        """Тест обработки сетевых ошибок"""
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        # Создаем мок сессии
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        # Симулируем сетевую ошибку при вызове get
        mock_session.get.side_effect = Exception("Network error")
        
        client.session = mock_session
        
        # Метод должен вернуть пустой список при ошибке
        friends = await client.get_user_friends(steam_id)
        assert friends == []