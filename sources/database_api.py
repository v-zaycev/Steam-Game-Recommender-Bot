import json
from typing import Dict, List
import psycopg2
from sources.database_client import PgsqlClient

from sources.utils import parse_steam_date

class PgsqlApiClient(PgsqlClient):
    def __init__(self, env : str = None):
        super().__init__(env)

    
    def get_game_info(self, id : int) -> tuple | None: 
        params = [
            'name',
            'short_description',
            'header_image_url'
        ]
        result = self.select(params, "games", f"steam_app_id = {id}")

        return (result[0][0] if len(result[0]) != 0 else None)

    def add_telegram_user(self, tg_id: int) -> bool:
        result = self.select(['tg_id'], 'bot_users', f"tg_id = {tg_id}")
        
        if len(result[0]) > 0:
            return False
        
        self.insert(['tg_id', 'steam_id'], 'bot_users', [tg_id, None])
        return True
    
    def add_game(client, game_data : tuple[int, Dict]):        
        appid = game_data[0]
        game = game_data[1]
        release_date = game.get('release_date') 
        if release_date is not None: 
            release_date =parse_steam_date(release_date.get('date'))
        
        # Теги как JSON
        tags = json.dumps(game.get('tags', {}))
        
        # Категории и жанры как массивы
        categories = [ i['description'] for i in game.get('categories', [])]
        genres = [ i['description'] for i in game.get('genres', [])]
        

        columns = [
            'steam_app_id', 'name', 'release_date', 'required_age',
            'short_description', 'header_image_url', 'categories',
            'genres', 'positive', 'negative', 'estimated_owners',
            'average_playtime_forever', 'average_playtime_2weeks',
            'median_playtime_forever', 'median_playtime_2weeks', 'tags'
        ]
        data = [
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
        ]

        client.insert(columns, 'games', data)
            
    def get_steam_id(self, tg_id : int) -> int | None:
        result  = self.select(['steam_id'], 'bot_users', f"tg_id = {tg_id}")
        if result[0] is not None and len(result[0]) > 0:
            steam_id = result[0][0][0]  
            if steam_id is not None:
                return int(steam_id)
        return None

    def add_steam_friends(self, id : int, ids : List[int]):
        for item in ids:
            self.insert(['user1', 'user2'], 'friends', [min(id, item), max(id,item)])

    def add_steam_users(self, data : List[Dict]):
        for item in data:
            self.insert(
                ['steam_user_id', 'username', 'profile_url', 'avatarmedium_url'],
                'steam_users', 
                [item['steamid'], item['personaname'], item['profileurl'], item['avatarmedium']]
            )

    def add_user_games(self, user_id : int, games_info : List):
        for item in games_info:
            self.insert(
                ['user_id', 'game_id', 'playtime_total'],
                'user_games', 
                [user_id, item['appid'], item['playtime_forever']]
            )

    def get_friends_updates(self, user_id : int) -> List[tuple[int, str]]:
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT game_id, game_name 
                    FROM get_top_new_friend_games(%s, %s, %s)
                """, (user_id, 5, 14))
                result = cursor.fetchall()
                self.connection.commit()
                return result
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise

    def get_similar_games(self, app_id: int, limit: int = 5) -> List[tuple]:
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT app_id, game_name 
                    FROM find_similar_games(%s, %s)
                """, (app_id, limit))
                result = cursor.fetchall()
                self.connection.commit()
                return result
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise
    
    def get_recommendations(self, steam_user_id: int, limit: int = 5) -> List[tuple]:
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT app_id, game_name 
                    FROM recommend_by_user_profile(%s, %s)
                """, (steam_user_id, limit))
                result = cursor.fetchall()
                self.connection.commit()
                return result
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise
