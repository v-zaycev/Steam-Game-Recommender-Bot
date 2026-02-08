import aiohttp
from typing import Dict, List, Optional, Set

class SteamAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.steampowered.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def get_user_friends(self, steam_id: int) -> List[Dict]:
        """Получает список друзей пользователя"""
        url = f"{self.base_url}/ISteamUser/GetFriendList/v1/"
        params = {
            'key': self.api_key,
            'steamid': steam_id,
            'relationship': 'friend'
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return [ int(i['steamid']) for i in data.get('friendslist', {}).get('friends', [])]
            return []
    
    async def get_user_owned_games(self, steam_id: int) -> Dict:
        """Получает список игр пользователя с временем игры"""
        url = f"{self.base_url}/IPlayerService/GetOwnedGames/v1/"
        params = {
            'key': self.api_key,
            'steamid': steam_id,
            'include_played_free_games': 1,
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('response', {}).get('games',{})
            return {}
    
    async def get_player_summaries(self, steam_ids: List[int]) -> List[Dict]:
        """Получает информацию о пользователях"""
        if not steam_ids:
            return []
            
        url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            'key': self.api_key,
            'steamids': ','.join([str(id) for id in steam_ids])
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('response', {}).get('players', [])
            return []
    
    async def get_game_info(self, app_id : int) -> tuple[int, Dict]:
        """Получает информацию об играх из Steam Store"""

        result = (None, None)
        url = f"https://store.steampowered.com/api/appdetails"
        params = {
            'appids': app_id,
            'cc': 'us',  # Для обхода региональных ограничений
            'l': 'english'
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if str(app_id) in data:
                    app_data = data[str(app_id)]
                    if app_data.get('success', False):
                        result = (app_id, app_data.get('data', {}))        
        
        return result
    
    async def get_featured_games_summary(self) -> Dict[str, List[Dict]]:
        self.base_url = "https://store.steampowered.com/api/featuredcategories"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.base_url, 
                params={'cc': 'us', 'l': 'english'}
            ) as response:
                data = await response.json()
                
                result = {
                    'top_sellers': [],
                    'new_releases': [],
                    'coming_soon': []
                }
                
                seen_game_ids = set()
                
                # Вспомогательная функция для добавления игры
                def add_game(category: str, game: dict, is_coming_soon: bool = False):
                    game_id = game.get('id')
                    
                    # Пропускаем если игра уже была добавлена в любую категорию
                    if game_id in seen_game_ids:
                        return False
                    
                    seen_game_ids.add(game_id)
                    
                    game_data = {
                        'id': game_id,
                        'name': game.get('name')
                    }
                    
                    if is_coming_soon:
                        game_data['release_date'] = game.get('release_date', 'Coming Soon')
                    else:
                        game_data['price'] = game.get('final_price', 0)
                        if not is_coming_soon and 'discount_percent' in game:
                            game_data['discount'] = game.get('discount_percent', 0)
                    
                    result[category].append(game_data)
                    return True
                
                all_games_by_category = {}
                
                if 'top_sellers' in data:
                    all_games_by_category['top_sellers'] = data['top_sellers'].get('items', [])
                
                if 'new_releases' in data:
                    all_games_by_category['new_releases'] = data['new_releases'].get('items', [])
                
                if 'coming_soon' in data:
                    all_games_by_category['coming_soon'] = data['coming_soon'].get('items', [])
                
                for category in ['top_sellers', 'new_releases', 'coming_soon']:
                    if category in all_games_by_category:
                        games_added = 0
                        for game in all_games_by_category[category]:
                            if games_added >= 5:
                                break
                            
                            is_coming_soon = (category == 'coming_soon')
                            if add_game(category, game, is_coming_soon):
                                games_added += 1
                
                return result
    
