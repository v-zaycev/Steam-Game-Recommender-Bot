from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

def parse_steam_date(date_str):
    """Конвертирует Steam дату в формат PostgreSQL"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%b %d, %Y').date()
    except ValueError:
        return None


def is_valid_steamid64(steamid64):
    try:
        steamid64 = int(steamid64)
        return 76561197960265728 <= steamid64 <= 76561202255233023
    except:
        return False

class States(StatesGroup):
    id_waiting = State()
    info_game_id_waiting = State()
    similar_game_id_waiting = State()