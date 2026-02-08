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
        async with SteamAPIClient(api_key) as client:
            assert client.session is not None
            assert isinstance(client.session, aiohttp.ClientSession)
            assert client.api_key == api_key
        
        assert client.session.closed
    
    @pytest.mark.asyncio
    async def test_get_user_friends_success(self, api_key):
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
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
        
        class MockGetContext:
            def __init__(self, status=200, json_result=None):
                self.response = MockResponseContext(status)
                if json_result is not None:
                    self.response._json_result = json_result
            
            async def __aenter__(self):
                return self.response
            
            async def __aexit__(self, *args):
                pass
        
        mock_session.get.return_value = MockGetContext(status=200)
        client.session = mock_session
        friends = await client.get_user_friends(steam_id)
        
        assert len(friends) == 3
        assert friends == [76561197960265729, 76561197960265730, 76561197960265731]
        
        mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_friends_empty_response(self, api_key):
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
        steam_id = 76561197960265728
        
        client = SteamAPIClient(api_key)
        
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        
        class MockResponseContext:
            def __init__(self):
                self.status = 500 
            
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
        client = SteamAPIClient(api_key)
        
        players = await client.get_player_summaries([])
        assert players == []
    
    @pytest.mark.asyncio
    async def test_get_game_info_success(self, api_key):
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
        app_id = 999999
        
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

class TestEdgeCases: 
    @pytest.mark.asyncio
    async def test_methods_without_context_manager(self, api_key="test_key"):
        client = SteamAPIClient(api_key)
        
        assert client.session is None
        
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'get'"):
            await client.get_user_friends(76561197960265728)
    